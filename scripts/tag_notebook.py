#!/usr/bin/env python3
"""
Tag an existing reMarkable notebook with HasLilly and Lilly tags.
"""

import os
import json
import logging
import tempfile
import zipfile
import sys

from inklink.adapters.rmapi_adapter import RmapiAdapter

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def tag_notebook(notebook_name):
    """
    Tag a notebook with HasLilly at document level and add Lilly tag to a page.

    Args:
        notebook_name: Name of the notebook to tag
    """
    # Initialize the RmapiAdapter
    rmapi_path = os.path.abspath("/home/ryan/bin/rmapi")
    adapter = RmapiAdapter(rmapi_path)

    # Verify the notebook exists
    success, notebooks = adapter.list_files()
    if not success:
        logger.error("Failed to list notebooks")
        return False

    target_notebook = None
    for notebook in notebooks:
        if (
            notebook.get("VissibleName") == notebook_name
            and notebook.get("Type") == "DocumentType"
        ):
            target_notebook = notebook
            break

    if not target_notebook:
        logger.error(f"Notebook not found: {notebook_name}")
        return False

    notebook_id = target_notebook.get("ID")
    logger.info(f"Found notebook: {notebook_name} (ID: {notebook_id})")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download the notebook
        download_path = os.path.join(temp_dir, f"{notebook_name}.rmdoc")
        success, message = adapter.download_file(notebook_id, download_path, "zip")

        if not success:
            logger.error(f"Failed to download notebook: {message}")
            return False

        logger.info(f"Downloaded notebook to {download_path}")

        # Extract the notebook
        extraction_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extraction_dir, exist_ok=True)

        with zipfile.ZipFile(download_path, "r") as zip_ref:
            zip_ref.extractall(extraction_dir)

        # Find content file
        content_file_path = None
        for root, _, files in os.walk(extraction_dir):
            for file in files:
                if file.endswith(".content"):
                    content_file_path = os.path.join(root, file)
                    break

        if not content_file_path:
            logger.error("No content file found in notebook")
            return False

        # Load content
        with open(content_file_path, "r") as f:
            content = json.load(f)

        # Add HasLilly tag to notebook
        if "tags" not in content:
            content["tags"] = []

        if "HasLilly" not in content["tags"]:
            content["tags"].append("HasLilly")
            logger.info("Added HasLilly tag to notebook")

        # Get or create pages
        pages = content.get("pages", [])
        if not pages:
            logger.info("No pages found in notebook, creating a new page")
            # Create a new page ID
            import uuid

            page_id = str(uuid.uuid4())
            # Create a simple page
            first_page = {
                "id": page_id,
                "visibleName": "Test Query Page",
                "tags": ["Lilly"],
            }
            pages.append(first_page)
            content["pages"] = pages

            # Create page file
            page_dir = None
            content_id = os.path.splitext(os.path.basename(content_file_path))[0]
            page_dir = os.path.join(os.path.dirname(content_file_path), content_id)
            os.makedirs(page_dir, exist_ok=True)

            # Create page file
            page_file_path = os.path.join(page_dir, f"{page_id}.rm")
            with open(page_file_path, "w") as f:
                f.write("Test content for the Lilly query page")

            logger.info(f"Created new page with ID: {page_id}")
        else:
            # Add Lilly tag to first page
            first_page = pages[0]
            if "tags" not in first_page:
                first_page["tags"] = []

            if "Lilly" not in first_page["tags"]:
                first_page["tags"].append("Lilly")
                logger.info(
                    f"Added Lilly tag to page: {first_page.get('visibleName', first_page.get('id'))}"
                )

        # Save modified content
        with open(content_file_path, "w") as f:
            json.dump(content, f, indent=2)

        # Create modified zip
        modified_path = os.path.join(temp_dir, f"{notebook_name}_modified.rmdoc")
        with zipfile.ZipFile(modified_path, "w") as zipf:
            for root, _, files in os.walk(extraction_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, extraction_dir)
                    zipf.write(file_path, arcname)

        # Upload modified notebook
        success, message = adapter.upload_file(modified_path, notebook_name)

        if success:
            logger.info(f"Successfully tagged notebook: {notebook_name}")
            logger.info(
                "You can now run the Claude Penpal service to process this notebook."
            )
            return True
        else:
            logger.error(f"Failed to upload modified notebook: {message}")
            return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tag_notebook.py <notebook_name>")
        sys.exit(1)

    notebook_name = sys.argv[1]
    tag_notebook(notebook_name)
