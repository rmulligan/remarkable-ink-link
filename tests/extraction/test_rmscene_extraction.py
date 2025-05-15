#!/usr/bin/env python3
"""
Test script for rmscene stroke extraction functionality.

This script tests the extraction of strokes from a reMarkable file
using rmscene without requiring MyScript API credentials.
"""

import os
import sys
import json
import logging
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

# Import the handwriting web adapter for testing
from src.inklink.adapters.handwriting_web_adapter import HandwritingWebAdapter


def create_test_strokes():
    """
    Create test stroke data for a test .rm file.

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


def create_and_save_test_rm_file():
    """
    Create a test .rm file with simple strokes and save it.

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


def test_rmscene_extraction():
    """Test rmscene extraction functionality."""
    print("\n" + "=" * 80)
    print("RMSCENE STROKE EXTRACTION TEST")
    print("=" * 80)

    # Create a test .rm file
    test_file_path = create_and_save_test_rm_file()
    if not test_file_path:
        print("❌ Test failed: Could not create test .rm file")
        return False

    try:
        # Create adapter without API keys (we don't need them for extraction)
        adapter = HandwritingWebAdapter()

        # Extract strokes from test file
        strokes = adapter.extract_strokes_from_rm_file(test_file_path)

        # Check if strokes were extracted successfully
        if strokes and len(strokes) > 0:
            print(f"✅ Successfully extracted {len(strokes)} strokes from test file")
            print("\nFirst stroke data:")
            print(json.dumps(strokes[0], indent=2))

            # Check if strokes have expected properties
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
                return True
            else:
                print("\n❌ Failed to convert strokes to iink format")
                return False

        else:
            print("❌ No strokes extracted from test file")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        # Clean up test file
        try:
            os.unlink(test_file_path)
            print(f"\nRemoved test file {test_file_path}")
        except Exception as e:
            print(f"\nFailed to remove test file {test_file_path}: {e}")


if __name__ == "__main__":
    # Try to load environment variables if available
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("dotenv not available, continuing without loading .env")

    # Run the extraction test
    success = test_rmscene_extraction()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    if success:
        print("🎉 rmscene stroke extraction test passed successfully!")
    else:
        print("⚠️ rmscene stroke extraction test failed!")
    print("=" * 80 + "\n")
