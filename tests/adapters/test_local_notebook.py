#!/usr/bin/env python3
"""
Test Claude Penpal Service with a local notebook.

This script simulates the processing of a local test notebook without using rmapi,
to confirm that the subject-based directory structure is working properly.
"""

import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime

from inklink.services.claude_penpal_service import ClaudePenpalService

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
LILLY_DIR = os.path.join(os.path.expanduser("~/dev"), "Lilly")
NOTEBOOK_NAME = "Testing_Notebook"
WORK_DIR = os.path.join(LILLY_DIR, "Work")
NOTEBOOK_DIR = os.path.join(WORK_DIR, NOTEBOOK_NAME)
EXTRACTED_DIR = os.path.join(NOTEBOOK_DIR, "extracted")


def find_newest_content_file():
    """Find the most recently modified content file."""
    content_files = []
    for root, _, files in os.walk(EXTRACTED_DIR):
        for file in files:
            if file.endswith(".content"):
                content_files.append(os.path.join(root, file))

    if not content_files:
        logger.error(f"No content files found in {EXTRACTED_DIR}")
        return None

    content_files.sort(key=os.path.getmtime, reverse=True)
    content_file = content_files[0]
    logger.info(f"Using content file: {content_file}")
    return content_file


def clean_and_update_pages_directory(content_file, content_data):
    """Ensure all pages in the content file have corresponding .rm files."""
    content_id = os.path.splitext(os.path.basename(content_file))[0]
    pages_dir = os.path.join(EXTRACTED_DIR, content_id)
    os.makedirs(pages_dir, exist_ok=True)

    # Ensure every page in content has a .rm file
    for page in content_data.get("pages", []):
        page_id = page.get("id")
        page_file = os.path.join(pages_dir, f"{page_id}.rm")

        if not os.path.exists(page_file):
            logger.info(f"Creating missing page file: {page_id}")
            with open(page_file, "w") as f:
                f.write(f"Mock content for page {page_id}")


def process_local_notebook():
    """Process the local test notebook with the Claude Penpal service."""
    # Find the content file
    content_file = find_newest_content_file()
    if not content_file:
        return False

    # Load the content data
    with open(content_file, "r") as f:
        content_data = json.load(f)

    # Ensure all pages have files
    clean_and_update_pages_directory(content_file, content_data)

    # Override the rmapi adapter in the Claude Penpal service to use local files
    class MockRmapiAdapter:
        def __init__(self, *args, **kwargs):
            pass

        def list_files(self):
            return True, [
                {
                    "ID": NOTEBOOK_NAME,
                    "VissibleName": NOTEBOOK_NAME,
                    "Type": "DocumentType",
                }
            ]

        def find_tagged_notebooks(self, tag, pre_filter_tag=None):
            return [
                {
                    "id": NOTEBOOK_NAME,
                    "name": NOTEBOOK_NAME,
                    "tags": ["Subject:Work", "HasLilly"],
                }
            ]

        def download_file(self, doc_id, output_path, format="zip"):
            # Instead of downloading, we'll use our local files
            logger.info(f"Mock download of {doc_id} to {output_path}")

            # Create a temporary zip file with our local content
            temp_dir = tempfile.mkdtemp()
            try:
                # Copy content file
                temp_content_file = os.path.join(
                    temp_dir, os.path.basename(content_file)
                )
                shutil.copy2(content_file, temp_content_file)

                # Copy pages directory
                content_id = os.path.splitext(os.path.basename(content_file))[0]
                pages_dir = os.path.join(EXTRACTED_DIR, content_id)
                if os.path.exists(pages_dir):
                    temp_pages_dir = os.path.join(temp_dir, content_id)
                    os.makedirs(temp_pages_dir, exist_ok=True)

                    for item in os.listdir(pages_dir):
                        item_path = os.path.join(pages_dir, item)
                        if os.path.isfile(item_path):
                            shutil.copy2(item_path, os.path.join(temp_pages_dir, item))

                # Create a zip file
                import zipfile

                with zipfile.ZipFile(output_path, "w") as zipf:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)

                return True, "Mock download successful"
            finally:
                # Clean up the temporary directory
                shutil.rmtree(temp_dir)

        def upload_file(self, file_path, title):
            # For testing, we'll just log the upload attempt
            logger.info(f"Mock upload of {file_path} as {title}")

            # Extract the zip and save its contents to our extracted directory
            import zipfile

            # Create a new directory for the response
            response_dir = os.path.join(
                NOTEBOOK_DIR, "responses", datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            os.makedirs(response_dir, exist_ok=True)

            # Extract to response directory
            with zipfile.ZipFile(file_path, "r") as zipf:
                zipf.extractall(response_dir)

            logger.info(f"Extracted response to {response_dir}")
            return True, "Mock upload successful"

        def _check_document_for_tag(self, doc_id, tag):
            return True, content_data

    # Create service with mock adapter
    service = ClaudePenpalService(
        query_tag="Lilly",
        context_tag="Context",
        subject_tag="Subject",
        default_subject="Work",
        use_subject_dirs=True,
        pre_filter_tag=None,  # Disable pre-filtering for local test
    )

    # Replace the rmapi adapter with our mock
    service.rmapi_adapter = MockRmapiAdapter()

    # Override the process_with_claude method to not actually call Claude
    original_process_with_claude = service._process_with_claude

    def mock_process_with_claude(notebook_id, prompt, new_conversation=False):
        logger.info(f"Mock processing with Claude: {notebook_id}")
        logger.info(f"Prompt: {prompt}")
        return f"""
# Response from Claude

This is a mock response that would normally be generated by Claude.
In a real implementation, the service would send the prompt to Claude and get a real response.

## What I understood
- You tagged a page with #Lilly
- The subject of the notebook is 'Work'

## My response
This is working correctly! I can see that:
1. The notebook is organized in the proper directory structure: /dev/Lilly/Work/Testing_Notebook
2. The service correctly identified the page with the Lilly tag
3. The response is being generated and will be inserted after the query page

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # Replace the method with our mock
    service._process_with_claude = mock_process_with_claude

    # Process the notebook directly
    notebook = {
        "ID": NOTEBOOK_NAME,
        "VissibleName": NOTEBOOK_NAME,
        "Type": "DocumentType",
    }
    service._check_notebook_for_tagged_pages(notebook)

    # Restore original method
    service._process_with_claude = original_process_with_claude

    logger.info("Completed processing test notebook with Claude Penpal service")
    return True


def main():
    """Main entry point."""
    # Check if test notebook directory exists
    if not os.path.exists(NOTEBOOK_DIR):
        logger.error(f"Test notebook directory not found: {NOTEBOOK_DIR}")
        return 1

    # Process local notebook
    success = process_local_notebook()

    if success:
        logger.info("Successfully processed local notebook with Claude Penpal service")
        logger.info(f"Check the response in {NOTEBOOK_DIR}/responses/")
        return 0
    else:
        logger.error("Failed to process local notebook")
        return 1


if __name__ == "__main__":
    sys.exit(main())
