#!/usr/bin/env python3
"""Test script for the updated HandwritingWebAdapter with rmscene v0.7.0+."""

import json
import logging
import os
import sys
import tempfile

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

# Import rmscene for creating test files
try:
    import rmscene  # noqa: E402
    from rmscene.scene_items import Group, Line, Pen, PenColor, Point  # noqa: E402
    from rmscene.scene_stream import write_tree  # noqa: E402
    from rmscene.scene_tree import SceneTree  # noqa: E402

    RMSCENE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import rmscene: {e}")
    RMSCENE_AVAILABLE = False


def create_test_rm_file():
    """
    Create a test .rm file with the current rmscene API.

    Returns:
        Path to the temporary .rm file
    """
    if not RMSCENE_AVAILABLE:
        logger.error("rmscene not available - cannot create test file")
        return None

    try:
        # Create a scene tree
        scene_tree = SceneTree()

        # Create a group for our strokes
        group = Group(node_id=scene_tree.generate_id())
        group_id = scene_tree.add_item(group)

        # Create a line (stroke)
        line = Line(node_id=scene_tree.generate_id())
        line.pen = Pen.FINELINER
        line.color = PenColor.BLACK

        # Add points to the line
        current_time = int(1000 * 1692300000)  # Base timestamp
        points = []

        # Simple horizontal line
        for i in range(5):
            x = 100 + (i * 50)
            y = 150
            pressure = 0.5 + (i * 0.1) % 0.5
            t = current_time + (i * 100)

            point = Point(x=x, y=y, pressure=pressure, t=t)
            points.append(point)

        line.points = points

        # Add the line to the tree
        line_id = scene_tree.add_item(line, parent_id=group_id)
        logger.info(f"Added line with ID: {line_id}")

        # Create a second line
        line2 = Line(node_id=scene_tree.generate_id())
        line2.pen = Pen.BALLPOINT
        line2.color = PenColor.BLACK

        # Add points for a vertical line
        points2 = []
        for i in range(5):
            x = 200
            y = 100 + (i * 50)
            pressure = 0.7 - (i * 0.05)
            t = current_time + 1000 + (i * 100)

            point = Point(x=x, y=y, pressure=pressure, t=t)
            points2.append(point)

        line2.points = points2

        # Add the second line to the tree
        line2_id = scene_tree.add_item(line2, parent_id=group_id)
        logger.info(f"Added line2 with ID: {line2_id}")

        # Write to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".rm") as temp_file:
            temp_path = temp_file.name

        # Write the scene tree to the file
        with open(temp_path, "wb") as f:
            write_tree(scene_tree, f)

        logger.info(f"Created test .rm file at {temp_path}")
        return temp_path

    except Exception as e:
        logger.error(f"Failed to create test .rm file: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_updated_adapter():
    """Test the updated HandwritingWebAdapter with a test .rm file."""
    print("\n" + "=" * 80)
    print("UPDATED HANDWRITING WEB ADAPTER TEST")
    print("=" * 80)

    if not RMSCENE_AVAILABLE:
        print("❌ Test cannot continue: rmscene not available")
        return False

    # Create a test .rm file
    test_file_path = create_test_rm_file()
    if not test_file_path:
        print("❌ Test failed: Could not create test .rm file")
        return False

    try:
        # Create the adapter
        adapter = HandwritingWebAdapter()

        # Extract strokes from the test file
        strokes = adapter.extract_strokes_from_rm_file(test_file_path)

        # Check if strokes were extracted
        if strokes and len(strokes) > 0:
            print(
                f"✅ Successfully extracted {len(strokes)} strokes from the test file"
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
        print("❌ No strokes extracted from test file")
        return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up the test file
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

    # Run the test
    success = test_updated_adapter()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    if success:
        print("🎉 Updated HandwritingWebAdapter test passed successfully!")
    else:
        print("⚠️ Updated HandwritingWebAdapter test failed!")
    print("=" * 80)
