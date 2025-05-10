"""
This module provides a decorator that allows a function to be executed in a virtual environment.
The decorator will create a virtual environment if it does not exist, and install the pip dependencies
specified in the decorator arguments. The decorator will also install the pip dependencies if the
virtual environment exists but does not contain the pip dependencies.

Example usage:

```python
from atlasvibe_sdk import atlasvibe_node, run_in_venv, Matrix # Assuming Matrix is part of atlasvibe_sdk

@atlasvibe_node
@run_in_venv(pip_dependencies=["torch==2.0.1", "torchvision==0.15.2"])
def TORCH_NODE(default: Matrix) -> Matrix:
    import torch
    import torchvision
    # Do stuff with torch
    ...
    return Matrix(...)

"""

import hashlib
import importlib.metadata
import inspect
import logging
import multiprocessing
import multiprocessing.connection
import os
import shutil
import subprocess
import sys
import threading
import traceback
import venv
from collections.abc import Iterable, Mapping
from contextlib import ExitStack, contextmanager
from functools import wraps
from time import sleep
from typing import Any, Callable

import cloudpickle
import portalocker

from ._logging import LogPipe, LogPipeMode, StreamEnum
# Import ATLASVIBE_CACHE_DIR from the centralized location
from atlasvibe_engine.utils.cache_utils import ATLASVIBE_CACHE_DIR

__all__ = ["run_in_venv"]


def _get_venv_cache_dir():
    return os.path.join(ATLASVIBE_CACHE_DIR, "atlasvibe_node_venv")


def _get_venv_syspath(venv_executable: os.PathLike[Any]) -> list[str]:
    """Get the sys.path of the virtual environment."""
    command = [venv_executable, "-c", "import sys\nprint(sys.path)"]
    cmd_output = subprocess.run(command, check=True, capture_output=True, text=True)
    return eval(cmd_output.stdout)


@contextmanager
def swap_sys_path(
    venv_executable: os.PathLike[Any], extra_sys_path: list[str] | None = None
):
    """Temporarily swap the sys.path of the child process with the sys.path of the parent process."""
    old_path = sys.path
    try:
        new_path = _get_venv_syspath(venv_executable)
        extra_sys_path = [] if extra_sys_path is None else extra_sys_path
        sys.path = new_path + extra_sys_path
        yield
    finally:
        sys.path = old_path


def _get_venv_executable_path(
    venv_path: os.PathLike[Any] | str,
) -> os.PathLike[Any] | str:
    """Get the path to the python executable of the virtual environment."""
    if sys.platform == "win32":
        return os.path.realpath(os.path.join(venv_path, "Scripts", "python.exe"))
    else:
        return os.path.realpath(os.path.join(venv_path, "bin", "python"))


def _get_venv_lockfile_path(
    venv_path: os.PathLike[Any] | str,
) -> os.PathLike[Any] | str:
    """Get the path to the lockfile of the virtual environment."""
    return os.path.join(
        os.path.dirname(venv_path), f".{os.path.basename(venv_path)}.lockfile"
    )


