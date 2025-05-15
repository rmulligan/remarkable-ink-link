#!/usr/bin/env python3
"""
Test script for Limitless endpoints.

This script tests the Limitless API endpoints directly, without needing
the full InkLink server to be running. It creates a lightweight application
instance just to test the Limitless integration functionality.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import necessary components from the project
from src.inklink.adapters.limitless_adapter import LimitlessAdapter  # noqa: E402
from src.inklink.services.limitless_life_log_service import (  # noqa: E402
    LimitlessLifeLogService,
)
from src.inklink.services.limitless_scheduler_service import (  # noqa: E402
    LimitlessSchedulerService,
)


class LimitlessLiveTest:
    """Test the Limitless API integration."""

    def __init__(self):
        """Initialize the test environment."""
        self.api_key = os.environ.get("LIMITLESS_API_KEY")
        if not self.api_key:
            logger.error("LIMITLESS_API_KEY environment variable not set!")
            sys.exit(1)

        logger.info(f"Using API key: {self.api_key[:4]}...{self.api_key[-4:]}")

        # Create adapter
        self.adapter = LimitlessAdapter(
            api_key=self.api_key,
            base_url="https://api.limitless.ai",
            timeout=30,
            retries=3,
        )

        # Create temp directory
        os.makedirs("/tmp/limitless_test", exist_ok=True)

        # Create mock knowledge graph service
        from tests.mocks.test_kg_mock import MockKnowledgeGraphService

        self.kg_service = MockKnowledgeGraphService()

        # Create services
        self.service = LimitlessLifeLogService(
            limitless_adapter=self.adapter,
            knowledge_graph_service=self.kg_service,
            storage_path="/tmp/limitless_test",
        )

        self.scheduler = LimitlessSchedulerService(
            limitless_service=self.service,
            sync_interval=3600,  # 1 hour
            initial_delay=5,  # 5 seconds
        )

    def test_adapter_ping(self):
        """Test API connectivity."""
        logger.info("Testing Limitless API connectivity...")
        result = self.adapter.ping()
        if result:
            logger.info("✅ Limitless API connection successful")
        else:
            logger.error("❌ Limitless API connection failed")
        return result

    def test_get_life_logs(self, limit=3):
        """Test fetching life logs."""
        logger.info(f"Fetching {limit} life logs...")
        success, result = self.adapter.get_life_logs(limit=limit)

        if not success:
            logger.error(f"❌ Failed to fetch life logs: {result}")
            return False

        # Print structure
        logger.info(
            f"API response structure: {json.dumps({k: type(v).__name__ for k, v in result.items()}, indent=2)}"
        )

        # Extract logs
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

        logger.info(f"✅ Successfully extracted {len(logs)} logs")

        # Print log details
        for i, log in enumerate(logs):
            logger.info(f"Log {i + 1}:")
            logger.info(f"  ID: {log.get('id')}")
            logger.info(f"  Title: {log.get('title')}")
            logger.info(f"  Time: {log.get('startTime')} to {log.get('endTime')}")

        return True

    def test_sync_service(self):
        """Test syncing life logs."""
        logger.info("Testing Limitless sync service...")
        success, message = self.service.sync_life_logs()

        if success:
            logger.info(f"✅ Sync successful: {message}")
        else:
            logger.error(f"❌ Sync failed: {message}")

        return success

    def test_scheduler(self):
        """Test scheduler functionality."""
        logger.info("Testing scheduler functionality...")

        # Start scheduler
        self.scheduler.start()
        status = self.scheduler.get_status()
        logger.info(f"Scheduler status after start: {json.dumps(status, indent=2)}")

        # Wait for initial sync
        logger.info("Waiting for initial sync to complete...")
        time.sleep(10)

        # Get updated status
        status = self.scheduler.get_status()
        logger.info(
            f"Scheduler status after initial sync: {json.dumps(status, indent=2)}"
        )

        # Stop scheduler
        self.scheduler.stop()
        status = self.scheduler.get_status()
        logger.info(f"Scheduler status after stop: {json.dumps(status, indent=2)}")

        return True

    def test_manual_trigger(self):
        """Test manual sync trigger."""
        logger.info("Testing manual sync trigger...")

        result = self.scheduler.trigger_sync()
        logger.info(f"Trigger sync result: {json.dumps(result, indent=2)}")

        if result.get("success"):
            logger.info("✅ Manual sync trigger successful")
            return True
        else:
            logger.error("❌ Manual sync trigger failed")
            return False

    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "=" * 80)
        print("LIMITLESS INTEGRATION LIVE TEST")
        print("=" * 80)

        results = {}

        # Test 1: Connectivity
        print("\nTest 1: API Connectivity")
        results["connectivity"] = self.test_adapter_ping()

        # Test 2: List Life Logs
        print("\nTest 2: List Life Logs")
        results["list_logs"] = self.test_get_life_logs()

        # Test 3: Sync Service
        print("\nTest 3: Sync Service")
        results["sync_service"] = self.test_sync_service()

        # Test 4: Scheduler
        print("\nTest 4: Scheduler")
        results["scheduler"] = self.test_scheduler()

        # Test 5: Manual Trigger
        print("\nTest 5: Manual Trigger")
        results["manual_trigger"] = self.test_manual_trigger()

        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        for test, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test.replace('_', ' ').title()}: {status}")

        if all(results.values()):
            print("\nAll tests passed successfully!")
        else:
            print("\nSome tests failed. See log for details.")


if __name__ == "__main__":
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("dotenv not available, using system environment variables")

    # Run tests
    test = LimitlessLiveTest()
    test.run_all_tests()
