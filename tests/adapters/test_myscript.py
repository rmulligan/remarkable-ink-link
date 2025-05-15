#!/usr/bin/env python3
"""
Test script for MyScript iink SDK integration.

This script tests the handwriting recognition service using the MyScript iink SDK.
"""

import os
import sys
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the necessary components
from src.inklink.services.handwriting_recognition_service import (  # noqa: E402
    HandwritingRecognitionService,
)


class MyScriptTest:
    """Test the MyScript iink SDK integration."""

    def __init__(self):
        """Initialize the test environment."""
        # Get credentials from environment or prompt
        self.app_key = os.environ.get("MYSCRIPT_APP_KEY")
        self.hmac_key = os.environ.get("MYSCRIPT_HMAC_KEY")

        if not self.app_key or not self.hmac_key:
            logger.error("MyScript keys not found in environment variables!")
            sys.exit(1)

        logger.info(f"Using MyScript App Key: {self.app_key[:8]}...{self.app_key[-8:]}")
        logger.info(
            f"Using MyScript HMAC Key: {self.hmac_key[:8]}...{self.hmac_key[-8:]}"
        )

        # Create the handwriting recognition service
        self.service = HandwritingRecognitionService()

    def test_initialization(self):
        """Test initialization of the SDK."""
        logger.info("Testing iink SDK initialization...")
        result = self.service.initialize_iink_sdk(self.app_key, self.hmac_key)

        if result:
            logger.info("✅ iink SDK initialized successfully")
        else:
            logger.error("❌ Failed to initialize iink SDK")

        return result

    def run_tests(self):
        """Run all tests."""
        print("\n" + "=" * 80)
        print("MYSCRIPT IINK SDK INTEGRATION TEST")
        print("=" * 80)

        # Test SDK initialization
        print("\nTest: SDK Initialization")
        initialization_success = self.test_initialization()

        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        # Report initialization status
        initialization_status = "✅ PASSED" if initialization_success else "❌ FAILED"
        print(f"SDK Initialization: {initialization_status}")

        # Overall status
        if initialization_success:
            print("\nMyScript iink SDK integration is working correctly!")
        else:
            print("\nMyScript iink SDK integration has issues. See logs for details.")


if __name__ == "__main__":
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("dotenv not available, using system environment variables")

    # Run tests
    test = MyScriptTest()
    test.run_tests()