def _bootstrap_venv(
    venv_path: os.PathLike[Any],
    pip_dependencies: list[str],
    logger: logging.Logger,
    verbose: bool = False,
):
    lockfile_path = _get_venv_lockfile_path(venv_path)
    logger.info(f"Waiting to acquire lock on {lockfile_path}...")
    # Acquire a lock on the virtual environment to ensure no other process is using it
    with portalocker.Lock(
        lockfile_path, mode="ab", fail_when_locked=False, flags=portalocker.LOCK_EX
    ):
        logger.info(f"Acquired lock on {lockfile_path}...")
        # Check if the virtual environment is complete, i.e. it contains a .venv_is_complete file
        venv_is_complete_path = os.path.realpath(
            os.path.join(venv_path, ".venv_is_complete")
        )
        # Look for the .venv_is_complete file. If it does not exist, wipe and re-create the venv
        # The .venv_is_complete file is created at the end of a successful pip install process
        if not os.path.exists(venv_is_complete_path):
            logger.warning(
                f"For some reason, the virtual environment at {venv_path} was found to be incomplete. Deleting the virtual environment and creating a new one..."
            )
            shutil.rmtree(venv_path, ignore_errors=True)
            logger.info(f"Creating new virtual environment at {venv_path}...")
            venv.create(venv_path, with_pip=True)
        # At this point, the venv should be created and
        # _get_venv_executable_path should return a valid path (with symlinks resolved)
        venv_executable = _get_venv_executable_path(venv_path)
        command = [venv_executable, "-m", "pip", "install"]
        if not verbose:
            command += ["-q", "-q"]
        command += list(pip_dependencies)
        with ExitStack() as stack:
            logpipe_stderr = stack.enter_context(
                LogPipe(
                    logger,
                    log_level=logging.ERROR,
                    mode=LogPipeMode.SUBPROCESS,
                    buffer_logs=True,
                )
            )
            logpipe_stdout = stack.enter_context(
                LogPipe(
                    logger,
                    log_level=logging.INFO,
                    mode=LogPipeMode.SUBPROCESS,
                    buffer_logs=True,
                )
            )
            proc = subprocess.Popen(
                command,
                stdout=logpipe_stdout.get_pipe_writer(),
                stderr=logpipe_stderr.get_pipe_writer(),
            )
            # Poll the process until it finishes, while occasionally checking if there was a failure
            # in the global cancel event
            while proc.poll() is None:
                if PipInstallThread._cancel_all_threads.is_set():
                    proc.terminate()
                    logger.error(
                        f"Another thread has failed its pip install step, terminating pip install process for {venv_path}..."
                    )
                    break
                sleep(0.1)

        # The process was terminated due to the _cancel_all_threads event
        if proc.returncode is None:
            return

        if proc.returncode != 0:
            # First wipe the .venv_is_complete file to mark the directory as invalid
            # in case the deletion of the entire directory fails.
            if os.path.exists(venv_is_complete_path):
                os.remove(venv_is_complete_path)
            # Then delete the entire directory.
            shutil.rmtree(venv_path, ignore_errors=True)
            bullet_points_list = "\n - ".join([""] + pip_dependencies)
            logger.error(
                f"Failed to install pip dependencies into virtual environment from "
                f"the provided list: {bullet_points_list}\n. "
                f"The virtual environment under {venv_path} has been deleted."
            )
            raise subprocess.CalledProcessError(
                proc.returncode,
                command,
                output=logpipe_stdout.log_buffer.getvalue().encode("utf-8"),
                stderr=logpipe_stderr.log_buffer.getvalue().encode("utf-8"),
            )

        # Create a file to mark the virtual environment as complete
        with open(venv_is_complete_path, "w") as f:
            f.write("")


class PipInstallThread(threading.Thread):
    _bounded_semaphore = threading.BoundedSemaphore(1)
    _cancel_all_threads = threading.Event()
    _threads = dict()
    _exceptions = dict()

    def __init__(
        self,
        group: None = None,
        target: Callable[..., object] | None = None,
        name: str | None = None,
        args: Iterable[Any] = ..., # Ellipsis for args
        kwargs: Mapping[str, Any] | None = None, # Ellipsis for kwargs
    ) -> None:
        super().__init__(group, target, name, args, kwargs, daemon=False) # daemon=False is default
        self.target = target
        self.args = args if args is not ... else tuple() # Ensure args is a tuple
        self.kwargs = kwargs if kwargs is not None else {} # Ensure kwargs is a dict
        PipInstallThread._threads.update({self.name: self})
        PipInstallThread._exceptions.update({self.name: None})

    def run(self):
        with PipInstallThread._bounded_semaphore:
            # Just exit if all was cancelled
            if PipInstallThread._cancel_all_threads.is_set():
                return
            try:
                if self.target: # Ensure target is not None
                    self.target(*self.args, **self.kwargs)
            except Exception as e:
                PipInstallThread._exceptions.update({self.name: e})
                # It's generally better to let the main thread handle re-raising
                # or logging the exception after join(), rather than raising here.
                # For now, keeping the original behavior of raising.
                raise e

    @staticmethod
    def terminate_all():
        PipInstallThread._cancel_all_threads.set()
        # Wait for all threads to finish
        for thread_name in list(PipInstallThread._threads.keys()): # Iterate over a copy of keys
            thread = PipInstallThread._threads.get(thread_name)
            if thread and thread.is_alive():
                thread.join(timeout=5.0) # Add a timeout to join
            # Clean up after thread finishes or times out
            if thread_name in PipInstallThread._threads:
                del PipInstallThread._threads[thread_name]
            if thread_name in PipInstallThread._exceptions:
                del PipInstallThread._exceptions[thread_name]


# Define ChildProcessError if it's a custom exception type used here
class ChildProcessError(Exception):
    """Custom exception for errors originating in a child process."""
    pass


