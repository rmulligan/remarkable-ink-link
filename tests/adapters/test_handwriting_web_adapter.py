#!/usr/bin/env python3
"""
Test script for MyScript Web API Adapter integration.

This script tests the handwriting recognition using the new HandwritingWebAdapter
which integrates with the MyScript Cloud API instead of the local SDK.
"""

import argparse
import json
import logging
import os
import sys
import tempfile
import time
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
from src.inklink.adapters.handwriting_web_adapter import (  # noqa: E402
    HandwritingWebAdapter,
)
from src.inklink.services.handwriting_recognition_service import (  # noqa: E402
    HandwritingRecognitionService,
)


def create_test_strokes():
    """
    Create test stroke data for recognition testing.

    Returns:
        A list of stroke dictionaries simulating handwritten content
    """
    current_time = int(time.time() * 1000)  # Current time in milliseconds

    # Simple strokes that resemble "hello"
    return [
        # 'h' stroke
        {
            "id": "1",
            "x": [100, 100, 100, 100, 120, 140, 140, 140],
            "y": [100, 120, 140, 160, 160, 160, 140, 120],
            "p": [0.5, 0.6, 0.7, 0.7, 0.6, 0.5, 0.6, 0.7],
            "t": [
                current_time,
                current_time + 10,
                current_time + 20,
                current_time + 30,
                current_time + 40,
                current_time + 50,
                current_time + 60,
                current_time + 70,
            ],
        },
        # 'e' stroke
        {
            "id": "2",
            "x": [180, 200, 220, 200, 180, 180, 200, 220],
            "y": [140, 130, 140, 150, 160, 140, 140, 140],
            "p": [0.5, 0.6, 0.7, 0.6, 0.5, 0.5, 0.5, 0.5],
            "t": [
                current_time + 100,
                current_time + 110,
                current_time + 120,
                current_time + 130,
                current_time + 140,
                current_time + 150,
                current_time + 160,
                current_time + 170,
            ],
        },
        # 'l' stroke
        {
            "id": "3",
            "x": [240, 240, 240, 240],
            "y": [100, 120, 140, 160],
            "p": [0.5, 0.6, 0.7, 0.5],
            "t": [
                current_time + 200,
                current_time + 210,
                current_time + 220,
                current_time + 230,
            ],
        },
        # 'l' stroke
        {
            "id": "4",
            "x": [280, 280, 280, 280],
            "y": [100, 120, 140, 160],
            "p": [0.5, 0.6, 0.7, 0.5],
            "t": [
                current_time + 300,
                current_time + 310,
                current_time + 320,
                current_time + 330,
            ],
        },
        # 'o' stroke
        {
            "id": "5",
            "x": [320, 340, 360, 360, 340, 320, 320],
            "y": [140, 120, 140, 160, 180, 160, 140],
            "p": [0.5, 0.6, 0.7, 0.7, 0.6, 0.5, 0.5],
            "t": [
                current_time + 400,
                current_time + 410,
                current_time + 420,
                current_time + 430,
                current_time + 440,
                current_time + 450,
                current_time + 460,
            ],
        },
    ]


def create_test_rm_file():
    """
    Create a test .rm file with simple strokes.

    Returns:
        Path to the temporary .rm file
    """
    try:
        # Try to import rmscene for creating test files
        try:
            import rmscene
        except ImportError:
            logger.error("rmscene not installed - cannot create test .rm file")
            return None

        # Create a scene
        scene = rmscene.Scene()

        # Add a layer
        layer = rmscene.Layer()
        scene.layers.append(layer)

        # Add test strokes from the create_test_strokes function
        test_strokes = create_test_strokes()

        # Convert to rmscene lines
        for stroke in test_strokes:
            line = rmscene.Line()

            # Set line properties
            line.width = 2.0
            line.color = "#000000"

            # Add points
            for i in range(len(stroke["x"])):
                point = rmscene.Point()
                point.x = stroke["x"][i]
                point.y = stroke["y"][i]
                point.pressure = stroke["p"][i]
                point.timestamp_ms = stroke["t"][i]
                line.points.append(point)

            # Add line to layer
            layer.lines.append(line)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".rm") as temp_file:
            temp_file.write(scene.to_bytes())
            temp_path = temp_file.name

        logger.info(f"Created test .rm file at {temp_path}")
        return temp_path

    except Exception as e:
        logger.error(f"Failed to create test .rm file: {e}")
        return None


