#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial test implementation for error_utils module
# - Test all error handling utilities
# - Use real exceptions and scenarios instead of mocking
#

"""
Test suite for error handling utilities.

Tests all functions and classes in captain.utils.shared.error_utils with real
error scenarios to ensure proper error handling in production.
"""

import logging
import time
import pytest
from captain.utils.shared.error_utils import (
    safe_execute,
    with_error_handling,
    with_retry,
    error_context,
    ErrorAccumulator,
    format_exception_chain,
    create_error_handler,
)


class TestSafeExecute:
    """Test safe_execute function."""

    def test_safe_execute_success(self):
        """Test safe execution of successful function."""

        def successful_func(x, y):
            return x + y

        result = safe_execute(successful_func, 2, 3)
        assert result == 5

    def test_safe_execute_with_kwargs(self):
        """Test safe execution with keyword arguments."""

        def func_with_kwargs(a, b=10):
            return a * b

        result = safe_execute(func_with_kwargs, 5, b=20)
        assert result == 100

    def test_safe_execute_exception(self):
        """Test safe execution returns default on exception."""

        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func, default=42)
        assert result == 42

    def test_safe_execute_none_default(self):
        """Test safe execution with None as default."""

        def failing_func():
            raise RuntimeError("Error")

        result = safe_execute(failing_func, default=None)
        assert result is None

    def test_safe_execute_with_logger(self, caplog):
        """Test safe execution logs errors when logger provided."""
        logger = logging.getLogger("test_logger")

        def failing_func():
            raise ValueError("Test error message")

        with caplog.at_level(logging.ERROR):
            result = safe_execute(
                failing_func,
                default="default_value",
                logger=logger,
                error_message="Custom error occurred",
            )

        assert result == "default_value"
        assert "Custom error occurred: Test error message" in caplog.text

    def test_safe_execute_complex_return(self):
        """Test safe execution with complex return types."""

        def complex_func():
            return {"status": "success", "data": [1, 2, 3]}

        result = safe_execute(complex_func)
        assert result == {"status": "success", "data": [1, 2, 3]}


