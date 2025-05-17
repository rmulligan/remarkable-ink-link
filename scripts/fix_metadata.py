#!/usr/bin/env python3
"""
Fix metadata in reMarkable notebooks.

This script ensures that both content and metadata files are properly updated
when modifying notebooks, addressing issues with the reMarkable Cloud API.
"""

import json
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
NOTEBOOK_NAME = "Testing Notebook"
LILLY_DIR = os.path.join(os.path.expanduser("~/dev"), "Lilly")
WORK_DIR = os.path.join(LILLY_DIR, "Work")
NOTEBOOK_DIR = os.path.join(WORK_DIR, "Testing_Notebook")
EXTRACTED_DIR = os.path.join(NOTEBOOK_DIR, "extracted")
RMAPI_PATH = "/home/ryan/bin/rmapi"


def find_content_files():
    """Find content and metadata files in the extracted directory."""
    content_files = []
    metadata_files = []

    for root, _, files in os.walk(EXTRACTED_DIR):
        for file in files:
            if file.endswith(".content"):
                content_files.append(os.path.join(root, file))
            elif file.endswith(".metadata"):
                metadata_files.append(os.path.join(root, file))

    if not content_files:
        logger.error(f"No content files found in {EXTRACTED_DIR}")
        return None, None

    # Sort by modification time, newest first
    content_files.sort(key=os.path.getmtime, reverse=True)
    content_file = content_files[0]
    logger.info(f"Using content file: {content_file}")

    # Find corresponding metadata file
    content_id = os.path.splitext(os.path.basename(content_file))[0]
    metadata_file = None

    for mf in metadata_files:
        if os.path.splitext(os.path.basename(mf))[0] == content_id:
            metadata_file = mf
            logger.info(f"Found matching metadata file: {metadata_file}")
            break

    if not metadata_file:
        logger.warning(f"No matching metadata file found for content ID: {content_id}")

    return content_file, metadata_file


def update_metadata(content_file, metadata_file):
    """Update the metadata to match the content file."""
    try:
        # Load content file
        with open(content_file, "r") as f:
            content_data = json.load(f)

        # Load metadata file if it exists, or create new
        metadata = {}
        if metadata_file and os.path.exists(metadata_file):
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Failed to parse metadata file, creating new one")

        # Update metadata based on content
        now = datetime.now().isoformat()

        # Ensure basic metadata fields exist
        metadata.update(
            {
                "deleted": False,
                "lastModified": now,
                "lastOpened": now,
                "lastOpenedPage": 0,
                "metadatamodified": True,
                "modified": True,
                "parent": "",
                "pinned": False,
                "synced": False,
                "type": "DocumentType",
                "version": 1,
                "visibleName": content_data.get("VissibleName", "Notebook"),
            }
        )

        # Get content ID
        content_id = os.path.splitext(os.path.basename(content_file))[0]

        # Create or update metadata file
        if not metadata_file:
            metadata_file = os.path.join(
                os.path.dirname(content_file), f"{content_id}.metadata"
            )

        # Write updated metadata
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Updated metadata file: {metadata_file}")
        return True

    except Exception as e:
        logger.error(f"Error updating metadata: {e}")
        return False


def create_modified_rmdoc():
    """Create a new rmdoc file with updated metadata."""
    # Find content and metadata files
    content_file, metadata_file = find_content_files()
    if not content_file:
        return None

    # Update metadata
    if not update_metadata(content_file, metadata_file):
        logger.warning("Failed to update metadata, continuing anyway")

    # Get content ID
    content_id = os.path.splitext(os.path.basename(content_file))[0]
    logger.info(f"Working with content ID: {content_id}")

    # Create temporary directory for the new rmdoc
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy content file to temp dir
        temp_content_file = os.path.join(temp_dir, os.path.basename(content_file))
        shutil.copy2(content_file, temp_content_file)

        # Copy metadata file if it exists
        if metadata_file and os.path.exists(metadata_file):
            temp_metadata_file = os.path.join(temp_dir, os.path.basename(metadata_file))
            shutil.copy2(metadata_file, temp_metadata_file)

        # Create directory for the page files
        temp_pages_dir = os.path.join(temp_dir, content_id)
        os.makedirs(temp_pages_dir, exist_ok=True)

        # Copy all page files
        pages_dir = os.path.join(EXTRACTED_DIR, content_id)
        if os.path.exists(pages_dir):
            for item in os.listdir(pages_dir):
                src = os.path.join(pages_dir, item)
                dst = os.path.join(temp_pages_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)

        # List all files that will be included in the rmdoc
        logger.info("Files to be included in rmdoc:")
        for root, _, files in os.walk(temp_dir):
            for file in files:
                logger.info(f"  {os.path.join(root, file)}")

        # Create the zip file
        modified_rmdoc = os.path.join(
            NOTEBOOK_DIR, f"{NOTEBOOK_NAME}_metadata_fixed.rmdoc"
        )
        with zipfile.ZipFile(modified_rmdoc, "w") as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        logger.info(f"Created modified rmdoc at {modified_rmdoc}")
        return modified_rmdoc


def upload_to_remarkable(rmdoc_path):
    """Upload the modified rmdoc to reMarkable cloud."""
    if not os.path.exists(rmdoc_path):
        logger.error(f"rmdoc file not found: {rmdoc_path}")
        return False

    # Upload the modified notebook
    logger.info("Uploading modified notebook to reMarkable...")

    # First remove any existing notebook with the same name
    import subprocess

    remove_cmd = f"{RMAPI_PATH} rm '{NOTEBOOK_NAME}'"
    try:
        subprocess.run(remove_cmd, shell=True, check=False)
        logger.info("Removed existing notebook if it existed")
    except Exception as e:
        logger.warning(f"Error removing existing notebook: {e}")

    # Upload the new notebook
    upload_cmd = f"{RMAPI_PATH} put '{rmdoc_path}'"
    try:
        result = subprocess.run(
            upload_cmd, shell=True, check=True, capture_output=True, text=True
        )
        logger.info(f"Upload output: {result.stdout}")

        # If uploaded with a different name, rename it
        if NOTEBOOK_NAME not in rmdoc_path:
            # Try to extract the ID from output
            id_line = next(
                (line for line in result.stdout.splitlines() if "ID:" in line), None
            )
            if id_line:
                doc_id = id_line.split("ID:")[1].strip()
                rename_cmd = f"{RMAPI_PATH} mv '{doc_id}' '{NOTEBOOK_NAME}'"
                subprocess.run(rename_cmd, shell=True, check=True)
                logger.info(f"Renamed document to {NOTEBOOK_NAME}")

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Upload failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False


def main():
    """Main entry point."""
    # Check if notebook directory exists
    if not os.path.exists(NOTEBOOK_DIR):
        logger.error(f"Notebook directory not found: {NOTEBOOK_DIR}")
        return 1

    # Create modified rmdoc with fixed metadata
    modified_rmdoc = create_modified_rmdoc()
    if not modified_rmdoc:
        logger.error("Failed to create modified rmdoc")
        return 1

    # Upload to reMarkable
    success = upload_to_remarkable(modified_rmdoc)

    if success:
        logger.info("Successfully uploaded notebook with fixed metadata")
        return 0
    logger.error("Failed to upload notebook")
    return 1


if __name__ == "__main__":
    sys.exit(main())
