#!/usr/bin/env python3
"""
Updated test script for rmscene stroke extraction functionality.

This script tests the extraction of strokes from a reMarkable file
using the current rmscene API without requiring MyScript API credentials.
"""

import json
import logging
import os
import sys
import tempfile
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try importing rmscene
try:
    import rmscene
    import rmscene.scene_items as si
    import rmscene.scene_tree as st
    from rmscene.scene_stream import read_tree, write_tree

    RMSCENE_AVAILABLE = True
except ImportError:
    logger.error("rmscene not installed or not properly configured")
    RMSCENE_AVAILABLE = False

# Import the handwriting web adapter for testing
try:
    from src.inklink.adapters.handwriting_web_adapter import HandwritingWebAdapter
except ImportError:
    logger.error("Failed to import HandwritingWebAdapter")
    sys.exit(1)


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
    Create a test .rm file with simple strokes and save it using the current rmscene API.

    Returns:
        Path to the temporary .rm file
    """
    if not RMSCENE_AVAILABLE:
        logger.error("rmscene not available - cannot create test .rm file")
        return None

    try:
        # Create a SceneTree instead of Scene
        scene_tree = st.SceneTree()

        # Create a root group to hold strokes
        root_group = si.Group()
        root_id = scene_tree.add_item(root_group)

        # Add test strokes from the create_test_strokes function
        test_strokes = create_test_strokes()

        # Convert to rmscene lines
        for stroke in test_strokes:
            line = si.Line()

            # Set line properties
            line.pen = si.Pen.FINELINER
            line.color = si.PenColor.BLACK

            # Add points
            points = []
            for i, item in enumerate(stroke["x"]):
                point = si.Point(
                    x=item,
                    y=stroke["y"][i],
                    pressure=stroke["p"][i],
                    t=stroke["t"][i],  # t is the timestamp in ms
                )
                points.append(point)

            line.points = points

            # Add line to scene tree under the root group
            scene_tree.add_item(line, parent_id=root_id)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".rm") as temp_file:
            temp_path = temp_file.name

        # Write scene tree to the file
        with open(temp_path, "wb") as f:
            write_tree(scene_tree, f)

        logger.info(f"Created test .rm file at {temp_path}")
        return temp_path

    except Exception as e:
        logger.error(f"Failed to create test .rm file: {e}")
        return None


def test_extract_strokes_manually():
    """Test manual extraction of strokes from an .rm file using rmscene."""
    print("\n" + "=" * 80)
    print("RMSCENE MANUAL STROKE EXTRACTION TEST")
    print("=" * 80)

    if not RMSCENE_AVAILABLE:
        print("❌ Test failed: rmscene not available")
        return False, []

    # Create a test .rm file
    test_file_path = create_and_save_test_rm_file()
    if not test_file_path:
        print("❌ Test failed: Could not create test .rm file")
        return False, []

    try:
        # Read the .rm file directly using rmscene
        with open(test_file_path, "rb") as f:
            scene_tree = read_tree(f)

        # Extract strokes manually
        strokes = []
        line_items = []

        # Find all Line items in the tree
        for item_id, item in scene_tree.items.items():
            if isinstance(item, si.Line):
                line_items.append((item_id, item))

        # Process Line items
        for item_id, line in line_items:
            x_points = []
            y_points = []
            pressures = []
            timestamps = []

            for point in line.points:
                x_points.append(point.x)
                y_points.append(point.y)
                pressures.append(point.pressure)
                timestamps.append(point.t if hasattr(point, "t") else 0)

            stroke = {
                "id": str(item_id),
                "x": x_points,
                "y": y_points,
                "p": pressures,
                "t": timestamps,
                "color": str(line.color) if hasattr(line, "color") else "#000000",
                "width": float(line.pen.value) if hasattr(line, "pen") else 2.0,
            }

            strokes.append(stroke)

        # Print extraction results
        if strokes and len(strokes) > 0:
            print(
                f"✅ Successfully extracted {len(strokes)} strokes directly using rmscene"
            )
            print("\nFirst stroke data:")
            print(json.dumps(strokes[0], indent=2))
            return True, strokes
        print("❌ No strokes extracted from test file")
        return False, []

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False, []
    finally:
        # Clean up test file
        try:
            os.unlink(test_file_path)
            print(f"\nRemoved test file {test_file_path}")
        except Exception as e:
            print(f"\nFailed to remove test file {test_file_path}: {e}")


def test_adapter_extraction():
    """Test extraction via the HandwritingWebAdapter."""
    print("\n" + "=" * 80)
    print("HANDWRITING WEB ADAPTER EXTRACTION TEST")
    print("=" * 80)

    # Get test strokes and file from previous test
    success, _ = test_extract_strokes_manually()
    if not success:
        return False

    # Create a new test file
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
            print(
                f"✅ Successfully extracted {len(strokes)} strokes using HandwritingWebAdapter"
            )
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
            print("\n❌ Failed to convert strokes to iink format")
            return False
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

    # Run the extraction tests
    manual_success = test_extract_strokes_manually()[0]
    adapter_success = test_adapter_extraction()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    print(f"Manual Extraction Test: {'✅ PASSED' if manual_success else '❌ FAILED'}")
    print(f"Adapter Extraction Test: {'✅ PASSED' if adapter_success else '❌ FAILED'}")

    if manual_success and adapter_success:
        print("\n🎉 All rmscene stroke extraction tests passed successfully!")
    else:
        print("\n⚠️ Some rmscene stroke extraction tests failed!")
    print("=" * 80 + "\n")
