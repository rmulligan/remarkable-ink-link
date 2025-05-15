#!/usr/bin/env python3
"""
Create a properly structured notebook that matches the format expected by rmapi.
This script creates a notebook with both metadata and content files.
"""

import os
import sys
import json
import logging
import time
import zipfile
import tempfile
import uuid
import subprocess

from inklink.config import CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
NOTEBOOK_NAME = "Test_Claude_Penpal_Notebook"


def run_rmapi_command(command, path=None, name=None):
    """Run rmapi command directly to work around upload issues."""
    rmapi_path = CONFIG.get("RMAPI_PATH", "./local-rmapi")

    base_cmd = [rmapi_path]
    if path:
        # For uploads, rmapi expects: rmapi put <file>
        # The file will be uploaded with its base name automatically
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


def create_proper_notebook():
    """Create a notebook with proper structure based on existing notebooks."""

    # Create a temporary directory in the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(project_dir, "temp_notebook_creation")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Generate a new notebook ID to avoid conflicts
        notebook_id = str(uuid.uuid4())
        page1_id = str(uuid.uuid4())

        # Use millisecond timestamp as a string (reMarkable format)
        now_ms = str(int(time.time() * 1000))

        # Create notebook content file
        content_data = {
            "pages": [
                {
                    "id": page1_id,
                    "visibleName": "Query Page",
                    "lastModified": now_ms,
                    "tags": ["Lilly"],
                }
            ],
            "tags": ["HasLilly"],
            "pageTags": {},  # This field seems to be required even if empty
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
                    "createdTime": "1747201671936",  # Keep original creation time
                    "lastModified": now_ms,
                    "lastOpened": now_ms,
                    "lastOpenedPage": 0,
                    "parent": "",
                    "pinned": False,
                    "synced": True,  # Must be true for uploads
                    "type": "DocumentType",
                    "version": 1,
                    "visibleName": NOTEBOOK_NAME,
                    "tags": ["HasLilly"],  # Also include tags in metadata
                },
                f,
                indent=2,
            )

        # Create notebook directory for pages if it doesn't exist
        pages_dir = os.path.join(temp_dir, notebook_id)
        os.makedirs(pages_dir, exist_ok=True)

        # Create page file with test content
        page_path = os.path.join(pages_dir, f"{page1_id}.rm")
        # Create a simple .rm file (this would normally be a complex binary format)
        # For now, just create it as a text file
        with open(page_path, "w") as f:
            f.write(
                """This is a test query for the Claude Penpal service.

Please tell me about the metadata structure required for reMarkable notebooks.

#Lilly"""
            )

        # Create notebook zip
        notebook_path = os.path.join(temp_dir, f"{NOTEBOOK_NAME}.rmdoc")
        with zipfile.ZipFile(notebook_path, "w") as zipf:
            # Add content and metadata files
            zipf.write(content_file_path, os.path.basename(content_file_path))
            zipf.write(metadata_path, os.path.basename(metadata_path))

            # Add page file with correct path
            zipf.write(page_path, os.path.join(notebook_id, f"{page1_id}.rm"))

        # Make a debug copy of the rmdoc file
        debug_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "debug_upload"
        )
        os.makedirs(debug_dir, exist_ok=True)
        debug_copy = os.path.join(
            debug_dir, f"{NOTEBOOK_NAME}_{int(time.time())}.rmdoc"
        )
        import shutil

        shutil.copy2(notebook_path, debug_copy)
        logger.info(f"Created debug copy at: {debug_copy}")

        # First refresh rmapi to sync with remote state
        run_rmapi_command("refresh")

        time.sleep(1)  # Wait a moment for refresh to complete

        # Upload with direct rmapi command
        # rmapi will use the base name of the file automatically
        success, stdout, stderr = run_rmapi_command(None, notebook_path)

        if not success:
            logger.error(f"Failed to upload notebook: {stderr}")

            # Try to understand the format of the HTTP 400 error
            if "400" in stderr:
                logger.info("Received HTTP 400 error. Examining notebook structure...")

                # Output the exact structure of what we're trying to upload
                with zipfile.ZipFile(notebook_path, "r") as zip_ref:
                    logger.info(f"Files in notebook: {zip_ref.namelist()}")

                    # Check each file
                    for file_name in zip_ref.namelist():
                        with zip_ref.open(file_name) as f:
                            content = f.read()
                            logger.info(
                                f"File: {file_name}, Size: {len(content)} bytes"
                            )

                            # If it's JSON, show it
                            if file_name.endswith((".metadata", ".content")):
                                try:
                                    json_content = json.loads(content)
                                    logger.info(f"JSON content of {file_name}:")
                                    logger.info(json.dumps(json_content, indent=2))
                                except Exception as e:
                                    logger.error(f"Error parsing JSON: {e}")

            return False
        else:
            logger.info(f"Successfully uploaded test notebook: {NOTEBOOK_NAME}")
            return True
    finally:
        # Clean up the temporary directory
        if os.path.exists(temp_dir):
            logger.info(f"Cleaning up temporary directory: {temp_dir}")
            import shutil

            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {e}")


if __name__ == "__main__":
    if create_proper_notebook():
        print(
            f"Successfully created and uploaded proper test notebook '{NOTEBOOK_NAME}'"
        )
        print("You can now run the Claude Penpal service to process this notebook.")
    else:
        print(f"Failed to create and upload proper test notebook")
        sys.exit(1)
