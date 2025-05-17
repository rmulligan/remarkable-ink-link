#!/usr/bin/env python3
"""
Test script for MyScript Web Recognition API.

This script tests basic connectivity with the MyScript Web API
for handwriting recognition.

Notes:
1. This test requires valid MyScript API credentials in the .env file
2. The MyScript API keys must be registered for the domain/IP you're using
3. If you receive a 401 error, check that:
   - Your API keys are correct and valid
   - Your keys are registered for the domain making the requests
   - Your account has permission to use the Text recognition endpoints
   - You've accepted the terms of service for the MyScript API
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# MyScript API configuration
API_BASE_URL = "https://cloud.myscript.com/api/v4.0/iink/"
RECOGNITION_ENDPOINT = (
    "batch"  # Use the batch endpoint which is known to work from the curl example
)


class MyScriptWebApiTest:
    """Test MyScript Web Recognition API."""

    def __init__(self):
        """Initialize with API keys from environment."""
        self.app_key = os.environ.get("MYSCRIPT_APP_KEY")
        self.hmac_key = os.environ.get("MYSCRIPT_HMAC_KEY")

        if not self.app_key or not self.hmac_key:
            logger.error("MyScript keys not found in environment variables!")
            sys.exit(1)

        logger.info(f"Using MyScript App Key: {self.app_key[:8]}...{self.app_key[-8:]}")
        logger.info(
            f"Using MyScript HMAC Key: {self.hmac_key[:8]}...{self.hmac_key[-8:]}"
        )

    def generate_hmac(self, data):
        """
        Generate HMAC signature for request authentication.

        Args:
            data: Data to sign

        Returns:
            HMAC signature as base64 encoded string
        """
        h = hmac.new(
            bytes(self.hmac_key, "utf-8"), data.encode("utf-8"), hashlib.sha512
        )
        return base64.b64encode(h.digest()).decode("utf-8")

    def create_test_ink(self):
        """
        Create test ink data for recognition based on the successful curl request.

        Returns:
            Dictionary with ink data
        """
        # Create a simple example of handwritten "hello"
        # This is a simplified representation of handwriting strokes
        # In a real application, this would come from the .rm file
        current_time = int(time.time() * 1000)  # Current time in milliseconds

        # Create request data matching the format from the successful curl request
        return {
            "configuration": {
                "text": {
                    "guides": {"enable": True},
                    "smartGuide": True,
                    "smartGuideFadeOut": {"enable": False, "duration": 10000},
                    "mimeTypes": ["text/plain", "application/vnd.myscript.jiix"],
                    "margin": {"top": 20, "left": 10, "right": 10},
                    "eraser": {"erase-precisely": False},
                },
                "lang": "en_US",
                "export": {
                    "image-resolution": 300,
                    "jiix": {
                        "bounding-box": False,
                        "strokes": False,
                        "text": {"chars": False, "words": True},
                    },
                },
            },
            "xDPI": 96,
            "yDPI": 96,
            "contentType": "Text",
            "theme": "ink {\ncolor: #000000;\n-myscript-pen-width: 1;\n-myscript-pen-fill-style: none;\n-myscript-pen-fill-color: #FFFFFF00;\n}\n.math {\nfont-family: STIXGeneral;\n}\n.math-solved {\nfont-family: STIXGeneral;\ncolor: #A8A8A8FF;\n}\n.text {\nfont-family: MyScriptInter;\nfont-size: 10;\n}\n",
            "strokeGroups": [
                {
                    "penStyle": "color: #000000;\n-myscript-pen-width: 1;",
                    "strokes": [
                        {
                            "x": [100, 150, 200, 250, 300],
                            "y": [100, 80, 100, 80, 100],
                            "t": [
                                current_time,
                                current_time + 100,
                                current_time + 200,
                                current_time + 300,
                                current_time + 400,
                            ],
                            "p": [0.5, 0.6, 0.7, 0.6, 0.5],
                            "pointerType": "mouse",
                        }
                    ],
                }
            ],
            "height": 500,
            "width": 656,
            "conversionState": "DIGITAL_EDIT",
        }

    def test_web_recognition(self):
        """Test the MyScript Web Recognition API."""
        logger.info("Testing MyScript Web Recognition API...")

        # Create test ink data already formatted like the successful curl request
        request_data = self.create_test_ink()

        # Add HMAC signature
        request_json = json.dumps(request_data)
        hmac_signature = self.generate_hmac(request_json)

        # Prepare headers to match the successful curl request
        headers = {
            "Accept": "application/json,application/vnd.myscript.jiix",
            "Content-Type": "application/json",
            "applicationkey": self.app_key,  # Note: lowercase key as in the successful curl
            "hmac": hmac_signature,
            "origin": "https://cloud.myscript.com",
            "referer": "https://cloud.myscript.com/",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
        }

        # Send request
        try:
            url = urljoin(API_BASE_URL, RECOGNITION_ENDPOINT)
            logger.info(f"Sending request to {url}")

            response = requests.post(
                url, headers=headers, data=request_json, timeout=30
            )

            # Check response
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"✅ Recognition successful: {json.dumps(result, indent=2)}"
                )
                return True, result
            logger.error(
                f"❌ Recognition failed: {response.status_code} - {response.text}"
            )
            return False, {
                "error": f"HTTP error {response.status_code}",
                "details": response.text,
            }

        except Exception as e:
            logger.error(f"❌ Error during API call: {e}")
            return False, {"error": str(e)}

    def run_test(self):
        """Run the test and display results."""
        print("\n" + "=" * 80)
        print("MYSCRIPT WEB RECOGNITION API TEST")
        print("=" * 80)

        # Test web recognition
        success, result = self.test_web_recognition()

        # Print summary
        print("\n" + "=" * 80)
        print("TEST RESULTS")
        print("=" * 80)

        if success:
            print("✅ Web Recognition API test passed!")
            print("\nRecognized Text:")
            if "result" in result:
                print(f"  {result['result']}")
            else:
                print(f"  Raw result: {json.dumps(result, indent=2)}")
        else:
            print("❌ Web Recognition API test failed!")
            print(f"\nError: {json.dumps(result, indent=2)}")

        return success


if __name__ == "__main__":
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("dotenv not available, using system environment variables")

    # Run test
    test = MyScriptWebApiTest()
    test.run_test()
