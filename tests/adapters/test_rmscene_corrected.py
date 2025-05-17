#!/usr/bin/env python3
"""
Corrected test for rmscene functionality.
This script tests the rmscene library with the correct API.
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

# Try importing rmscene
try:
    import rmscene
    from rmscene.scene_items import Group, Line, Pen, PenColor, Point
    from rmscene.scene_tree import CrdtId, SceneTree

    logger.info("Successfully imported rmscene classes")
except ImportError as e:
    logger.error(f"Failed to import rmscene: {e}")
    sys.exit(1)

# Import the handwriting web adapter for testing
try:
    from src.inklink.adapters.handwriting_web_adapter import HandwritingWebAdapter

    logger.info("Successfully imported HandwritingWebAdapter")
except ImportError as e:
    logger.error(f"Failed to import HandwritingWebAdapter: {e}")
    sys.exit(1)


def extract_strokes_using_adapter():
    """
    Test HandwritingWebAdapter's extract_strokes_from_rm_file method on a specified .rm file.
    """
    print("\n" + "=" * 80)
    print("RMSCENE EXTRACTION TEST USING ADAPTER")
    print("=" * 80)

    # Get the .rm file paths to test with
    print("Checking for .rm files in the project...")

    import tempfile

    # Create a temporary simple .rm file
    try:
        # Create a basic .rm file with a single line
        with open(
            "/home/ryan/dev/remarkable-ink-link/rmdoc_extract/6aaaeaf7-6932-4643-ae39-2c880e094b0f.content",
            "rb",
        ) as rm_file:
            content = rm_file.read()

        # Write content to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".rm") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        print(f"Created a temporary .rm file: {temp_file_path}")
    except Exception as e:
        logger.error(f"Failed to create temporary .rm file: {e}")
        temp_file_path = None

    # If we couldn't create a temporary file, try to locate existing files
    if not temp_file_path:
        print("Failed to create temp file, searching for existing .rm files...")

        # Look for existing .rm files in common locations
        potential_files = []
        for root_dir in ["/home/ryan/dev/remarkable-ink-link/rmdoc_extract"]:
            if os.path.exists(root_dir):
                for file in os.listdir(root_dir):
                    if file.endswith(".content"):
                        potential_files.append(os.path.join(root_dir, file))

        if not potential_files:
            print("❌ No .rm files found for testing")
            return False

        temp_file_path = potential_files[0]
        print(f"Found existing .rm file for testing: {temp_file_path}")

    # Now use the HandwritingWebAdapter to extract strokes from the .rm file
    try:
        adapter = HandwritingWebAdapter()
        strokes = adapter.extract_strokes_from_rm_file(temp_file_path)

        # Check if strokes were extracted
        if strokes and len(strokes) > 0:
            print(f"✅ Successfully extracted {len(strokes)} strokes from file")
            print("\nFirst stroke data:")
            print(json.dumps(strokes[0], indent=2))

            # Check if strokes have the expected properties
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
        else:
            print("❌ No strokes extracted from file")
            return False
    except Exception as e:
        logger.error(f"Error in adapter extraction: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # Clean up temp file if we created one
        if temp_file_path and temp_file_path.startswith("/tmp/"):
            try:
                os.unlink(temp_file_path)
                print(f"Removed temporary file: {temp_file_path}")
            except Exception as e:
                print(f"Failed to remove temporary file: {e}")


if __name__ == "__main__":
    # Try to load environment variables if available
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("dotenv not available, continuing without loading .env")

    # Test stroke extraction using the adapter
    success = extract_strokes_using_adapter()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    if success:
        print("🎉 rmscene stroke extraction test passed successfully!")
    else:
        print("⚠️ rmscene stroke extraction test failed!")
    print("=" * 80 + "\n")
