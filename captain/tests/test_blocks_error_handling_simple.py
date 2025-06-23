#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Simplified test for error handling without complex imports
# - Tests the error handling utilities directly
#

"""
Simplified test suite for error handling utilities.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from captain.utils.fastapi_error_handler import (
    create_error_response,
    sanitize_error_details,
    fastapi_error_handler,
    ErrorAccumulator,
    managed_operation,
)
from captain.utils.shared.error_utils import (
    with_retry,
    error_context,
)


class TestErrorResponseFormat:
    """Test standardized error response format."""

    def test_create_error_response_with_all_fields(self):
        """Test creating error response with all fields."""
        response = create_error_response(
            status_code=400,
            error_code="INVALID_INPUT",
            message="Invalid input provided",
            details={"field": "name", "error": "too long"},
            request_id="req-123",
        )

        assert response["error"]["code"] == "INVALID_INPUT"
        assert response["error"]["message"] == "Invalid input provided"
        assert response["error"]["details"]["field"] == "name"
        assert response["error"]["request_id"] == "req-123"
        assert "timestamp" in response["error"]

    def test_create_error_response_minimal(self):
        """Test creating error response with minimal fields."""
        response = create_error_response(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message="Internal server error",
        )

        assert response["error"]["code"] == "INTERNAL_ERROR"
        assert response["error"]["message"] == "Internal server error"
        assert response["error"]["details"] is None
        assert response["error"]["request_id"].startswith("req-")
        assert "timestamp" in response["error"]


class TestErrorSanitization:
    """Test error message sanitization."""

    def test_sanitize_file_not_found(self):
        """Test sanitizing FileNotFoundError."""
        error = FileNotFoundError("/secret/path/to/file")
        result = sanitize_error_details(error)
        assert result == "The requested file was not found"
        assert "/secret" not in result

    def test_sanitize_permission_error(self):
        """Test sanitizing PermissionError."""
        error = PermissionError("Cannot access /etc/passwd")
        result = sanitize_error_details(error)
        assert result == "Permission denied for this operation"
        assert "/etc/passwd" not in result

    def test_sanitize_syntax_error(self):
        """Test sanitizing SyntaxError."""
        error = SyntaxError("invalid syntax")
        result = sanitize_error_details(error)
        assert "Syntax error in code:" in result
        assert "invalid syntax" in result

    def test_sanitize_generic_error(self):
        """Test sanitizing generic exception."""
        error = RuntimeError("Database password: secret123")
        result = sanitize_error_details(error)
        assert result == "An internal error occurred. Please check logs for details."
        assert "secret123" not in result


class TestFastAPIErrorHandler:
    """Test FastAPI error handler decorator."""

    @pytest.mark.asyncio
    async def test_async_success_no_error(self):
        """Test successful async operation."""

        @fastapi_error_handler(operation="test operation")
        async def test_func():
            return {"success": True}

        result = await test_func()
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_async_http_exception_passthrough(self):
        """Test that HTTPException is passed through."""
        from fastapi import HTTPException

        @fastapi_error_handler(operation="test operation")
        async def test_func():
            raise HTTPException(status_code=404, detail="Not found")

        with pytest.raises(HTTPException) as exc_info:
            await test_func()

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    @pytest.mark.asyncio
    async def test_async_generic_exception_handling(self):
        """Test generic exception is converted to HTTP 500."""
        from fastapi import HTTPException

        @fastapi_error_handler(operation="test operation")
        async def test_func():
            raise RuntimeError("Secret internal error")

        with pytest.raises(HTTPException) as exc_info:
            await test_func()

        assert exc_info.value.status_code == 500
        assert "Secret internal error" not in str(exc_info.value.detail)

    def test_sync_success_no_error(self):
        """Test successful sync operation."""

        @fastapi_error_handler(operation="test operation")
        def test_func():
            return {"success": True}

        result = test_func()
        assert result == {"success": True}

    def test_sync_generic_exception_handling(self):
        """Test sync generic exception handling."""
        from fastapi import HTTPException

        @fastapi_error_handler(operation="test operation")
        def test_func():
            raise ValueError("Bad value")

        with pytest.raises(HTTPException) as exc_info:
            test_func()

        assert exc_info.value.status_code == 500


class TestRetryLogic:
    """Test retry functionality."""

    def test_retry_on_connection_error(self):
        """Test retry logic for transient failures."""
        call_count = 0

        @with_retry(max_attempts=3, delay=0.01, exceptions=(ConnectionError,))
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient failure")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Test when all retry attempts fail."""

        @with_retry(max_attempts=2, delay=0.01, exceptions=(ValueError,))
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError) as exc_info:
            always_fails()

        assert str(exc_info.value) == "Always fails"


