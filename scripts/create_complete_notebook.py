#!/usr/bin/env python3
"""
Create a notebook that matches the structure of a real reMarkable notebook.
This version creates the complete structure with all required fields.
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


def run_rmapi_command(command, path=None):
    """Run rmapi command directly."""
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

        if result.stdout:
            logger.info(f"Command output: {result.stdout.strip()}")
        if result.stderr:
            logger.warning(f"Command error: {result.stderr.strip()}")

        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        logger.error(f"Error running rmapi command: {e}")
        return False, "", str(e)


def create_rm_file_header():
    """Create the header for a .rm file."""
    # reMarkable .lines file, version=6
    header = b"reMarkable .lines file, version=6                    "
    # Add 25 00 00 00 00 01 01
    header += b"\x19\x00\x00\x00\x00\x01\x01"
    return header


def create_complete_notebook():
    """Create a notebook with structure matching real notebooks."""

    # Create a temporary directory in the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(project_dir, "temp_notebook_creation")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Generate a new notebook ID
        notebook_id = str(uuid.uuid4())
        page1_id = str(uuid.uuid4())

        # Use millisecond timestamp as a string (reMarkable format)
        now_ms = str(int(time.time() * 1000))

        # Create notebook content file with complete structure
        content_data = {
            "cPages": {
                "lastOpened": {"timestamp": "1:1", "value": page1_id},
                "original": {"timestamp": "0:0", "value": -1},
                "pages": [
                    {
                        "id": page1_id,
                        "idx": {"timestamp": "1:1", "value": "aa"},
                        "template": {"timestamp": "1:1", "value": "P Margin large"},
                    }
                ],
                "uuids": [{"first": str(uuid.uuid4()), "second": 1}],
            },
            "coverPageNumber": -1,
            "documentMetadata": {},
            "extraMetadata": {
                "LastActiveTool": "primary",
                "LastBallpointColor": "Black",
                "LastBallpointSize": "2",
                "LastPen": "Finelinerv2",
                "SecondaryPen": "Finelinerv2",
            },
            "fileType": "notebook",
            "fontName": "",
            "formatVersion": 2,
            "lineHeight": -1,
            "orientation": "portrait",
            "pageCount": 1,
            "pageTags": [],
            "sizeInBytes": "0",
            "tags": ["HasLilly"],
            "textAlignment": "justify",
            "textScale": 1,
            "zoomMode": "bestFit",
        }

        # Create content file
        content_file_path = os.path.join(temp_dir, f"{notebook_id}.content")
        with open(content_file_path, "w") as f:
            json.dump(content_data, f, indent=2)

        # Create metadata file (simpler structure)
        metadata_path = os.path.join(temp_dir, f"{notebook_id}.metadata")
        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "createdTime": now_ms,
                    "lastModified": now_ms,
                    "lastOpened": now_ms,
                    "lastOpenedPage": 0,
                    "parent": "",
                    "pinned": False,
                    "synced": True,  # Must be true for uploads
                    "type": "DocumentType",
                    "visibleName": NOTEBOOK_NAME,
                },
                f,
                indent=2,
            )

        # Create notebook directory for pages
        pages_dir = os.path.join(temp_dir, notebook_id)
        os.makedirs(pages_dir, exist_ok=True)

        # Create page file with proper .rm header
        page_path = os.path.join(pages_dir, f"{page1_id}.rm")
        with open(page_path, "wb") as f:
            # Write the header
            f.write(create_rm_file_header())
            # Write some test content (this would be stroke data in a real file)
            # For now, just write zeros to make it non-empty
            f.write(b"\x00" * 100)

        # Create notebook zip
        notebook_path = os.path.join(temp_dir, f"{NOTEBOOK_NAME}.rmdoc")
        with zipfile.ZipFile(notebook_path, "w", zipfile.ZIP_STORED) as zipf:
            # Add content and metadata files
            zipf.write(content_file_path, os.path.basename(content_file_path))
            zipf.write(metadata_path, os.path.basename(metadata_path))

            # Add page file with correct path
            zipf.write(page_path, os.path.join(notebook_id, f"{page1_id}.rm"))

        # Make a debug copy of the rmdoc file
        debug_dir = os.path.join(project_dir, "debug_upload")
        os.makedirs(debug_dir, exist_ok=True)
        debug_copy = os.path.join(
            debug_dir, f"{NOTEBOOK_NAME}_complete_{int(time.time())}.rmdoc"
        )
        import shutil

        shutil.copy2(notebook_path, debug_copy)
        logger.info(f"Created debug copy at: {debug_copy}")

        # First refresh rmapi to sync with remote state
        run_rmapi_command("refresh")

        time.sleep(1)  # Wait a moment for refresh to complete

        # Upload with direct rmapi command
        success, stdout, stderr = run_rmapi_command(None, notebook_path)

        if not success:
            logger.error(f"Failed to upload notebook: {stderr}")
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
    if create_complete_notebook():
        print(
            f"Successfully created and uploaded complete test notebook '{NOTEBOOK_NAME}'"
        )
        print("You can now run the Claude Penpal service to process this notebook.")
    else:
        print(f"Failed to create and upload complete test notebook")
        sys.exit(1)