class TestWithErrorHandling:
    """Test with_error_handling decorator."""

    def test_decorator_success(self):
        """Test decorator with successful function."""

        @with_error_handling(default="error")
        def successful_func(x, y):
            return x * y

        result = successful_func(3, 4)
        assert result == 12

    def test_decorator_with_exception(self):
        """Test decorator returns default on exception."""

        @with_error_handling(default=99)
        def failing_func():
            raise ValueError("Test error")

        result = failing_func()
        assert result == 99

    def test_decorator_with_logger(self, caplog):
        """Test decorator logs errors."""
        logger = logging.getLogger("test_decorator")

        @with_error_handling(default="failed", logger=logger, error_message="Error in {func_name}")
        def test_function():
            raise RuntimeError("Something went wrong")

        with caplog.at_level(logging.ERROR):
            result = test_function()

        assert result == "failed"
        assert "Error in test_function: Something went wrong" in caplog.text

    def test_decorator_reraise(self):
        """Test decorator can re-raise exceptions."""

        @with_error_handling(reraise=True)
        def failing_func():
            raise ValueError("Should be re-raised")

        with pytest.raises(ValueError, match="Should be re-raised"):
            failing_func()

    def test_decorator_specific_exceptions(self):
        """Test decorator catches only specific exceptions."""

        @with_error_handling(default="caught", exceptions=(ValueError, TypeError))
        def multi_error_func(error_type):
            if error_type == "value":
                raise ValueError("Value error")
            elif error_type == "type":
                raise TypeError("Type error")
            elif error_type == "runtime":
                raise RuntimeError("Runtime error")
            return "success"

        # Caught exceptions
        assert multi_error_func("value") == "caught"
        assert multi_error_func("type") == "caught"

        # Not caught exception
        with pytest.raises(RuntimeError):
            multi_error_func("runtime")

        # Success case
        assert multi_error_func("none") == "success"

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves original function metadata."""

        @with_error_handling()
        def documented_func():
            """This is a documented function."""
            return "result"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a documented function."


class TestWithRetry:
    """Test with_retry decorator."""

    def test_retry_eventual_success(self):
        """Test retry succeeds after failures."""
        attempt_count = 0

        @with_retry(max_attempts=3, delay=0.01, backoff=1.0)
        def eventually_succeeds():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert attempt_count == 3

    def test_retry_all_attempts_fail(self):
        """Test retry fails after max attempts."""
        attempt_count = 0

        @with_retry(max_attempts=2, delay=0.01)
        def always_fails():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError(f"Attempt {attempt_count}")

        with pytest.raises(ValueError, match="Attempt 2"):
            always_fails()

        assert attempt_count == 2

    def test_retry_with_backoff(self):
        """Test retry with exponential backoff."""
        start_time = time.time()

        @with_retry(max_attempts=3, delay=0.1, backoff=2.0)
        def measure_backoff():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            measure_backoff()

        # Should take at least 0.1 + 0.2 = 0.3 seconds
        elapsed = time.time() - start_time
        assert elapsed >= 0.3

    def test_retry_specific_exceptions(self):
        """Test retry only on specific exceptions."""
        attempt_count = 0

        @with_retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def different_errors():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ValueError("Retryable")
            else:
                raise RuntimeError("Not retryable")

        # RuntimeError should not be retried, so it raises immediately
        with pytest.raises(RuntimeError, match="Not retryable"):
            different_errors()

    def test_retry_with_logger(self, caplog):
        """Test retry logs attempts."""
        logger = logging.getLogger("retry_logger")
        attempt_count = 0

        @with_retry(max_attempts=2, delay=0.01, logger=logger)
        def logged_retry():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError(f"Attempt {attempt_count} failed")

        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError):
                logged_retry()

        assert "Attempt 1/2 failed for logged_retry" in caplog.text
        assert "All 2 attempts failed for logged_retry" in caplog.text


class TestErrorContext:
    """Test error_context context manager."""

    def test_error_context_success(self):
        """Test error context with successful operation."""
        with error_context("performing test operation"):
            result = 1 + 1

        assert result == 2

    def test_error_context_with_exception(self):
        """Test error context with exception."""
        with pytest.raises(ValueError):
            with error_context("failing operation"):
                raise ValueError("Test error")

    def test_error_context_with_logger(self, caplog):
        """Test error context logs errors."""
        logger = logging.getLogger("context_logger")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                with error_context("database operation", logger=logger):
                    raise RuntimeError("Connection failed")

        assert "Error while database operation: Connection failed" in caplog.text

    def test_error_context_no_reraise(self):
        """Test error context can suppress exceptions."""
        with error_context("suppressed operation", reraise=False):
            raise ValueError("This is suppressed")

        # Should not raise


class TestErrorAccumulator:
    """Test ErrorAccumulator class."""

    def test_accumulator_basic(self):
        """Test basic error accumulation."""
        accumulator = ErrorAccumulator()

        assert not accumulator.has_errors()

        accumulator.add("operation1", ValueError("Error 1"))
        accumulator.add("operation2", TypeError("Error 2"))

        assert accumulator.has_errors()
        assert len(accumulator.errors) == 2

    def test_accumulator_from_callable(self):
        """Test accumulating errors from callable."""
        accumulator = ErrorAccumulator()

        def successful_func():
            return "success"

        def failing_func():
            raise RuntimeError("Failed")

        result1 = accumulator.add_from_callable("success_op", successful_func)
        assert result1 == "success"

        result2 = accumulator.add_from_callable("fail_op", failing_func)
        assert result2 is None

        assert accumulator.has_errors()
        assert len(accumulator.errors) == 1
        assert accumulator.errors[0][0] == "fail_op"

    def test_accumulator_summary(self):
        """Test error summary generation."""
        accumulator = ErrorAccumulator()

        # No errors
        assert accumulator.get_summary() == "No errors"

        # With errors
        accumulator.add("step1", ValueError("Value error"))
        accumulator.add("step2", TypeError("Type error"))

        summary = accumulator.get_summary()
        assert "Errors encountered:" in summary
        assert "step1: Value error" in summary
        assert "step2: Type error" in summary

    def test_accumulator_raise_if_errors(self):
        """Test raising accumulated errors."""
        accumulator = ErrorAccumulator()

        # No errors - should not raise
        accumulator.raise_if_errors()

        # With errors - should raise
        accumulator.add("test", ValueError("Test error"))

        with pytest.raises(Exception) as exc_info:
            accumulator.raise_if_errors("Custom message")

        assert "Custom message" in str(exc_info.value)
        assert "test: Test error" in str(exc_info.value)

    def test_accumulator_clear(self):
        """Test clearing accumulated errors."""
        accumulator = ErrorAccumulator()

        accumulator.add("error1", ValueError("Error"))
        assert accumulator.has_errors()

        accumulator.clear()
        assert not accumulator.has_errors()
        assert len(accumulator.errors) == 0


class TestFormatExceptionChain:
    """Test format_exception_chain function."""

    def test_format_single_exception(self):
        """Test formatting single exception."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            formatted = format_exception_chain(e)
            assert formatted == "ValueError: Test error"

    def test_format_exception_chain_simple(self):
        """Test formatting chained exceptions."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise RuntimeError("Wrapper error") from e
        except RuntimeError as e:
            formatted = format_exception_chain(e)
            assert "RuntimeError: Wrapper error" in formatted
            assert "ValueError: Original error" in formatted
            assert " -> " in formatted

    def test_format_exception_with_traceback(self):
        """Test formatting with traceback included."""
        try:
            raise TypeError("Type mismatch")
        except TypeError as e:
            formatted = format_exception_chain(e, include_traceback=True)
            assert "Traceback" in formatted
            assert "TypeError: Type mismatch" in formatted
            assert "test_format_exception_with_traceback" in formatted

    def test_format_complex_chain(self):
        """Test formatting complex exception chain."""
        try:
            try:
                try:
                    raise KeyError("Missing key")
                except KeyError as e:
                    raise ValueError("Invalid value") from e
            except ValueError as e:
                raise RuntimeError("Operation failed") from e
        except RuntimeError as e:
            formatted = format_exception_chain(e)
            # Should show all three exceptions in chain
            assert "RuntimeError: Operation failed" in formatted
            assert "ValueError: Invalid value" in formatted
            assert "KeyError: 'Missing key'" in formatted


class TestCreateErrorHandler:
    """Test create_error_handler function."""

    def test_create_basic_handler(self, caplog):
        """Test creating basic error handler."""
        logger = logging.getLogger("handler_logger")
        handler = create_error_handler(logger)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                try:
                    raise ValueError("Test error")
                except ValueError as e:
                    handler(e)

        assert "Unhandled error: Test error" in caplog.text

    def test_create_handler_with_mapping(self):
        """Test error handler with custom mappings."""
        logger = logging.getLogger("mapped_handler")

        handled_errors = []

        def handle_value_error(e):
            handled_errors.append(("value", str(e)))
            return "handled_value"

        def handle_type_error(e):
            handled_errors.append(("type", str(e)))
            return "handled_type"

        error_mapping = {
            ValueError: handle_value_error,
            TypeError: handle_type_error,
        }

        handler = create_error_handler(logger, error_mapping)

        # Test mapped exceptions
        try:
            raise ValueError("Value problem")
        except ValueError as e:
            result = handler(e)
            assert result == "handled_value"
            assert handled_errors[-1] == ("value", "Value problem")

        try:
            raise TypeError("Type problem")
        except TypeError as e:
            result = handler(e)
            assert result == "handled_type"
            assert handled_errors[-1] == ("type", "Type problem")

        # Test unmapped exception
        with pytest.raises(RuntimeError):
            try:
                raise RuntimeError("Unmapped error")
            except RuntimeError as e:
                handler(e)

    def test_handler_inheritance(self):
        """Test handler respects exception inheritance."""
        logger = logging.getLogger("inheritance_handler")

        class CustomError(ValueError):
            pass

        def handle_value_error(e):
            return f"Handled: {e}"

        error_mapping = {ValueError: handle_value_error}
        handler = create_error_handler(logger, error_mapping)

        # CustomError inherits from ValueError, should be handled
        try:
            raise CustomError("Custom error")
        except CustomError as e:
            result = handler(e)
            assert result == "Handled: Custom error"
