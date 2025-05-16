"""Real-world examples of retry decorator usage in InkLink framework."""

import asyncio
import logging
import requests
from typing import Dict, Any

from inklink.utils.retry import retry
from inklink.adapters.handwriting_web_adapter import HandwritingWebAdapter
from inklink.agents.base.lifecycle import AgentLifecycle
from inklink.agents.base.registry import AgentRegistry

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class InkLinkRetryExamples:
    """Examples showing how retry decorator is used in critical InkLink operations."""

    @staticmethod
    def example_handwriting_recognition():
        """Example: Handwriting recognition with MyScript Web API."""
        print("\n=== Handwriting Recognition with Retry ===")

        # Initialize the handwriting adapter (would normally use real API keys)
        adapter = HandwritingWebAdapter(
            application_key="your_app_key", hmac_key="your_hmac_key"
        )

        # The recognize_handwriting method is decorated with retry
        # It will automatically retry on network errors
        ink_data = {
            "contentType": "Text",
            "strokeGroups": [
                {
                    "strokes": [
                        {
                            "x": [100, 110, 120],
                            "y": [100, 105, 110],
                            "t": [1000, 1010, 1020],
                            "p": [0.5, 0.6, 0.7],
                        }
                    ]
                }
            ],
        }

        try:
            # This will retry up to 3 times with exponential backoff
            result = adapter.recognize_handwriting(ink_data)
            print(f"Recognition result: {result}")
        except Exception as e:
            print(f"Recognition failed after retries: {e}")

    @staticmethod
    async def example_agent_restart():
        """Example: Agent restart with retry in lifecycle management."""
        print("\n=== Agent Restart with Retry ===")

        # Create a mock registry for demonstration
        registry = AgentRegistry()
        lifecycle = AgentLifecycle(registry)

        # The _restart_agent method is decorated with retry
        # It will retry the restart operation if it fails
        try:
            # This would be called when an agent enters error state
            await lifecycle._restart_agent("example-agent")
            print("Agent restarted successfully")
        except Exception as e:
            print(f"Agent restart failed after retries: {e}")

    @staticmethod
    def example_custom_retry_operation():
        """Example: Custom operation with retry for critical data processing."""
        print("\n=== Custom Critical Operation with Retry ===")

        @retry(
            max_attempts=5,
            base_delay=2.0,
            max_delay=30.0,
            exceptions=(IOError, requests.exceptions.RequestException),
            logger=logger,
        )
        def process_notebook_upload(
            notebook_path: str, remote_url: str
        ) -> Dict[str, Any]:
            """
            Upload a notebook to remote storage with automatic retry.

            This simulates a critical operation that might fail due to:
            - Network issues
            - Temporary server unavailability
            - File system errors
            """
            logger.info(f"Uploading notebook {notebook_path} to {remote_url}")

            # Simulate the upload operation
            # In real code, this would use requests or similar
            import random

            if random.random() < 0.3:  # 30% chance of failure
                raise requests.exceptions.ConnectionError("Upload failed")

            return {
                "status": "success",
                "notebook_id": "12345",
                "upload_time": "2024-01-15T10:30:00Z",
            }

        try:
            result = process_notebook_upload(
                "/path/to/notebook.pdf", "https://cloud.remarkable.com/api/v1/upload"
            )
            print(f"Upload successful: {result}")
        except Exception as e:
            print(f"Upload failed after all retries: {e}")

    @staticmethod
    def example_retry_in_api_calls():
        """Example: API calls with different retry strategies."""
        print("\n=== API Calls with Different Retry Strategies ===")

        # Fast retry for ping/health checks
        @retry(
            max_attempts=2, base_delay=0.5, exceptions=(requests.exceptions.Timeout,)
        )
        def health_check(url: str) -> bool:
            """Quick health check with minimal retry."""
            response = requests.get(f"{url}/health", timeout=2)
            return response.status_code == 200

        # Slower retry for data operations
        @retry(
            max_attempts=4,
            base_delay=3.0,
            exponential_base=2.0,
            max_delay=20.0,
            exceptions=(requests.exceptions.RequestException,),
        )
        def fetch_user_data(user_id: str) -> Dict[str, Any]:
            """Fetch user data with robust retry strategy."""
            response = requests.get(
                f"https://api.example.com/users/{user_id}", timeout=10
            )
            response.raise_for_status()
            return response.json()

        print(
            "Health check and data fetching operations are now resilient to failures!"
        )


def main():
    """Run all examples."""
    examples = InkLinkRetryExamples()

    # Run sync examples
    examples.example_handwriting_recognition()
    examples.example_custom_retry_operation()
    examples.example_retry_in_api_calls()

    # Run async example
    print("\nRunning async example...")
    asyncio.run(examples.example_agent_restart())

    print("\n=== Summary ===")
    print("The retry decorator provides:")
    print("- Automatic retry with exponential backoff")
    print("- Configurable retry attempts and delays")
    print("- Exception filtering for selective retry")
    print("- Custom callbacks for monitoring")
    print("- Support for both sync and async functions")
    print("\nUse it for any critical operation that might fail transiently!")


if __name__ == "__main__":
    main()
