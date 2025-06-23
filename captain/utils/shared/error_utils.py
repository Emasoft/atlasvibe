#!/usr/bin/env python3
# Copyright (c) 2024 Emasoft
#
# This file is part of AtlasVibe, which is based on Flojoy Studio
# Original Copyright (c) 2023-2024 Flojoy
#
# SPDX-License-Identifier: MIT
# See the LICENSE file for details.

# -*- coding: utf-8 -*-

"""
Error handling utilities for consistent error management across the codebase.
"""

import functools
import logging
import traceback
import time
import asyncio
import inspect
from typing import TypeVar, Callable, Any, Optional, Type, cast
from contextlib import contextmanager


T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def safe_execute(
    func: Callable[..., T],
    *args,
    default: Optional[T] = None,
    logger: Optional[logging.Logger] = None,
    error_message: str = "Error occurred",
    **kwargs,
) -> T:
    """
    Execute a function safely, catching and logging exceptions.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        default: Default value to return on error
        logger: Logger to use for error messages
        error_message: Custom error message prefix
        **kwargs: Keyword arguments for the function

    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if logger:
            logger.error(f"{error_message}: {e}")
            logger.debug(traceback.format_exc())
        return default


def with_error_handling(
    default: Any = None,
    logger: Optional[logging.Logger] = None,
    error_message: str = "Error in {func_name}",
    reraise: bool = False,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Decorator for adding error handling to functions.

    Args:
        default: Default value to return on error
        logger: Logger to use for error messages
        error_message: Error message template (can use {func_name})
        reraise: Whether to re-raise the exception after logging
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if logger:
                    msg = error_message.format(func_name=func.__name__)
                    logger.error(f"{msg}: {e}")
                    logger.debug(traceback.format_exc())

                if reraise:
                    raise

                return default

        return cast(F, wrapper)

    return decorator


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[logging.Logger] = None,
) -> Callable[[F], F]:
    """
    Decorator for adding retry logic to functions.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to retry on
        logger: Logger for retry messages

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        # Check if the function is async
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                current_delay = delay
                last_exception = None

                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            if logger:
                                logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}")
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff
                        else:
                            if logger:
                                logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")

                if last_exception:
                    raise last_exception

            return cast(F, async_wrapper)
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                current_delay = delay
                last_exception = None

                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            if logger:
                                logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}")
                            time.sleep(current_delay)
                            current_delay *= backoff
                        else:
                            if logger:
                                logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")

                if last_exception:
                    raise last_exception

            return cast(F, sync_wrapper)

    return decorator


@contextmanager
def error_context(operation: str, logger: Optional[logging.Logger] = None, reraise: bool = True):
    """
    Context manager for error handling with descriptive operation names.

    Args:
        operation: Description of the operation being performed
        logger: Logger to use for error messages
        reraise: Whether to re-raise exceptions

    Example:
        with error_context("loading configuration", logger):
            config = load_config()
    """
    try:
        yield
    except Exception as e:
        if logger:
            logger.error(f"Error while {operation}: {e}")
            logger.debug(traceback.format_exc())

        if reraise:
            raise


class ErrorAccumulator:
    """
    Accumulate errors without stopping execution.

    Useful for validation or batch operations where you want to
    collect all errors before reporting.
    """

    def __init__(self):
        self.errors: list[tuple[str, Exception]] = []

    def add(self, context: str, error: Exception) -> None:
        """Add an error with context."""
        self.errors.append((context, error))

    def add_from_callable(self, context: str, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a function and capture any errors."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.add(context, e)
            return None

    def has_errors(self) -> bool:
        """Check if any errors have been accumulated."""
        return len(self.errors) > 0

    def get_summary(self) -> str:
        """Get a summary of all errors."""
        if not self.errors:
            return "No errors"

        lines = ["Errors encountered:"]
        for context, error in self.errors:
            lines.append(f"  - {context}: {error}")

        return "\n".join(lines)

    def raise_if_errors(self, message: str = "Multiple errors occurred") -> None:
        """Raise an exception if any errors were accumulated."""
        if self.errors:
            raise Exception(f"{message}\n{self.get_summary()}")

    def clear(self) -> None:
        """Clear all accumulated errors."""
        self.errors.clear()


def format_exception_chain(e: Exception, include_traceback: bool = False) -> str:
    """
    Format an exception and its chain in a readable way.

    Args:
        e: The exception to format
        include_traceback: Whether to include full traceback

    Returns:
        Formatted exception string
    """
    parts = []
    current = e

    while current is not None:
        if include_traceback:
            parts.append(traceback.format_exception(type(current), current, current.__traceback__))
        else:
            parts.append(f"{type(current).__name__}: {current}")

        current = current.__cause__ or current.__context__

    if include_traceback:
        return "\n".join("".join(part) for part in parts)
    else:
        return " -> ".join(parts)


def create_error_handler(
    logger: logging.Logger,
    error_mapping: Optional[dict[Type[Exception], Callable[[Exception], Any]]] = None,
) -> Callable[[Exception], Any]:
    """
    Create a custom error handler with specific handling for different exception types.

    Args:
        logger: Logger to use
        error_mapping: Dictionary mapping exception types to handler functions

    Returns:
        Error handler function
    """
    if error_mapping is None:
        error_mapping = {}

    def handle_error(e: Exception) -> Any:
        # Check for specific handlers
        for exc_type, handler in error_mapping.items():
            if isinstance(e, exc_type):
                return handler(e)

        # Default handling
        logger.error(f"Unhandled error: {e}")
        logger.debug(traceback.format_exc())
        raise e

    return handle_error
