#!/usr/bin/env python3
"""
Download and Re-upload Test

This script downloads an existing notebook from reMarkable,
makes a simple change, and then re-uploads it to test metadata handling.
"""

import os
import sys
import time
import json
import zipfile
import tempfile
import logging
import argparse
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("download_and_reupload")

# Import project modules
try:
    from inklink.config import CONFIG
    from inklink.adapters.rmapi_adapter import RmapiAdapter
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.config import CONFIG
    from inklink.adapters.rmapi_adapter import RmapiAdapter


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download, modify, and re-upload a notebook"
    )
    parser.add_argument(
        "--notebook",
        type=str,
        default="Testing Notebook",
        help="Name of existing notebook to download",
    )
    parser.add_argument(
        "--new-name", type=str, help="New name for the re-uploaded notebook"
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

    # Set new name
    new_name = args.new_name or f"{args.notebook} (Copy)"

    # Create rmapi adapter
    rmapi_adapter = RmapiAdapter(rmapi_path)

    # Create temp dir for download
    temp_dir = tempfile.mkdtemp(prefix="rm_download_")
    download_path = os.path.join(temp_dir, f"{args.notebook}.rmdoc")
    extract_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        # Download notebook
        logger.info(f"Downloading notebook: {args.notebook}")
        success, message = rmapi_adapter.download_file(args.notebook, download_path)

        if not success:
            logger.error(f"Failed to download notebook: {message}")
            return False

        logger.info(f"Successfully downloaded notebook to {download_path}")

        # Extract notebook
        logger.info(f"Extracting notebook to {extract_dir}")
        with zipfile.ZipFile(download_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Find metadata file
        metadata_file = None
        for file in os.listdir(extract_dir):
            if file.endswith(".metadata"):
                metadata_file = os.path.join(extract_dir, file)
                break

        if not metadata_file:
            logger.error(f"No metadata file found in notebook {args.notebook}")
            return False

        # Read metadata
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        logger.info("Original metadata:")
        logger.info(json.dumps(metadata, indent=2))

        # Modify metadata - only change visibleName
        metadata["visibleName"] = new_name

        # Update timestamp
        now_ms = str(int(time.time() * 1000))
        if "lastModified" in metadata:
            metadata["lastModified"] = now_ms

        # Write updated metadata
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Updated metadata:")
        logger.info(json.dumps(metadata, indent=2))

        # Get the notebook ID (UUID) from metadata filename
        notebook_id = os.path.splitext(os.path.basename(metadata_file))[0]
        logger.info(f"Using notebook ID: {notebook_id}")

        # Create zip for upload - IMPORTANT: Keep the original file structure
        upload_path = os.path.join(temp_dir, f"{new_name}.rmdoc")

        logger.info(f"Creating zip file at {upload_path}")
        with zipfile.ZipFile(upload_path, "w") as zipf:
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, extract_dir)
                    zipf.write(file_path, arcname)

        # Refresh before upload
        logger.info("Refreshing rmapi before upload")
        success, stdout, stderr = rmapi_adapter.run_command("refresh")
        if not success:
            logger.warning(f"Failed to refresh rmapi: {stderr}")
        else:
            logger.info("Successfully refreshed rmapi")

        # Upload modified notebook
        logger.info(f"Uploading modified notebook as: {new_name}")
        success, message = rmapi_adapter.upload_file(upload_path, new_name)

        if success:
            logger.info(f"✅ SUCCESS: Upload succeeded: {message}")
            return True
        else:
            logger.error(f"❌ FAILURE: Upload failed: {message}")
            return False

    finally:
        # Clean up
        if not args.no_cleanup:
            shutil.rmtree(temp_dir)
            logger.info("Cleaned up temporary files")


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
