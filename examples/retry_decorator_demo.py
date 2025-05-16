"""Example demonstrating the use of the retry decorator for critical operations."""

import logging
import random
import time
from typing import Any, Dict

import requests

from inklink.utils.retry import RetryError, retry

# Set up logging to see retry attempts
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class APIClient:
    """Example API client that uses retry decorator for resilient operations."""

    def __init__(self, base_url: str = "https://api.example.com"):
        self.base_url = base_url
        self.request_count = 0

    @retry(
        max_attempts=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException,),
        logger=logger,
    )
    def make_api_request(self, endpoint: str) -> Dict[str, Any]:
        """
        Make an API request with automatic retry on failure.

        This will retry up to 3 times with exponential backoff
        if the request fails with a network-related exception.
        """
        self.request_count += 1
        logger.info(f"Making request #{self.request_count} to {endpoint}")

        # Simulate occasional failures
        if self.request_count < 3 and random.random() < 0.5:
            logger.warning(f"Simulating request failure #{self.request_count}")
            raise requests.exceptions.ConnectionError("Connection failed")

        # Simulate successful response
        return {"status": "success", "data": {"message": "API request successful"}}

    @retry(
        max_attempts=5,
        base_delay=2.0,
        max_delay=10.0,
        jitter=True,
        exceptions=(ConnectionError, TimeoutError),
        on_retry=lambda e, attempt: logger.warning(
            f"Custom retry callback: attempt {attempt}, error: {e}"
        ),
    )
    def complex_operation(self) -> str:
        """
        Demonstrate a more complex retry configuration with:
        - More attempts (5)
        - Custom exceptions
        - Maximum delay cap
        - Jitter for preventing thundering herd
        - Custom retry callback
        """
        self.request_count += 1
        logger.info(f"Attempting complex operation #{self.request_count}")

        # Simulate failures with different error types
        if self.request_count < 4:
            if random.random() < 0.5:
                raise ConnectionError("Network connection lost")
            else:
                raise TimeoutError("Operation timed out")

        return "Complex operation completed successfully"


def main():
    """Demonstrate retry decorator usage."""
    client = APIClient()

    # Example 1: Simple API request with retry
    print("\n=== Example 1: API Request with Retry ===")
    try:
        result = client.make_api_request("/users/123")
        print(f"Success: {result}")
    except RetryError as e:
        print(f"Failed after all retries: {e}")
        if e.last_error:
            print(f"Last error was: {e.last_error}")

    # Reset request count
    client.request_count = 0

    # Example 2: Complex operation with custom retry configuration
    print("\n=== Example 2: Complex Operation with Custom Retry ===")
    try:
        result = client.complex_operation()
        print(f"Success: {result}")
    except RetryError as e:
        print(f"Failed after all retries: {e}")

    # Example 3: Synchronous function with immediate success
    print("\n=== Example 3: Immediate Success ===")

    @retry(max_attempts=3)
    def always_works():
        logger.info("This function always succeeds on first try")
        return "Immediate success"

    result = always_works()
    print(f"Result: {result}")

    # Example 4: Retry with specific exceptions only
    print("\n=== Example 4: Specific Exception Handling ===")

    @retry(max_attempts=3, exceptions=(ValueError,))
    def selective_retry():
        # This will not retry TypeError but will retry ValueError
        if random.random() < 0.5:
            raise ValueError("This will be retried")
        else:
            raise TypeError("This won't be retried")

    try:
        selective_retry()
    except (RetryError, TypeError) as e:
        print(f"Function failed: {e}")


if __name__ == "__main__":
    main()
