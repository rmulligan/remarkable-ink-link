#!/usr/bin/env python3
"""
Create a test notebook with the correct structure and upload it directly.
This script addresses HTTP 400 errors by ensuring the correct metadata format.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

from inklink.config import CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
NOTEBOOK_NAME = "Test_Lilly_Notebook"


def run_rmapi_command(command, path=None):
    """Run rmapi command directly to work around upload issues."""
    rmapi_path = CONFIG.get("RMAPI_PATH", "./local-rmapi")

    base_cmd = [rmapi_path]
    if path:
        base_cmd.extend(["put", path])
    else:
        base_cmd.extend(command.split())

    try:
        logger.info(f"Running command: {' '.join(base_cmd)}")
        result = subprocess.run(
            base_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        # Log the output
        if result.stdout:
            logger.info(f"Command output: {result.stdout.strip()}")
        if result.stderr:
            logger.warning(f"Command error: {result.stderr.strip()}")

        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        logger.error(f"Error running rmapi command: {e}")
        return False, "", str(e)


def create_and_upload_test_notebook():
    """Create a test notebook with the correct structure and upload it directly."""

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate unique IDs
        notebook_id = str(uuid.uuid4())
        page1_id = str(uuid.uuid4())

        # Use millisecond timestamp as a string (reMarkable format)
        now_ms = str(int(time.time() * 1000))

        # Create notebook content file
        content_data = {
            "pages": [
                {
                    "id": page1_id,
                    "visibleName": "Test Query Page",
                    "lastModified": now_ms,
                    "tags": ["Lilly"],
                }
            ],
            "pageTags": {},
            "tags": ["HasLilly"],
        }

        # Create content file
        content_file_path = os.path.join(temp_dir, f"{notebook_id}.content")
        with open(content_file_path, "w") as f:
            json.dump(content_data, f, indent=2)

        # Create metadata file
        metadata_path = os.path.join(temp_dir, f"{notebook_id}.metadata")
        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "deleted": False,
                    "lastModified": now_ms,
                    "lastOpened": now_ms,
                    "lastOpenedPage": 0,
                    "metadatamodified": False,
                    "modified": False,
                    "parent": "",
                    "pinned": False,
                    "synced": True,  # Must be true for uploads
                    "type": "DocumentType",
                    "version": 1,
                    "visibleName": NOTEBOOK_NAME,
                },
                f,
                indent=2,
            )

        # Create notebook directory for pages
        pages_dir = os.path.join(temp_dir, notebook_id)
        os.makedirs(pages_dir, exist_ok=True)

        # Create page files
        page_path = os.path.join(pages_dir, f"{page1_id}.rm")
        with open(page_path, "w") as f:
            f.write("This is a test query for Lilly. #Lilly")

        # Create notebook zip
        notebook_path = os.path.join(temp_dir, f"{NOTEBOOK_NAME}.rmdoc")
        with zipfile.ZipFile(notebook_path, "w") as zipf:
            # Add content and metadata files
            zipf.write(content_file_path, os.path.basename(content_file_path))
            zipf.write(metadata_path, os.path.basename(metadata_path))

            # Add page files
            zipf.write(page_path, os.path.join(notebook_id, f"{page1_id}.rm"))

        # Make a debug copy of the rmdoc file
        debug_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "debug_upload"
        )
        os.makedirs(debug_dir, exist_ok=True)
        debug_copy = os.path.join(
            debug_dir, f"{NOTEBOOK_NAME}_{int(time.time())}.rmdoc"
        )
        shutil.copy2(notebook_path, debug_copy)
        logger.info(f"Created debug copy at: {debug_copy}")

        # First refresh rmapi to sync with remote state
        run_rmapi_command("refresh")

        time.sleep(1)  # Wait a moment for refresh to complete

        # Upload with direct rmapi command
        success, stdout, stderr = run_rmapi_command(None, notebook_path)

        if not success:
            logger.error(f"Failed to upload notebook: {stderr}")

            # Examine the notebook to help with debugging
            logger.info("Examining notebook structure for debugging...")
            with zipfile.ZipFile(notebook_path, "r") as zip_ref:
                files = zip_ref.namelist()
                logger.info(f"Zip contains files: {files}")

                # Try to extract and examine metadata
                temp_extract = tempfile.mkdtemp()
                try:
                    zip_ref.extractall(temp_extract)

                    # Check metadata files
                    for file in files:
                        if file.endswith(".metadata"):
                            metadata_debug_path = os.path.join(temp_extract, file)
                            with open(metadata_debug_path, "r") as f:
                                metadata = json.load(f)
                                logger.info(
                                    f"Metadata content: {json.dumps(metadata, indent=2)}"
                                )
                except Exception as e:
                    logger.error(f"Error examining metadata: {e}")
                finally:
                    shutil.rmtree(temp_extract)

            return False
        logger.info(f"Successfully uploaded test notebook: {NOTEBOOK_NAME}")
        return True


if __name__ == "__main__":
    if create_and_upload_test_notebook():
        print(f"Successfully created and uploaded test notebook '{NOTEBOOK_NAME}'")
    else:
        print("Failed to create and upload test notebook")
        sys.exit(1)
