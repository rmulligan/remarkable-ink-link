#!/usr/bin/env python3
"""Quick test for Claude Penpal Service with local notebook."""

import logging
import os
import sys

from inklink.services.claude_penpal_service import ClaudePenpalService

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Process a local test notebook with the Claude Penpal Service."""
    # Check if our test notebook exists
    test_notebook_dir = os.path.join(
        os.path.expanduser("~/dev/Lilly/Work/Testing_Notebook")
    )
    if not os.path.exists(test_notebook_dir):
        logger.error(f"Test notebook directory not found: {test_notebook_dir}")
        logger.info("Please run run_mock_penpal.py first to create the test notebook")
        return 1

    # Path to the test notebook file
    test_notebook_path = os.path.join(test_notebook_dir, "Testing_Notebook.rmdoc")
    if not os.path.exists(test_notebook_path):
        logger.error(f"Test notebook file not found: {test_notebook_path}")
        return 1

    extracted_dir = os.path.join(test_notebook_dir, "extracted")
    if not os.path.exists(extracted_dir):
        logger.error(f"Extracted directory not found: {extracted_dir}")
        return 1

    # Find content file
    content_files = []
    for root, _, files in os.walk(extracted_dir):
        for file in files:
            if file.endswith(".content"):
                content_files.append(os.path.join(root, file))

    if not content_files:
        logger.error(f"No content file found in {extracted_dir}")
        return 1

    content_file = content_files[0]
    logger.info(f"Using content file: {content_file}")

    # Create and configure the service
    service = ClaudePenpalService(
        rmapi_path=os.path.abspath("/home/ryan/bin/rmapi"),
        query_tag="Lilly",
        context_tag="Context",
        subject_tag="Subject",
        default_subject="Work",
        use_subject_dirs=True,
        pre_filter_tag=None,  # Disable pre-filtering for local test
    )

    logger.info("Initialized Claude Penpal Service")

    # Process the test notebook directly
    logger.info(f"Processing test notebook at {test_notebook_path}")

    # Extract notebook ID from content file path
    notebook_id = (
        os.path.basename(os.path.dirname(content_file))
        if os.path.dirname(content_file)
        else None
    )

    if not notebook_id:
        logger.error("Could not determine notebook ID from content file path")
        return 1

    # Prepare a mock notebook dictionary
    notebook = {
        "ID": "Testing_Notebook",
        "VissibleName": "Testing_Notebook",
        "Type": "DocumentType",
    }

    # Process the notebook
    service._check_notebook_for_tagged_pages(notebook)

    logger.info("Completed processing test notebook")
    return 0


if __name__ == "__main__":
    sys.exit(main())