class WebAdapterTester:
    """Test the MyScript Web API Adapter integration."""

    def __init__(self):
        """Initialize the test environment."""
        # Get credentials from environment
        self.app_key = os.environ.get("MYSCRIPT_APP_KEY")
        self.hmac_key = os.environ.get("MYSCRIPT_HMAC_KEY")

        if not self.app_key or not self.hmac_key:
            logger.error("MyScript keys not found in environment variables!")
            sys.exit(1)

        logger.info(
            f"Using MyScript App Key: {self.app_key[:8]}...{self.app_key[-8:] if len(self.app_key) > 16 else ''}"
        )
        logger.info(
            f"Using MyScript HMAC Key: {self.hmac_key[:8]}...{self.hmac_key[-8:] if len(self.hmac_key) > 16 else ''}"
        )

        # Create the HandwritingWebAdapter for direct testing
        self.adapter = HandwritingWebAdapter(
            application_key=self.app_key, hmac_key=self.hmac_key
        )

        # Create the standard HandwritingAdapter that uses WebAdapter internally
        self.std_adapter = HandwritingAdapter(
            application_key=self.app_key, hmac_key=self.hmac_key
        )

        # Create the handwriting recognition service
        self.service = HandwritingRecognitionService(
            application_key=self.app_key, hmac_key=self.hmac_key
        )

    def test_ping(self):
        """Test ping functionality."""
        logger.info("Testing adapter ping...")
        result = self.adapter.ping()

        if result:
            logger.info("✅ Ping successful - API is accessible")
        else:
            logger.error("❌ Ping failed - API is not accessible")

        return result

    def test_convert_to_iink_format(self):
        """Test stroke conversion to iink format."""
        logger.info("Testing conversion to iink format...")

        # Create test strokes
        test_strokes = create_test_strokes()

        # Convert to iink format
        iink_data = self.adapter.convert_to_iink_format(test_strokes)

        # Check result structure
        success = (
            "contentType" in iink_data
            and "strokeGroups" in iink_data
            and len(iink_data["strokeGroups"]) > 0
            and "strokes" in iink_data["strokeGroups"][0]
            and len(iink_data["strokeGroups"][0]["strokes"]) == len(test_strokes)
        )

        if success:
            logger.info(
                f"✅ Conversion successful - {len(test_strokes)} strokes converted"
            )
        else:
            logger.error(f"❌ Conversion failed - Invalid format")
            logger.debug(json.dumps(iink_data, indent=2))

        return success, iink_data

    def test_direct_recognition(self):
        """Test direct handwriting recognition with test strokes."""
        logger.info("Testing direct handwriting recognition...")

        # Convert test strokes to iink format
        success, iink_data = self.test_convert_to_iink_format()
        if not success:
            return False, None

        # Recognize handwriting
        result = self.adapter.recognize_handwriting(iink_data)

        # Check if recognition was successful
        if "error" not in result:
            logger.info(f"✅ Recognition successful")
            if "result" in result:
                logger.info(f"Recognized text: {result['result']}")
            elif "candidates" in result and len(result["candidates"]) > 0:
                logger.info(f"Recognized text: {result['candidates'][0]}")
            else:
                logger.info(f"Raw result: {json.dumps(result, indent=2)}")
            return True, result
        else:
            logger.error(f"❌ Recognition failed: {result['error']}")
            return False, result

    def test_file_processing(self):
        """Test processing a test .rm file."""
        logger.info("Testing .rm file processing...")

        # Create test .rm file
        test_file_path = create_test_rm_file()
        if not test_file_path:
            logger.error(
                "❌ Cannot continue with file processing test - failed to create test file"
            )
            return False, None

        try:
            # Process the file
            result = self.adapter.process_rm_file(test_file_path)

            # Check if processing was successful
            if "error" not in result:
                logger.info(f"✅ File processing successful")
                if "result" in result:
                    logger.info(f"Recognized text: {result['result']}")
                elif "candidates" in result and len(result["candidates"]) > 0:
                    logger.info(f"Recognized text: {result['candidates'][0]}")
                else:
                    logger.info(f"Raw result: {json.dumps(result, indent=2)[:200]}...")
                return True, result
            else:
                logger.error(f"❌ File processing failed: {result['error']}")
                return False, result

        finally:
            # Clean up test file
            try:
                os.unlink(test_file_path)
                logger.info(f"Removed test file {test_file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove test file {test_file_path}: {e}")

    def test_standard_adapter(self):
        """Test the standard HandwritingAdapter with Web API integration."""
        logger.info("Testing standard HandwritingAdapter...")

        # Get test strokes
        test_strokes = create_test_strokes()

        # Convert to iink format using standard adapter
        iink_data = self.std_adapter.convert_to_iink_format(test_strokes)

        # Recognize handwriting using standard adapter
        result = self.std_adapter.recognize_handwriting(iink_data, "Text", "en_US")

        # Check if recognition was successful
        if "error" not in result:
            logger.info(f"✅ Standard adapter integration successful")
            if "result" in result:
                logger.info(f"Recognized text: {result['result']}")
            elif "candidates" in result and len(result["candidates"]) > 0:
                logger.info(f"Recognized text: {result['candidates'][0]}")
            else:
                logger.info(f"Raw result: {json.dumps(result, indent=2)[:200]}...")
            return True, result
        else:
            logger.error(f"❌ Standard adapter integration failed: {result['error']}")
            return False, result

    def test_service_integration(self):
        """Test integration with the handwriting recognition service."""
        logger.info("Testing service integration...")

        # Get test strokes
        test_strokes = create_test_strokes()

        # Use the service to convert strokes
        iink_data = self.service.convert_to_iink_format(test_strokes)

        # Use the service to recognize handwriting
        result = self.service.recognize_handwriting(iink_data)

        # Check if recognition was successful
        if result.get("success", False):
            logger.info(f"✅ Service integration successful")

            # Look at raw result
            raw_result = result.get("raw_result", {})
            if "result" in raw_result:
                logger.info(f"Recognized text: {raw_result['result']}")
            elif "candidates" in raw_result and len(raw_result["candidates"]) > 0:
                logger.info(f"Recognized text: {raw_result['candidates'][0]}")
            else:
                logger.info(f"Raw result: {json.dumps(raw_result, indent=2)[:200]}...")

            return True, result
        else:
            logger.error(
                f"❌ Service integration failed: {result.get('error', 'Unknown error')}"
            )
            return False, result

    def run_tests(self):
        """Run all tests and report results."""
        print("\n" + "=" * 80)
        print("MYSCRIPT WEB API ADAPTER INTEGRATION TEST")
        print("=" * 80)

        # Run all tests
        test_results = {
            "Ping Test": self.test_ping(),
            "Format Conversion Test": self.test_convert_to_iink_format()[0],
            "Direct Recognition Test": self.test_direct_recognition()[0],
            "File Processing Test": self.test_file_processing()[0],
            "Standard Adapter Test": self.test_standard_adapter()[0],
            "Service Integration Test": self.test_service_integration()[0],
        }

        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        all_passed = True
        for test_name, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")

            if not result:
                all_passed = False

        # Overall status
        print("\n" + "=" * 80)
        if all_passed:
            print(
                "🎉 All tests passed! MyScript Web API integration is working correctly!"
            )
        else:
            print("⚠️  Some tests failed. MyScript Web API integration has issues.")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test MyScript Web API Adapter")
    parser.add_argument(
        "--skip-file-test",
        action="store_true",
        help="Skip .rm file test (useful if rmscene is not installed)",
    )
    args = parser.parse_args()

    # Configure logging level
    if os.environ.get("DEBUG"):
        logging.getLogger().setLevel(logging.DEBUG)

    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("dotenv not available, using system environment variables")

    # Run tests
    tester = WebAdapterTester()

    if args.skip_file_test:
        # Run only API tests
        print("Skipping .rm file test as requested")
        ping_result = tester.test_ping()
        format_result, iink_data = tester.test_convert_to_iink_format()

        if ping_result and format_result:
            recognition_result, _ = tester.test_direct_recognition()
            service_result, _ = tester.test_service_integration()

            # Print summary
            print("\n" + "=" * 80)
            print("TEST SUMMARY")
            print("=" * 80)
            print(f"Ping Test: {'✅ PASSED' if ping_result else '❌ FAILED'}")
            print(
                f"Format Conversion Test: {'✅ PASSED' if format_result else '❌ FAILED'}"
            )
            print(
                f"Direct Recognition Test: {'✅ PASSED' if recognition_result else '❌ FAILED'}"
            )
            print(
                f"Service Integration Test: {'✅ PASSED' if service_result else '❌ FAILED'}"
            )

            if ping_result and format_result and recognition_result and service_result:
                print(
                    "\n🎉 All run tests passed! MyScript Web API integration is working correctly!"
                )
            else:
                print(
                    "\n⚠️  Some tests failed. MyScript Web API integration has issues."
                )
    else:
        # Run all tests
        tester.run_tests()