class PickleableFunctionWithPipeIO:
    """A wrapper for a function that can be pickled and executed in a child process."""

    def __init__(
        self,
        func: Callable,
        child_conn: multiprocessing.connection.Connection,
        venv_executable: str, # Changed from os.PathLike[Any] to str for simplicity
    ):
        self._func_serialized = cloudpickle.dumps(func)
        func_module_path = os.path.dirname(os.path.realpath(inspect.getabsfile(func)))
        # Check that the function is in a directory indeed
        self._extra_sys_path = (
            [func_module_path] if os.path.isdir(func_module_path) else None
        )
        self._child_conn = child_conn
        self._venv_executable = venv_executable

    def __call__(self, *args_serialized, **kwargs_serialized):
        with swap_sys_path(
            venv_executable=self._venv_executable, extra_sys_path=self._extra_sys_path
        ):
            try:
                fn = cloudpickle.loads(self._func_serialized)
                args = [cloudpickle.loads(arg) for arg in args_serialized]
                kwargs = {
                    key: cloudpickle.loads(value)
                    for key, value in kwargs_serialized.items()
                }
                # Capture logs here too
                output = fn(*args, **kwargs)
                serialized_result = cloudpickle.dumps(output)
            except Exception as e:
                # Not all exceptions are expected to be picklable
                # so we clone their traceback and send our own custom type of exception
                exc_type = type(e)
                exc_tb_str = traceback.format_exception(exc_type, e, e.__traceback__)
                # Send a tuple (Exception type, args, traceback string)
                # This avoids pickling complex exceptions directly.
                serialized_result = cloudpickle.dumps(
                    (exc_type, e.args, exc_tb_str)
                )
        self._child_conn.send_bytes(serialized_result)


