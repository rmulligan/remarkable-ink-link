"""Tests for the retry decorator."""

import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from inklink.utils.retry import RetryError, retry


class TestRetryError(Exception):
    """Test exception for retry tests."""

    pass


class TestRetryDecorator:
    """Test cases for the retry decorator."""

    def test_sync_success_first_attempt(self):
        """Test sync function that succeeds on first attempt."""
        call_count = 0

        @retry(max_attempts=3)
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 1

    def test_sync_success_after_retries(self):
        """Test sync function that succeeds after retries."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(TestRetryError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TestRetryError("Temporary failure")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 3

    def test_sync_max_attempts_exceeded(self):
        """Test sync function that exceeds max attempts."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(TestRetryError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            raise TestRetryError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            test_func()

        assert call_count == 3
        assert exc_info.value.last_error is not None
        assert isinstance(exc_info.value.last_error, TestRetryError)

    @pytest.mark.asyncio
    async def test_async_success_first_attempt(self):
        """Test async function that succeeds on first attempt."""
        call_count = 0

        @retry(max_attempts=3)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_success_after_retries(self):
        """Test async function that succeeds after retries."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, exceptions=(TestRetryError,))
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TestRetryError("Temporary failure")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 3

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        delays = []

        @retry(
            max_attempts=4,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False,
            exceptions=(TestRetryError,),
        )
        def test_func():
            raise TestRetryError("Always fails")

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda d: delays.append(d)
            with pytest.raises(RetryError):
                test_func()

        # Verify exponential backoff: 1s, 2s, 4s
        assert len(delays) == 3
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        delays = []

        @retry(
            max_attempts=5,
            base_delay=1.0,
            max_delay=3.0,
            exponential_base=2.0,
            jitter=False,
            exceptions=(TestRetryError,),
        )
        def test_func():
            raise TestRetryError("Always fails")

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda d: delays.append(d)
            with pytest.raises(RetryError):
                test_func()

        # Verify delays are capped: 1s, 2s, 3s, 3s
        assert len(delays) == 4
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 3.0  # Capped
        assert delays[3] == 3.0  # Capped

    def test_jitter(self):
        """Test that jitter adds randomness to delays."""
        delays = []

        @retry(
            max_attempts=3, base_delay=1.0, jitter=True, exceptions=(TestRetryError,)
        )
        def test_func():
            raise TestRetryError("Always fails")

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda d: delays.append(d)
            with pytest.raises(RetryError):
                test_func()

        # Verify jitter adds variation
        assert len(delays) == 2
        assert 0.5 <= delays[0] <= 1.5  # Jittered around 1s
        assert 1.0 <= delays[1] <= 3.0  # Jittered around 2s

    def test_exception_filtering(self):
        """Test that only specified exceptions trigger retries."""
        call_count = 0

        @retry(max_attempts=3, exceptions=(TestRetryError,))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Not retryable")
            return "success"

        with pytest.raises(ValueError):
            test_func()

        assert call_count == 1  # Should not retry on ValueError

    def test_on_retry_callback(self):
        """Test on_retry callback is called correctly."""
        retry_calls = []

        def on_retry(exception, attempt):
            retry_calls.append((type(exception).__name__, attempt))

        @retry(
            max_attempts=3,
            base_delay=0.01,
            exceptions=(TestRetryError,),
            on_retry=on_retry,
        )
        def test_func():
            raise TestRetryError("Always fails")

        with pytest.raises(RetryError):
            test_func()

        assert len(retry_calls) == 2  # Called on retries, not final failure
        assert retry_calls[0] == ("TestRetryError", 1)
        assert retry_calls[1] == ("TestRetryError", 2)

    def test_custom_logger(self):
        """Test using a custom logger."""
        mock_logger = Mock()

        @retry(
            max_attempts=2,
            base_delay=0.01,
            exceptions=(TestRetryError,),
            logger=mock_logger,
        )
        def test_func():
            raise TestRetryError("Always fails")

        with pytest.raises(RetryError):
            test_func()

        # Verify custom logger was used
        assert mock_logger.warning.call_count == 1
        assert mock_logger.error.call_count == 1

    def test_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""

        @retry()
        def test_func():
            """Test function docstring."""
            return "success"

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."
