#!/usr/bin/env python3
"""Demonstrate creating editable ink on reMarkable."""

import logging
import os
import sys
import tempfile

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from inklink.adapters.rmapi_adapter import RmapiAdapter  # noqa: E402
from inklink.config import CONFIG  # noqa: E402
from inklink.services.ink_generation_service import get_ink_generation_service  # noqa: E402
from inklink.services.remarkable_service import RemarkableService  # noqa: E402

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_editable_ink_notebook():
    """Create a notebook with editable ink strokes."""
    try:
        # Initialize services
        ink_service = get_ink_generation_service()
        rmapi_adapter = RmapiAdapter(CONFIG.get("RMAPI_PATH", "./local-rmapi"))
        remarkable_service = RemarkableService(rmapi_adapter)

        # Test connectivity
        success, message = remarkable_service.test_connection()
        if not success:
            logger.error(f"Failed to connect to reMarkable cloud: {message}")
            return False

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create an editable ink file
            rm_path = os.path.join(temp_dir, "editable_ink_demo.rm")

            # Generate editable ink strokes
            text = """Hello from InkLink!

This is editable ink that you can modify on your reMarkable device.

Unlike static text from PDF, this can be:
- Erased
- Modified
- Annotated
- Extended

Try editing this text on your device!
"""

            logger.info("Creating editable ink file...")
            success = ink_service.create_rm_file_with_text(text, rm_path)

            if not success:
                logger.error("Failed to create editable ink file")
                return False

            logger.info(f"Created editable ink file at: {rm_path}")

            # Upload to reMarkable
            title = "Editable Ink Demo"
            logger.info(f"Uploading '{title}' to reMarkable...")

            success, message = remarkable_service.upload(rm_path, title)

            if success:
                logger.info(f"Successfully uploaded editable ink notebook: {title}")
                logger.info(
                    "Check your reMarkable device - you should be able to edit the text!"
                )
                return True
            else:
                logger.error(f"Failed to upload notebook: {message}")
                return False

    except Exception as e:
        logger.error(f"Error creating editable ink notebook: {e}")
        return False


def create_multipage_demo():
    """Create a demo with multiple pages of editable ink."""
    try:
        ink_service = get_ink_generation_service()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Page 1
            page1_path = os.path.join(temp_dir, "page1.rm")
            text1 = """Page 1: Introduction to Editable Ink

This is the first page of editable content.
You can write, erase, and modify this text.

Try adding your own notes below:
"""
            ink_service.create_rm_file_with_text(text1, page1_path)

            # Page 2
            page2_path = os.path.join(temp_dir, "page2.rm")
            text2 = """Page 2: Advanced Features

This ink supports:
- Natural handwriting strokes
- Multiple pen types
- Color variations
- Pressure sensitivity

Experiment with different editing tools!
"""
            ink_service.create_rm_file_with_text(text2, page2_path)

            # TODO: Implement multi-page notebook creation
            # This would require creating a proper .rmdoc structure
            # with content and metadata files

            logger.info("Multi-page demo creation not yet implemented")
            return False

    except Exception as e:
        logger.error(f"Error creating multipage demo: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("InkLink Editable Ink Demo")
    print("=" * 50)

    if create_editable_ink_notebook():
        print("\nSuccess! Check your reMarkable device for the editable ink notebook.")
        print("You should be able to:")
        print("- Erase parts of the text")
        print("- Add your own handwriting")
        print("- Modify existing strokes")
        print("\nThis demonstrates true editable ink instead of static PDF-like text!")
    else:
        print("\nFailed to create editable ink notebook. Check the logs for details.")
        sys.exit(1)
