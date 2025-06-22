#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

# CHANGELOG:
# - Async-compatible worker for use with PrefectTopologyExecutor
# - Uses asyncio.Queue instead of blocking Queue
# - Properly handles async/await patterns

import uuid
import asyncio
from typing import Any, Dict, List, Optional
import logging

from pkgs.atlasvibe.atlasvibe import JobFailure, JobService, JobSuccess
from captain.types.worker import JobInfo, PoisonPill
from captain.utils.broadcast import Signaler
from captain.services.change_queue import ChangeQueueManager

logger = logging.getLogger(__name__)


class AsyncWorker:
    """Async-compatible worker for processing jobs."""

    def __init__(
        self,
        task_queue: asyncio.Queue[Any],  # async queue for tasks
        finish_queue: asyncio.Queue[Any],  # async queue for results
        imported_functions: Dict[str, Any],  # job_id -> function mapping
        observe_blocks: List[str],
        signaler: Optional[Signaler] = None,
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
        """Run the worker asynchronously."""
        logger.info(f"AsyncWorker {self.uuid} has started")

        while True:
            try:
                logger.debug(f"AsyncWorker {self.uuid} waiting for task...")
                queue_fetch = await self.task_queue.get()
                logger.info(f"AsyncWorker {self.uuid} got task: {queue_fetch}")

                if isinstance(queue_fetch, PoisonPill):
                    logger.debug(f"AsyncWorker {self.uuid} got poison pill.")
                    break

                # Process job
                if isinstance(queue_fetch, JobInfo):
                    await self._process_job(queue_fetch)
                else:
                    logger.error(f"Unknown task type: {type(queue_fetch)}")

            except Exception as e:
                logger.error(f"AsyncWorker {self.uuid} error: {e}")
                import traceback

                traceback.print_exc()

        logger.info(f"AsyncWorker {self.uuid} has finished")

    async def _process_job(self, job: JobInfo):
        """Process a single job."""
        func = self.imported_functions.get(job.job_id)
        if func is None:
            raise ValueError(f"Function {job.job_id} not found in imported functions")

        if self.signaler:
            # Signal the running node to the front-end
            await self.signaler.signal_current_running_node(
                job.jobset_id, job.job_id, func.__name__
            )

        # Mark block as executing in change queue
        self.change_queue_manager.mark_block_executing(job.job_id)

        kwargs = {
            "ctrls": job.ctrls,
            "previous_jobs": job.previous_jobs,
            "observe_blocks": self.observe_blocks,
            "jobset_id": job.jobset_id,
            "node_id": job.job_id,
            "job_id": job.iteration_id,
        }

        logger.debug("=" * 100)
        logger.debug(f"Executing job {job.job_id}, kwargs = {kwargs}")

        # Add delay if needed
        if self.node_delay > 0:
            await asyncio.sleep(self.node_delay)

        # Execute function (assuming it's synchronous)
        response = func(**kwargs)

        if isinstance(response, JobSuccess):
            logger.debug(f"Job finished: {job.job_id}, status: ok")
            if self.signaler:
                # Send results to frontend
                await self.signaler.signal_node_results(
                    job.jobset_id, job.job_id, func.__name__, response.result
                )

        elif isinstance(response, JobFailure):
            logger.debug(f"Job finished: {job.job_id}, status: failed")
            logger.error(f"Node {func.__name__} failed! reason: {response.error}")

            if self.signaler:
                # Signal to frontend that the node has failed
                await self.signaler.signal_failed_nodes(
                    job.jobset_id, job.job_id, func.__name__, response.error
                )

            # Mark block as finished before raising
            self.change_queue_manager.mark_block_finished(job.job_id)
            raise Exception(response.error)

        # Mark block as finished in change queue (applies pending changes)
        self.change_queue_manager.mark_block_finished(job.job_id)

        # Put the job result in the queue for producer to process
        await self.finish_queue.put(response)