def run_in_venv(pip_dependencies: list[str], verbose: bool = True): # Changed default verbose to True
    """A decorator that allows a function to be executed in a virtual environment.

    Args:
        pip_dependencies (list[str]): A list of pip dependencies to install into the virtual environment.
        verbose (bool): Whether to print the pip install output. Defaults to True.

    Example usage:
    ```python
    from atlasvibe_sdk import atlasvibe_node, run_in_venv, Matrix

    @atlasvibe_node
    @run_in_venv(pip_dependencies=["torch==2.0.1", "torchvision==0.15.2"])
    def TORCH_NODE(default: Matrix) -> Matrix:
        import torch
        import torchvision
        # Do stuff with torch
        ...
        return Matrix(...)
    """

    def decorator(
        func: Callable[..., Any],
        *,
        pip_dependencies: list[str] = pip_dependencies, # Default to outer scope pip_dependencies
        verbose: bool = verbose, # Default to outer scope verbose
    ):
        # Return the function as-is if we are not in the main process
        # This is due to the fact that the decorator is called twice
        # once in the main process and once in the child process
        # when unpickling the function
        if multiprocessing.current_process().name.startswith("run_in_venv"):
            return func

        # Pre-pend atlasvibe_sdk and cloudpickle as mandatory pip dependencies
        packages_dict = {
            package.name.lower(): package.version # Use lower case for matching
            for package in importlib.metadata.distributions()
        }
        # Assuming 'atlasvibe_sdk' is the name if this package were on PyPI or installable
        # This might need to be the main project name 'atlasvibe' if it's packaged that way
        # For development, this might involve installing an editable version.
        # For now, we assume 'atlasvibe_sdk' is not a pip-installable package itself,
        # but its code is available in the PYTHONPATH.
        # If 'atlasvibe_sdk' (or 'atlasvibe' as the main project) is installable, add it here.
        # sdk_package_name = "atlasvibe_sdk" # Or "atlasvibe"
        
        # Ensure cloudpickle version is pinned
        cloudpickle_version = packages_dict.get('cloudpickle')
        if not cloudpickle_version:
            # Fallback or raise error if cloudpickle isn't found in current env
            # This is critical for serialization.
            raise RuntimeError("cloudpickle not found in the current environment. It's required for @run_in_venv.")

        current_pip_dependencies = sorted(
            list(
                set( # Use set to avoid duplicates if user adds them
                    [
                        # sdk_package_name, # Only if atlasvibe_sdk is pip installable
                        f"cloudpickle=={cloudpickle_version}",
                    ]
                    + pip_dependencies
                )
            )
        )
        # Get the root directory for the virtual environments
        venv_cache_dir = _get_venv_cache_dir()
        os.makedirs(venv_cache_dir, exist_ok=True)
        venv_cache_dir = os.path.realpath(venv_cache_dir)
        # Generate a path-safe hash of the pip dependencies
        # this prevents the duplication of virtual environments
        pip_dependencies_hash = hashlib.md5(
            "".join(sorted(current_pip_dependencies)).encode() # Use current_pip_dependencies
        ).hexdigest()[:8]
        venv_path = os.path.join(venv_cache_dir, f"{pip_dependencies_hash}")
        logger = logging.getLogger(func.__name__)
        if verbose: # Check outer verbose flag
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING) # Or some other level if not verbose

        # Use a unique name for the thread, e.g., based on venv_path
        thread_name = f"PipInstallThread-{pip_dependencies_hash}"
        thread = PipInstallThread(
            name=thread_name, # Pass name to PipInstallThread
            target=_bootstrap_venv,
            args=(venv_path, current_pip_dependencies, logger, verbose), # Pass current_pip_dependencies
        )
        thread.start()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any): # Changed dict[str, Any] to Any for kwargs
            # Wait for the pip install to finish
            logger.info(
                f"Waiting for pip install to finish for virtual environment of {func.__name__} at {venv_path}..."
            )
            thread.join() # Wait for the specific thread for this venv
            venv_executable = _get_venv_executable_path(venv_path)
            # Check if the thread threw an exception
            if PipInstallThread._exceptions.get(thread.name) is not None: # Check specific thread
                # Clean up the other threads (and the processes they spawned)
                # This might be too aggressive if other unrelated venvs are being built.
                # PipInstallThread.terminate_all() # Consider if this is always desired
                # Re-raise from the main thread
                raise PipInstallThread._exceptions[thread.name]
            logger.info(
                f"Pip install complete. Spawning process for function {func.__name__}..."
            )
            # Generate a new multiprocessing context for the parent process in "spawn" mode
            parent_mp_context = multiprocessing.get_context("spawn")
            parent_conn, child_conn = parent_mp_context.Pipe()
            # Create a new multiprocessing context for the child process in "spawn" mode
            # while setting its executable to the virtual environment python executable
            child_mp_context = multiprocessing.get_context("spawn")
            child_mp_context.set_executable(str(venv_executable)) # Ensure it's a string
            with ExitStack() as stack:
                log_pipe_stdout = stack.enter_context(
                    LogPipe(
                        logger=logger, log_level=logging.INFO, mode=LogPipeMode.MP_SPAWN
                    )
                )
                log_pipe_stderr = stack.enter_context(
                    LogPipe(
                        logger=logger,
                        log_level=logging.ERROR,
                        mode=LogPipeMode.MP_SPAWN,
                    )
                )
                # Serialize function arguments using cloudpickle
                pickleable_func_with_pipe = PickleableFunctionWithPipeIO(
                    func=func,
                    child_conn=child_conn,
                    venv_executable=str(venv_executable), # Ensure it's a string
                )
                # Wrap the function with a decorator that redirects stdout and stderr to the log pipes
                mp_func = LogPipe.wrap_and_redirect_stream(
                    pickleable_func_with_pipe,
                    StreamEnum.STDOUT,
                    log_pipe_stdout.get_pipe_writer(),
                )
                mp_func = LogPipe.wrap_and_redirect_stream(
                    mp_func, StreamEnum.STDERR, log_pipe_stderr.get_pipe_writer()
                )
                # Resolve the function arguments using inspect
                # this is needed to avoid pickling issues
                # This should serialize args and kwargs directly, not the callargs dict
                serialized_args = [cloudpickle.dumps(arg_val) for arg_val in args]
                serialized_kwargs = {
                    key: cloudpickle.dumps(value) for key, value in kwargs.items()
                }

                # Create a new process that will run the Python code
                # Append a name and a random suffix
                process = child_mp_context.Process(
                    name=f"run_in_venv_{os.urandom(4).hex()}",
                    target=mp_func,
                    args=tuple(serialized_args), # Pass serialized args
                    kwargs=serialized_kwargs, # Pass serialized kwargs
                )
                # Start the process
                process.start()
                # Fetch result from the child process
                serialized_result = parent_conn.recv_bytes()
                # Wait for the process to finish
                process.join()
            # Check if the process sent an exception with a traceback
            result = cloudpickle.loads(serialized_result)
            # Check if the result is (Exception type, args, traceback string)
            if (
                isinstance(result, tuple)
                and len(result) == 3
                and isinstance(result[0], type) # Check if first element is a type
                and issubclass(result[0], Exception) # Check if it's an Exception subclass
            ):
                # Fetch exception type, args, and formatted traceback (list[str])
                exc_type, exc_args, tcb_str_list = result
                # Reraise an exception of the original type
                exception_instance = exc_type(*exc_args)
                logger.error(
                    f"Error in child process ({func.__name__}) with the following traceback:\n{''.join(tcb_str_list)}"
                )
                # To preserve the traceback as if it happened in the child,
                # it's tricky. For now, raise the reconstructed exception.
                raise exception_instance
            return result

        return wrapper

    return decorator
