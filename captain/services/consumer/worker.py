# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

import uuid
from queue import Queue
from typing import Any, cast

from pkgs.atlasvibe.atlasvibe import JobFailure, JobService, JobSuccess
from pkgs.atlasvibe.atlasvibe.atlasvibe_node_venv import PipInstallThread

from captain.types.worker import JobInfo, PoisonPill
from captain.utils.broadcast import Signaler
from captain.utils.logger import logger
from captain.services.change_queue import ChangeQueueManager

"""
IMPORTANT NOTE: This class mimics the RQ Worker package.
"""


class Worker:
    def __init__(
        self,
        task_queue: Queue[Any],  # queue for tasks to be processed
        finish_queue: Queue[Any],  # queue for finished tasks
        imported_functions: dict[str, Any],  # map of job id to corresponding function
        observe_blocks: list[str],
        signaler: Signaler | None = None,  # signaler object to signal to the front-end
        node_delay: float = 0,
    ):
        self.task_queue = task_queue
        self.finish_queue = finish_queue
        self.imported_functions = imported_functions
        self.observe_blocks = observe_blocks
        self.signaler = signaler
        self.job_service = JobService()
        self.uuid = uuid.uuid4()
        self.node_delay = node_delay
        self.change_queue_manager = ChangeQueueManager.get_instance()

    async def run(self):
        logger.info(f"Worker {self.uuid} has started")
        while True:
            logger.debug(f"Worker {self.uuid} waiting for task...")
            queue_fetch = self.task_queue.get()
            logger.info(f"Worker {self.uuid} got task: {queue_fetch}")

            if isinstance(queue_fetch, PoisonPill):
                logger.debug(f"Worker {self.uuid} got poison pill.")
                break

            # cast for type purposes
            try:
                job = cast(JobInfo, queue_fetch)
            except Exception:
                logger.error("Error in job: wrong arguments passed. Ignoring...")
                continue

            func = self.imported_functions.get(job.job_id, None)
            if func is None:
                raise ValueError(f"Function {job.job_id} not found in imported functions")
            if self.signaler:
                # signal the running node to the front-end:
                await self.signaler.signal_current_running_node(job.jobset_id, job.job_id, func.__name__)

            # Mark block as executing in change queue
            self.change_queue_manager.mark_block_executing(job.job_id)

            kwargs: dict[str, Any] = {
                "ctrls": job.ctrls,
                "previous_jobs": job.previous_jobs,
                "observe_blocks": self.observe_blocks,
                "jobset_id": job.jobset_id,
                "node_id": job.job_id,
                "job_id": job.iteration_id,
            }

            logger.debug("=" * 100)
            logger.debug(f"Executing job {job.job_id}, kwargs = {kwargs}")

            response = func(**kwargs)

            match response:
                case JobSuccess():
                    logger.debug(f"Job finished: {job.job_id}, status: ok")
                    if self.signaler:
                        # send results to frontend
                        await self.signaler.signal_node_results(job.jobset_id, job.job_id, func.__name__, response.result)

                case JobFailure():
                    logger.debug(f"Job finished: {job.job_id}, status: failed")
                    logger.error(f"Node {func.__name__} failed! reason: {response.error}")

                    if self.signaler:
                        # signal to frontend that the node has failed
                        await self.signaler.signal_failed_nodes(job.jobset_id, job.job_id, func.__name__, response.error)

                    PipInstallThread.terminate_all()
                    raise Exception(response.error)

            # Mark block as finished in change queue (applies pending changes)
            self.change_queue_manager.mark_block_finished(job.job_id)

            # put the job result in the queue for producer to process
            self.finish_queue.put(response)
            self.task_queue.task_done()

        logger.info(f"Worker {self.uuid} has finished")
