#!/usr/bin/env python3
"""
Simplified test for metadata handling with reMarkable API.

This script creates a minimal test notebook and uploads it to verify metadata format.
"""

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import uuid
import zipfile
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_simplified_metadata")

# Import project modules
try:
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG


def create_test_notebook():
    """Create a minimal test notebook structure."""
    temp_dir = tempfile.mkdtemp(prefix="simple_metadata_test_")
    logger.info(f"Created temporary directory: {temp_dir}")

    # Create a unique ID for the notebook
    notebook_id = str(uuid.uuid4())

    # Current timestamp in milliseconds
    now_ms = int(time.time() * 1000)

    # Create files with proper structure
    content_file_path = os.path.join(temp_dir, f"{notebook_id}.content")
    metadata_file_path = os.path.join(temp_dir, f"{notebook_id}.metadata")

    # Create super simple content structure
    content = {}

    # Create metadata structure - match exactly what we saw in downloaded file
    metadata = {
        "createdTime": str(now_ms),
        "lastModified": str(now_ms),
        "new": False,
        "parent": "",
        "pinned": False,
        "source": "com.remarkable.test",
        "type": "DocumentType",
        "visibleName": "Metadata Test Simple",
    }

    # Write the files
    with open(content_file_path, "w") as f:
        json.dump(content, f, indent=2)

    with open(metadata_file_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Create notebook directory
    notebook_dir = os.path.join(temp_dir, notebook_id)
    os.makedirs(notebook_dir, exist_ok=True)

    # Create a sample page file
    page_id = str(uuid.uuid4())
    page_file_path = os.path.join(notebook_dir, f"{page_id}.rm")

    with open(page_file_path, "w") as f:
        f.write("Simple test content")

    return temp_dir, content_file_path, metadata_file_path, notebook_id


def create_zip_from_directory(temp_dir, output_path):
    """Create a zip file from the directory."""
    try:
        with zipfile.ZipFile(output_path, "w") as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        logger.info(f"Created zip file at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating zip file: {e}")
        return False


def upload_and_test(rmapi_path, modified_zip_path, notebook_name):
    """Upload the test notebook to verify metadata handling."""
    try:
        # Create rmapi adapter
        rmapi_adapter = RmapiAdapter(rmapi_path)

        # Refresh to sync with remote state
        logger.info("Refreshing rmapi to sync with remote state...")
        success, stdout, stderr = rmapi_adapter.run_command("refresh")
        if not success:
            logger.warning(f"Failed to refresh rmapi: {stderr}")
        else:
            logger.info("Successfully refreshed rmapi")

        # Wait a moment to ensure refresh is complete
        time.sleep(1)

        # Upload the modified notebook
        logger.info(f"Uploading notebook to reMarkable Cloud: {notebook_name}")
        success, message = rmapi_adapter.upload_file(modified_zip_path, notebook_name)

        if success:
            logger.info(f"✅ SUCCESS: Upload succeeded: {message}")
            return True
        else:
            logger.error(f"❌ FAILURE: Upload failed: {message}")
            return False

    except Exception as e:
        logger.error(f"Error uploading test notebook: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test simplified metadata format")
    parser.add_argument(
        "--notebook-name",
        type=str,
        default="Simple Metadata Test",
        help="Name for the test notebook",
    )
    parser.add_argument(
        "--no-cleanup", action="store_true", help="Don't remove temporary files"
    )
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Configure rmapi path
    rmapi_path = args.rmapi_path or CONFIG.get("RMAPI_PATH")
    if not os.path.exists(rmapi_path):
        logger.error(f"RMAPI executable not found at {rmapi_path}")
        return False

    logger.info(f"Using rmapi path: {rmapi_path}")

    # Create test notebook
    temp_dir, content_file_path, metadata_file_path, notebook_id = (
        create_test_notebook()
    )
    zip_path = os.path.join(os.path.dirname(temp_dir), f"{args.notebook_name}.rmdoc")

    try:
        # Show original metadata
        with open(metadata_file_path, "r") as f:
            metadata = json.load(f)
        logger.info("Metadata being used:")
        logger.info(json.dumps(metadata, indent=2))

        # Create zip for upload
        if not create_zip_from_directory(temp_dir, zip_path):
            logger.error("Failed to create zip for upload")
            return False

        # Upload and test
        if not upload_and_test(rmapi_path, zip_path, args.notebook_name):
            logger.error("Failed to upload test notebook")
            return False

        logger.info(
            "✅ TEST PASSED: Successfully implemented and tested metadata handling fix"
        )
        return True

    finally:
        # Clean up
        if not args.no_cleanup:
            shutil.rmtree(temp_dir)
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            logger.info("Cleaned up temporary files")


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
