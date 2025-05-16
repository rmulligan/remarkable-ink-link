#!/usr/bin/env python3
"""
Create a test notebook with Lilly tag on a page and upload it to reMarkable.
"""

import json
import logging
import os
import tempfile
import time
import uuid
import zipfile

from inklink.adapters.rmapi_adapter import RmapiAdapter
from inklink.config import CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
NOTEBOOK_NAME = "Test_Lilly_Notebook"
NOTEBOOK_ID = str(uuid.uuid4())
SUBJECT_TAG = "Subject:Work"
LILLY_TAG = "Lilly"
CONTEXT_TAG = "Context"
HAS_LILLY_TAG = "HasLilly"


def create_test_notebook():
    """Create a test notebook with Lilly tag and upload it to reMarkable."""
    # Create temporary directory for notebook
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate IDs
        page1_id = str(uuid.uuid4())
        page2_id = str(uuid.uuid4())
        page3_id = str(uuid.uuid4())

        # Use millisecond timestamp as a string (reMarkable format)
        now_ms = str(int(time.time() * 1000))

        # Create notebook content file
        content_data = {
            "ID": NOTEBOOK_ID,
            "VissibleName": NOTEBOOK_NAME,
            "Type": "DocumentType",
            "tags": [SUBJECT_TAG, HAS_LILLY_TAG],
            "pages": [
                {
                    "id": page1_id,
                    "visibleName": "Title Page",
                    "lastModified": now_ms,
                    "tags": [],
                },
                {
                    "id": page2_id,
                    "visibleName": "Lilly Query Page",
                    "lastModified": now_ms,
                    "tags": [LILLY_TAG],
                },
                {
                    "id": page3_id,
                    "visibleName": "Context Information",
                    "lastModified": now_ms,
                    "tags": [CONTEXT_TAG],
                },
            ],
        }

        # Create content file
        content_file_path = os.path.join(temp_dir, f"{NOTEBOOK_ID}.content")
        with open(content_file_path, "w") as f:
            json.dump(content_data, f, indent=2)

        # Create metadata file
        metadata_path = os.path.join(temp_dir, f"{NOTEBOOK_ID}.metadata")
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

        # Create notebook directory
        pages_dir = os.path.join(temp_dir, NOTEBOOK_ID)
        os.makedirs(pages_dir, exist_ok=True)

        # Create page files
        for page_id in [page1_id, page2_id, page3_id]:
            page_path = os.path.join(pages_dir, f"{page_id}.rm")
            with open(page_path, "w") as f:
                f.write(f"Test content for page {page_id}")

        # Create notebook zip
        notebook_path = os.path.join(temp_dir, f"{NOTEBOOK_NAME}.rmdoc")
        with zipfile.ZipFile(notebook_path, "w") as zipf:
            # Add content and metadata files
            zipf.write(content_file_path, os.path.basename(content_file_path))
            zipf.write(metadata_path, os.path.basename(metadata_path))

            # Add page files
            for page_id in [page1_id, page2_id, page3_id]:
                page_path = os.path.join(pages_dir, f"{page_id}.rm")
                zipf.write(page_path, os.path.join(NOTEBOOK_ID, f"{page_id}.rm"))

        # Upload to reMarkable
        rmapi_path = CONFIG.get("RMAPI_PATH") or "/home/ryan/bin/rmapi"
        adapter = RmapiAdapter(rmapi_path)

        success, message = adapter.upload_file(notebook_path, NOTEBOOK_NAME)

        if success:
            logger.info(f"Successfully uploaded test notebook: {NOTEBOOK_NAME}")
            logger.info(f"Notebook has the following tags: Subject:Work, HasLilly")
            logger.info(f"Page 2 has the Lilly tag. Page 3 has the Context tag.")
            logger.info(
                "You can now run the Claude Penpal service to process this notebook."
            )
            logger.info(
                "Test with: python test_claude_penpal.py --rmapi-path=/home/ryan/bin/rmapi"
            )
            return True
        else:
            logger.error(f"Failed to upload test notebook: {message}")
            return False


if __name__ == "__main__":
    create_test_notebook()
