#!/usr/bin/env python3
"""
Update Testing Notebook on reMarkable cloud with local changes.

This script takes the local test notebook that has been modified by the mock penpal
service and uploads it back to the reMarkable cloud.
"""

import glob
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

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


def find_content_file():
    """Find the most recent content file in the extracted directory."""
    content_files = glob.glob(os.path.join(EXTRACTED_DIR, "*.content"))
    if not content_files:
        logger.error(f"No content files found in {EXTRACTED_DIR}")
        return None

    # Sort by modification time, newest first
    content_files.sort(key=os.path.getmtime, reverse=True)
    content_file = content_files[0]
    logger.info(f"Using content file: {content_file}")

    return content_file


def create_modified_rmdoc():
    """Create a new rmdoc file with the modified content."""
    content_file = find_content_file()
    if not content_file:
        return None

    content_id = os.path.splitext(os.path.basename(content_file))[0]
    logger.info(f"Found content ID: {content_id}")

    # Create temporary directory for the new rmdoc
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy content file to temp dir
        temp_content_file = os.path.join(temp_dir, os.path.basename(content_file))
        shutil.copy2(content_file, temp_content_file)

        # Find and copy metadata file if it exists
        metadata_file = os.path.join(EXTRACTED_DIR, f"{content_id}.metadata")
        if os.path.exists(metadata_file):
            temp_metadata_file = os.path.join(temp_dir, os.path.basename(metadata_file))
            shutil.copy2(metadata_file, temp_metadata_file)

        # Create directory for the page files
        temp_pages_dir = os.path.join(temp_dir, content_id)
        os.makedirs(temp_pages_dir, exist_ok=True)

        # Copy all page files
        pages_dir = os.path.join(EXTRACTED_DIR, content_id)
        if os.path.exists(pages_dir):
            page_files = glob.glob(os.path.join(pages_dir, "*.rm"))
            for page_file in page_files:
                shutil.copy2(
                    page_file, os.path.join(temp_pages_dir, os.path.basename(page_file))
                )

        # Copy other files that may have page content
        for rm_file in glob.glob(os.path.join(EXTRACTED_DIR, "*.rm")):
            shutil.copy2(
                rm_file, os.path.join(temp_pages_dir, os.path.basename(rm_file))
            )

        # List all files that will be included in the rmdoc
        logger.info("Files to be included in rmdoc:")
        for root, _, files in os.walk(temp_dir):
            for file in files:
                logger.info(f"  {os.path.join(root, file)}")

        # Create the zip file
        modified_rmdoc = os.path.join(NOTEBOOK_DIR, f"{NOTEBOOK_NAME}_updated.rmdoc")
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

    # First try to delete the existing notebook
    logger.info(f"Trying to delete existing notebook: {NOTEBOOK_NAME}")
    delete_cmd = f"{RMAPI_PATH} rm '{NOTEBOOK_NAME}'"
    try:
        subprocess.run(delete_cmd, shell=True, check=False, capture_output=True)
        logger.info("Deleted existing notebook (if it existed)")
    except Exception as e:
        logger.warning(f"Error deleting notebook (may not exist): {e}")

    # Upload the modified notebook
    logger.info("Uploading modified notebook to reMarkable...")
    upload_cmd = f"{RMAPI_PATH} put '{rmdoc_path}'"

    try:
        process = subprocess.run(
            upload_cmd, shell=True, check=True, capture_output=True, text=True
        )
        logger.info(f"Upload output: {process.stdout}")
        if process.returncode == 0:
            logger.info("Successfully uploaded notebook")

            # Rename to original name if needed
            id_line = next(
                (line for line in process.stdout.splitlines() if "ID:" in line), None
            )
            if id_line:
                doc_id = id_line.split("ID:")[1].strip()
                logger.info(f"Uploaded document ID: {doc_id}")

                rename_cmd = f"{RMAPI_PATH} mv '{doc_id}' '{NOTEBOOK_NAME}'"
                subprocess.run(rename_cmd, shell=True, check=True)
                logger.info(f"Renamed document to '{NOTEBOOK_NAME}'")

            return True
        logger.error(f"Upload failed with return code {process.returncode}")
        logger.error(f"Error: {process.stderr}")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Upload failed: {e}")
        logger.error(f"Output: {e.output}")
        logger.error(f"Error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error uploading notebook: {e}")
        return False


def main():
    """Main entry point."""
    # Check if test notebook directory exists
    if not os.path.exists(NOTEBOOK_DIR):
        logger.error(f"Test notebook directory not found: {NOTEBOOK_DIR}")
        return 1

    # Create modified rmdoc file
    modified_rmdoc = create_modified_rmdoc()
    if not modified_rmdoc:
        logger.error("Failed to create modified rmdoc file")
        return 1

    # Upload to reMarkable
    success = upload_to_remarkable(modified_rmdoc)

    if success:
        logger.info(
            f"Successfully updated notebook '{NOTEBOOK_NAME}' on reMarkable cloud"
        )
        logger.info(
            "You can now run the Claude Penpal service to process this notebook"
        )
        return 0
    logger.error(f"Failed to update notebook '{NOTEBOOK_NAME}'")
    return 1


if __name__ == "__main__":
    sys.exit(main())
