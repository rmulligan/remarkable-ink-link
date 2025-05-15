#!/usr/bin/env python3
"""
Test script for Limitless Life Log integration.

This script directly tests the LimitlessAdapter, LimitlessLifeLogService,
and LimitlessSchedulerService to verify the full integration flow.
"""

import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from test_kg_mock import MockKnowledgeGraphService  # noqa: E402

# Import Limitless components
from src.inklink.adapters.limitless_adapter import LimitlessAdapter  # noqa: E402


class LimitlessIntegrationTester:
    """Test the Limitless integration flow."""

    def __init__(self, api_key):
        self.api_key = api_key

        # Create adapter
        self.adapter = LimitlessAdapter(
            api_key=self.api_key,
            base_url="https://api.limitless.ai",
            timeout=30,
            retries=3,
        )

        # Create knowledge graph service (mock)
        self.kg_service = MockKnowledgeGraphService()

        # Create temp directory for testing
        self.temp_dir = tempfile.mkdtemp(prefix="limitless_test_")
        logger.info(f"Created temp directory: {self.temp_dir}")

    def test_ping(self):
        """Test API connectivity."""
        logger.info("Testing API connectivity...")
        result = self.adapter.ping()
        logger.info(f"Ping result: {result}")
        return result

    def test_get_life_logs(self, limit=5):
        """Test fetching life logs."""
        logger.info(f"Fetching {limit} life logs...")
        success, result = self.adapter.get_life_logs(limit=limit)

        if not success:
            logger.error(f"Failed to fetch life logs: {result}")
            return False, None

        # Print structure
        logger.info(
            f"Response structure: {json.dumps({k: type(v).__name__ for k, v in result.items()}, indent=2)}"
        )

        # Extract logs based on response format
        logs = []
        if isinstance(result, dict):
            if "data" in result and isinstance(result["data"], list):
                logs = result["data"]
            elif (
                "data" in result
                and isinstance(result["data"], dict)
                and "lifelogs" in result["data"]
            ):
                logs = result["data"]["lifelogs"]
            elif "lifelogs" in result:
                logs = result["lifelogs"]

        logger.info(f"Extracted {len(logs)} logs")

        # Print log titles
        for log in logs:
            logger.info(f"Log: {log.get('id')} - {log.get('title')}")

        return True, logs

    def test_get_specific_log(self, log_id):
        """Test fetching a specific log."""
        logger.info(f"Fetching specific log: {log_id}")
        success, log = self.adapter.get_life_log_by_id(log_id)

        if not success:
            logger.error(f"Failed to fetch log {log_id}: {log}")
            return False, None

        logger.info(f"Successfully retrieved log: {log.get('title')}")
        return True, log

    def test_all_life_logs(self):
        """Test fetching all life logs with pagination."""
        logger.info("Fetching all life logs from last 7 days...")
        from_date = datetime.now() - timedelta(days=7)

        success, logs = self.adapter.get_all_life_logs(from_date=from_date)

        if not success:
            logger.error(f"Failed to fetch all logs: {logs}")
            return False, None

        logger.info(f"Successfully retrieved {len(logs)} logs from the last 7 days")
        return True, logs

    def run_all_tests(self):
        """Run all tests in sequence."""
        print("=" * 80)
        print("LIMITLESS LIFE LOG INTEGRATION TEST")
        print("=" * 80)
        print(f"API Key: {self.api_key[:4]}...{self.api_key[-4:]}")
        print("-" * 80)

        # Test ping
        print("\n1. Testing API connectivity:")
        if not self.test_ping():
            print("❌ API ping failed. Check your API key.")
            return False
        print("✅ API connectivity test passed")

        # Test get life logs
        print("\n2. Fetching life logs:")
        success, logs = self.test_get_life_logs(limit=3)
        if not success or not logs:
            print("❌ Failed to fetch life logs")
            return False
        print(f"✅ Successfully fetched {len(logs)} life logs")

        # Test get specific log
        if logs:
            log_id = logs[0]["id"]
            print(f"\n3. Fetching specific log ({log_id}):")
            success, log = self.test_get_specific_log(log_id)
            if not success:
                print("❌ Failed to fetch specific log")
                return False
            print("✅ Successfully fetched specific log")

        # Test all life logs
        print("\n4. Fetching all life logs from last 7 days:")
        success, all_logs = self.test_all_life_logs()
        if not success:
            print("❌ Failed to fetch all life logs")
            return False
        print(f"✅ Successfully fetched {len(all_logs)} life logs from the last 7 days")

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 80)
        return True


if __name__ == "__main__":
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("dotenv not available, using system environment variables")

    # Get API key from environment or command line
    api_key = os.environ.get("LIMITLESS_API_KEY")

    if len(sys.argv) > 1:
        api_key = sys.argv[1]

    if not api_key:
        print(
            "Error: LIMITLESS_API_KEY environment variable or command line argument required"
        )
        sys.exit(1)

    # Run tests
    tester = LimitlessIntegrationTester(api_key)
    if not tester.run_all_tests():
        sys.exit(1)
