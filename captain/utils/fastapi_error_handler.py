#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Created FastAPI-specific error handling utilities
# - Integrates with shared error utils for consistent error management
# - Provides decorators, response formatting, and error accumulation
#

"""
FastAPI-specific error handling utilities that integrate with shared error utils.
"""

import functools
import time
import uuid
from datetime import datetime
from typing import TypeVar, Callable, Any, Optional, Type, cast, Dict, Tuple
from contextlib import asynccontextmanager

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from captain.utils.logger import logger
from captain.utils.shared.error_utils import (
    with_retry,
    ErrorAccumulator as BaseErrorAccumulator,
    format_exception_chain,
)


F = TypeVar("F", bound=Callable[..., Any])


class ErrorResponse(BaseModel):
    """Standardized error response structure."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: str
    timestamp: datetime


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error details
        request_id: Request ID for tracking

    Returns:
        Dictionary formatted for JSON response
    """
    if request_id is None:
        request_id = f"req-{uuid.uuid4().hex[:12]}"

    return {
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


def sanitize_error_details(error: Exception) -> str:
    """
    Sanitize error messages to prevent information disclosure.

    Args:
        error: The exception to sanitize

    Returns:
        A safe error message for client consumption
    """
    # Log the full error internally
    logger.error(f"Error details: {error}", exc_info=True)

    # Map specific exceptions to safe messages
    safe_messages = {
        "ProjectStructureError": str(error),  # These are user-facing validation errors
        "FileNotFoundError": "The requested file was not found",
        "PermissionError": "Permission denied for this operation",
        "ValueError": "Invalid input provided",
        "TypeError": "Invalid type provided",
        "SyntaxError": f"Syntax error in code: {error}",  # Users need to know about syntax errors
        "ConnectionError": "Connection failed. Please try again later.",
        "TimeoutError": "Operation timed out. Please try again.",
        "OSError": "System error occurred. Please contact support.",
    }

    error_type = type(error).__name__

    # Return specific message if available, otherwise generic
    return safe_messages.get(
        error_type, "An internal error occurred. Please check logs for details."
    )


def fastapi_error_handler(
    operation: str,
    error_code_prefix: str = "BLOCKS",
    log_request: bool = False,
    log_duration: bool = False,
    slow_threshold: float = 1.0,
    retry: bool = False,
    max_attempts: int = 3,
    retry_delay: float = 0.5,
    retry_backoff: float = 2.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (ConnectionError, TimeoutError),
) -> Callable[[F], F]:
    """
    Decorator for FastAPI endpoints with comprehensive error handling.

    Args:
        operation: Description of the operation for logging
        error_code_prefix: Prefix for error codes
        log_request: Whether to log request details
        log_duration: Whether to log operation duration
        slow_threshold: Threshold in seconds for slow operation warning
        retry: Whether to enable retry logic
        max_attempts: Maximum retry attempts
        retry_delay: Initial delay between retries
        retry_backoff: Backoff multiplier for retries
        retry_exceptions: Exceptions to retry on

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        # Apply retry decorator if enabled
        if retry:
            func = with_retry(
                max_attempts=max_attempts,
                delay=retry_delay,
                backoff=retry_backoff,
                exceptions=retry_exceptions,
                logger=logger,
            )(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time() if log_duration else None
            request_id = f"req-{uuid.uuid4().hex[:12]}"

            # Log request if enabled
            if log_request:
                request_details = _extract_request_details(args, kwargs)
                logger.info(f"[{request_id}] Starting {operation}: {request_details}")

            try:
                # Execute the function
                result = await func(*args, **kwargs)

                # Log duration if enabled
                if log_duration:
                    duration = time.time() - start_time
                    if duration > slow_threshold:
                        logger.warning(
                            f"[{request_id}] Slow operation detected: {operation} "
                            f"took {duration:.2f}s (threshold: {slow_threshold}s)"
                        )
                    else:
                        logger.debug(
                            f"[{request_id}] {operation} completed in {duration:.2f}s"
                        )

                return result

            except HTTPException:
                # Pass through FastAPI exceptions unchanged
                raise

            except Exception as e:
                # Log the full error
                logger.error(
                    f"[{request_id}] Error in {operation}: {format_exception_chain(e)}",
                    exc_info=True,
                )

                # Create error response
                error_code = f"{error_code_prefix}_{_get_error_code(e)}"
                error_message = sanitize_error_details(e)

                # Raise HTTPException with sanitized details
                raise HTTPException(
                    status_code=500,
                    detail=create_error_response(
                        status_code=500,
                        error_code=error_code,
                        message=error_message,
                        request_id=request_id,
                    ),
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time() if log_duration else None
            request_id = f"req-{uuid.uuid4().hex[:12]}"

            # Log request if enabled
            if log_request:
                request_details = _extract_request_details(args, kwargs)
                logger.info(f"[{request_id}] Starting {operation}: {request_details}")

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Log duration if enabled
                if log_duration:
                    duration = time.time() - start_time
                    if duration > slow_threshold:
                        logger.warning(
                            f"[{request_id}] Slow operation detected: {operation} "
                            f"took {duration:.2f}s (threshold: {slow_threshold}s)"
                        )
                    else:
                        logger.debug(
                            f"[{request_id}] {operation} completed in {duration:.2f}s"
                        )

                return result

            except HTTPException:
                # Pass through FastAPI exceptions unchanged
                raise

            except Exception as e:
                # Log the full error
                logger.error(
                    f"[{request_id}] Error in {operation}: {format_exception_chain(e)}",
                    exc_info=True,
                )

                # Create error response
                error_code = f"{error_code_prefix}_{_get_error_code(e)}"
                error_message = sanitize_error_details(e)

                # Raise HTTPException with sanitized details
                raise HTTPException(
                    status_code=500,
                    detail=create_error_response(
                        status_code=500,
                        error_code=error_code,
                        message=error_message,
                        request_id=request_id,
                    ),
                )

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator


def _extract_request_details(args: tuple, kwargs: dict) -> str:
    """Extract request details for logging."""
    details = []

    # Look for Pydantic models in arguments
    for arg in args:
        if hasattr(arg, "__class__") and hasattr(arg.__class__, "__fields__"):
            # This is likely a Pydantic model
            details.append(str(arg))

    # Look for specific known parameters
    for key in ["request", "data", "payload"]:
        if key in kwargs:
            details.append(f"{key}={kwargs[key]}")

    return ", ".join(details) if details else "No request details"


def _get_error_code(error: Exception) -> str:
    """Generate error code from exception type."""
    error_type = type(error).__name__

    # Map common exceptions to codes
    error_codes = {
        "FileNotFoundError": "NOT_FOUND",
        "PermissionError": "PERMISSION_DENIED",
        "ValueError": "INVALID_VALUE",
        "TypeError": "INVALID_TYPE",
        "SyntaxError": "SYNTAX_ERROR",
        "ConnectionError": "CONNECTION_FAILED",
        "TimeoutError": "TIMEOUT",
        "OSError": "SYSTEM_ERROR",
    }

    return error_codes.get(error_type, "INTERNAL_ERROR")


class ErrorAccumulator(BaseErrorAccumulator):
    """
    Extended error accumulator for FastAPI endpoints.

    Inherits from shared ErrorAccumulator and adds FastAPI-specific features.
    """

    def to_http_response(self, status_code: int = 400) -> JSONResponse:
        """Convert accumulated errors to HTTP response."""
        if not self.errors:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Operation completed successfully",
                },
            )

        error_details = []
        for context, error in self.errors:
            error_details.append(
                {"context": context, "error": str(error), "type": type(error).__name__}
            )

        return JSONResponse(
            status_code=status_code,
            content=create_error_response(
                status_code=status_code,
                error_code="MULTIPLE_ERRORS",
                message="Multiple errors occurred during operation",
                details={"errors": error_details},
            ),
        )

    def add_validation_error(self, field: str, message: str) -> None:
        """Add a validation error for a specific field."""
        self.add(f"Validation error for field '{field}'", ValueError(message))


@asynccontextmanager
async def managed_operation(
    operation: str,
    request_id: Optional[str] = None,
    broadcast_start: bool = False,
    broadcast_complete: bool = False,
    ws_manager: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Context manager for operations with lifecycle management.

    Args:
        operation: Description of the operation
        request_id: Request ID for tracking
        broadcast_start: Whether to broadcast start event
        broadcast_complete: Whether to broadcast completion event
        ws_manager: WebSocket manager for broadcasting
        metadata: Additional metadata for broadcasts

    Example:
        async with managed_operation(
            "regenerating block metadata",
            broadcast_start=True,
            broadcast_complete=True,
            ws_manager=ws_manager,
            metadata={"block_name": "MY_BLOCK"}
        ):
            # Perform operation
            regenerate_metadata()
    """
    if request_id is None:
        request_id = f"req-{uuid.uuid4().hex[:12]}"

    start_time = time.time()

    # Broadcast start event if requested
    if broadcast_start and ws_manager:
        await ws_manager.broadcast(
            {
                "type": f"{operation}_start",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {}),
            }
        )

    try:
        logger.info(f"[{request_id}] Starting {operation}")
        yield request_id

        # Broadcast completion event if requested
        if broadcast_complete and ws_manager:
            await ws_manager.broadcast(
                {
                    "type": f"{operation}_complete",
                    "request_id": request_id,
                    "duration": time.time() - start_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    **(metadata or {}),
                }
            )

        logger.info(
            f"[{request_id}] Completed {operation} in {time.time() - start_time:.2f}s"
        )

    except Exception as e:
        # Broadcast error event if requested
        if ws_manager:
            await ws_manager.broadcast(
                {
                    "type": f"{operation}_error",
                    "request_id": request_id,
                    "error": sanitize_error_details(e),
                    "timestamp": datetime.utcnow().isoformat(),
                    **(metadata or {}),
                }
            )

        logger.error(
            f"[{request_id}] Error in {operation}: {format_exception_chain(e)}",
            exc_info=True,
        )
        raise
