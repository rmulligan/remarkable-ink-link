#!/usr/bin/env python3
"""
Test script for the updated HandwritingWebAdapter using mock data.
This avoids the need for real .rm files.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the adapter for testing
from src.inklink.adapters.handwriting_web_adapter import (  # noqa: E402
    HandwritingWebAdapter,
)


def mock_strokes() -> List[Dict[str, Any]]:
    """
    Create mock strokes data for testing the conversion to iink format.

    Returns:
        A list of mock stroke dictionaries
    """
    base_time = 1692300000 * 1000  # Base timestamp in milliseconds

    return [
        # 'h' stroke
        {
            "id": "stroke1",
            "x": [100, 100, 100, 100, 120, 140, 140, 140],
            "y": [100, 120, 140, 160, 160, 160, 140, 120],
            "p": [0.5, 0.6, 0.7, 0.7, 0.6, 0.5, 0.6, 0.7],
            "t": [
                base_time,
                base_time + 10,
                base_time + 20,
                base_time + 30,
                base_time + 40,
                base_time + 50,
                base_time + 60,
                base_time + 70,
            ],
            "color": "#000000",
            "width": 2.0,
        },
        # 'e' stroke
        {
            "id": "stroke2",
            "x": [180, 200, 220, 200, 180, 180, 200, 220],
            "y": [140, 130, 140, 150, 160, 140, 140, 140],
            "p": [0.5, 0.6, 0.7, 0.6, 0.5, 0.5, 0.5, 0.5],
            "t": [
                base_time + 100,
                base_time + 110,
                base_time + 120,
                base_time + 130,
                base_time + 140,
                base_time + 150,
                base_time + 160,
                base_time + 170,
            ],
            "color": "#000000",
            "width": 2.0,
        },
        # 'l' stroke
        {
            "id": "stroke3",
            "x": [240, 240, 240, 240],
            "y": [100, 120, 140, 160],
            "p": [0.5, 0.6, 0.7, 0.5],
            "t": [base_time + 200, base_time + 210, base_time + 220, base_time + 230],
            "color": "#000000",
            "width": 2.0,
        },
    ]


def test_mock_conversion():
    """Test the conversion of mock strokes to iink format."""
    print("\n" + "=" * 80)
    print("MOCK STROKES CONVERSION TEST")
    print("=" * 80)

    try:
        # Create the adapter
        adapter = HandwritingWebAdapter()

        # Get mock strokes
        strokes = mock_strokes()
        print(f"Created {len(strokes)} mock strokes")

        # Convert to iink format
        iink_data = adapter.convert_to_iink_format(strokes)

        # Check if conversion was successful
        if (
            iink_data
            and "strokeGroups" in iink_data
            and len(iink_data["strokeGroups"]) > 0
        ):
            print("\n✅ Successfully converted mock strokes to iink format")

            # Verify stroke count
            stroke_count = len(iink_data["strokeGroups"][0]["strokes"])
            if stroke_count == len(strokes):
                print(f"✅ All {len(strokes)} strokes were included in iink format")
            else:
                print(
                    f"⚠️ Expected {len(strokes)} strokes but got {stroke_count} in iink format"
                )

            # Print sample of converted data
            print("\nSample of iink_data strokeGroups:")
            print(json.dumps(iink_data["strokeGroups"][0]["strokes"][0], indent=2))

            # Verify the structure is as expected for MyScript API
            if "contentType" in iink_data and "configuration" in iink_data:
                print("\n✅ iink_data has the expected top-level structure")

                # Check specific configuration options needed for MyScript
                if (
                    "text" in iink_data["configuration"]
                    and "lang" in iink_data["configuration"]
                ):
                    print("✅ Configuration includes text and language settings")
                else:
                    print("⚠️ Configuration missing some expected settings")

                return True
            print("\n⚠️ iink_data missing expected top-level structure")
            return False
        print("\n❌ Failed to convert mock strokes to iink format")
        return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the test
    success = test_mock_conversion()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    if success:
        print("🎉 Mock strokes conversion test passed successfully!")
    else:
        print("⚠️ Mock strokes conversion test failed!")
    print("=" * 80)