class TestErrorContext:
    """Test error context manager."""

    def test_error_context_success(self):
        """Test error context with successful operation."""
        with error_context("test operation", reraise=False):
            result = 1 + 1

        assert result == 2

    def test_error_context_with_error(self):
        """Test error context with error."""
        with pytest.raises(ValueError):
            with error_context("test operation"):
                raise ValueError("Test error")


class TestErrorAccumulator:
    """Test error accumulator."""

    def test_accumulate_errors(self):
        """Test accumulating multiple errors."""
        accumulator = ErrorAccumulator()

        accumulator.add("Operation 1", ValueError("Bad value"))
        accumulator.add("Operation 2", TypeError("Wrong type"))

        assert accumulator.has_errors()
        assert len(accumulator.errors) == 2

        summary = accumulator.get_summary()
        assert "Operation 1" in summary
        assert "Bad value" in summary
        assert "Operation 2" in summary
        assert "Wrong type" in summary

    def test_to_http_response_with_errors(self):
        """Test converting errors to HTTP response."""
        accumulator = ErrorAccumulator()
        accumulator.add("Field validation", ValueError("Invalid email"))

        response = accumulator.to_http_response(status_code=400)
        assert response.status_code == 400

        # Parse JSON content
        import json

        content = json.loads(response.body)
        assert content["error"]["code"] == "MULTIPLE_ERRORS"
        assert len(content["error"]["details"]["errors"]) == 1

    def test_add_validation_error(self):
        """Test adding validation errors."""
        accumulator = ErrorAccumulator()
        accumulator.add_validation_error("email", "Invalid format")

        assert accumulator.has_errors()
        assert "email" in accumulator.get_summary()


class TestManagedOperation:
    """Test managed operation context manager."""

    @pytest.mark.asyncio
    async def test_managed_operation_success(self):
        """Test managed operation with successful completion."""
        ws_manager = AsyncMock()

        async with managed_operation(
            "test_operation",
            broadcast_start=True,
            broadcast_complete=True,
            ws_manager=ws_manager,
            metadata={"key": "value"},
        ) as request_id:
            assert request_id.startswith("req-")
            # Simulate operation
            await asyncio.sleep(0.01)

        # Check broadcasts
        assert ws_manager.broadcast.call_count == 2
        start_call = ws_manager.broadcast.call_args_list[0][0][0]
        assert start_call["type"] == "test_operation_start"
        assert start_call["key"] == "value"

        complete_call = ws_manager.broadcast.call_args_list[1][0][0]
        assert complete_call["type"] == "test_operation_complete"

    @pytest.mark.asyncio
    async def test_managed_operation_with_error(self):
        """Test managed operation with error."""
        ws_manager = AsyncMock()

        with pytest.raises(ValueError):
            async with managed_operation(
                "test_operation", broadcast_start=True, ws_manager=ws_manager
            ):
                raise ValueError("Test error")

        # Check error broadcast
        error_call = ws_manager.broadcast.call_args_list[-1][0][0]
        assert error_call["type"] == "test_operation_error"
        assert "error" in error_call


# Run with: uv run pytest captain/tests/test_blocks_error_handling_simple.py -v
