#!/usr/bin/env python3
"""
Test script for the updated HandwritingWebAdapter extraction function.
This script tests the adapter with existing sample .rm files.
"""

import json
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the updated adapter
from src.inklink.adapters.handwriting_web_adapter import (  # noqa: E402
    HandwritingWebAdapter,
)


def test_extraction_with_sample_file():
    """
    Test the extraction with an existing sample .rm file.
    """
    print("\n" + "=" * 80)
    print("HANDWRITING WEB ADAPTER EXTRACTION TEST")
    print("=" * 80)

    # Path to sample file
    sample_file = os.path.join(
        project_root, "rmdoc_extract", "6aaaeaf7-6932-4643-ae39-2c880e094b0f.content"
    )

    if not os.path.exists(sample_file):
        print(f"❌ Sample file not found: {sample_file}")
        return False

    print(f"Using sample file: {sample_file}")

    try:
        # Create the adapter
        adapter = HandwritingWebAdapter()

        # Extract strokes from the sample file
        strokes = adapter.extract_strokes_from_rm_file(sample_file)

        # Check if strokes were extracted
        if strokes and len(strokes) > 0:
            print(
                f"✅ Successfully extracted {len(strokes)} strokes from the sample file"
            )
            print("\nFirst stroke data:")
            print(json.dumps(strokes[0], indent=2))

            # Check stroke properties
            expected_properties = ["id", "x", "y", "p", "t", "color", "width"]
            all_props_present = all(prop in strokes[0] for prop in expected_properties)

            if all_props_present:
                print("\n✅ All expected stroke properties are present")
            else:
                print("\n⚠️ Some expected stroke properties are missing")
                missing = [
                    prop for prop in expected_properties if prop not in strokes[0]
                ]
                print(f"Missing properties: {missing}")

            # Convert to iink format
            iink_data = adapter.convert_to_iink_format(strokes)

            if (
                iink_data
                and "strokeGroups" in iink_data
                and len(iink_data["strokeGroups"]) > 0
            ):
                print("\n✅ Successfully converted strokes to iink format")

                # Check if all strokes were included
                stroke_count = len(iink_data["strokeGroups"][0]["strokes"])
                if stroke_count == len(strokes):
                    print(f"✅ All {len(strokes)} strokes were included in iink format")
                else:
                    print(
                        f"⚠️ Expected {len(strokes)} strokes but got {stroke_count} in iink format"
                    )

                return True
            print("\n❌ Failed to convert strokes to iink format")
            return False
        else:
            print("❌ No strokes extracted from sample file")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Try to load environment variables if available
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("dotenv not available, continuing without loading .env")

    # Run the test
    success = test_extraction_with_sample_file()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    if success:
        print("🎉 HandwritingWebAdapter extraction test passed successfully!")
    else:
        print("⚠️ HandwritingWebAdapter extraction test failed!")
    print("=" * 80)
