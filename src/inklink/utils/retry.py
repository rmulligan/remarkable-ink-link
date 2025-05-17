"""Retry decorator for critical operations with exponential backoff."""

import asyncio
import functools
import logging
import random
from typing import Any, Callable, Optional, Type, Union

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, message: str, last_error: Optional[Exception] = None):
        super().__init__(message)
        self.last_error = last_error


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    logger: Optional[logging.Logger] = None,
) -> Callable:
    """
    Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (including the first attempt)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to prevent thundering herd
        exceptions: Tuple of exceptions to catch and retry on
        on_retry: Optional callback to call on each retry with (exception, attempt_number)
        logger: Optional logger to use for retry attempts

    Returns:
        Decorated function that implements retry logic
    """

    def decorator(func: Callable) -> Callable:
        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            nonlocal logger
            if logger is None:
                logger = globals()["logger"]

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
                        raise RetryError(
                            f"All {max_attempts} attempts failed for {func.__name__}",
                            last_error=e,
                        )

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)), max_delay
                    )

                    # Add jitter if enabled
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # Call optional retry callback
                    if on_retry:
                        on_retry(e, attempt)

                    await asyncio.sleep(delay)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            nonlocal logger
            if logger is None:
                logger = globals()["logger"]

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
                        raise RetryError(
                            f"All {max_attempts} attempts failed for {func.__name__}",
                            last_error=e,
                        )

                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)), max_delay
                    )

                    # Add jitter if enabled
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # Call optional retry callback
                    if on_retry:
                        on_retry(e, attempt)

                    import time

                    time.sleep(delay)

        return async_wrapper if is_async else sync_wrapper

    return decorator
