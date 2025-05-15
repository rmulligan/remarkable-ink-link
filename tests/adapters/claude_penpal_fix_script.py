#!/usr/bin/env python3
"""
Test script for Claude Penpal Service with real reMarkable notebooks.

This script tests the Claude Penpal Service with actual reMarkable notebooks
to ensure that the metadata handling fixes resolve the HTTP 400 errors when
uploading modified notebooks to the reMarkable Cloud.

Usage:
    python test_claude_penpal_fix.py [--tag TAG] [--test-tag TEST_TAG]

Arguments:
    --tag TAG                The tag to look for in notebooks (default: Lilly)
    --test-tag TEST_TAG      The tag to add for test purposes (default: LillyTest)
"""

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import uuid
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_claude_penpal_fix")

# Import project modules
try:
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG
    from inklink.services.claude_penpal_service import ClaudePenpalService
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG
    from inklink.services.claude_penpal_service import ClaudePenpalService


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test Claude Penpal Service with real notebooks"
    )
    parser.add_argument(
        "--tag", type=str, default="Lilly", help="Tag to look for in notebooks"
    )
    parser.add_argument(
        "--test-tag", type=str, default="LillyTest", help="Tag to add for test purposes"
    )
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument("--claude-command", type=str, help="Claude CLI command")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    return parser.parse_args()


def setup_environment(args):
    """Set up the test environment."""
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Configure RMAPI path
    rmapi_path = args.rmapi_path or CONFIG.get("RMAPI_PATH")
    if not os.path.exists(rmapi_path):
        logger.error(f"RMAPI executable not found at {rmapi_path}")
        sys.exit(1)
    logger.info(f"Using RMAPI path: {rmapi_path}")

    # Configure Claude CLI command
    claude_command = args.claude_command or CONFIG.get(
        "CLAUDE_COMMAND", "/home/ryan/.claude/local/claude"
    )
    logger.info(f"Using Claude command: {claude_command}")

    return rmapi_path, claude_command


def find_test_notebook(rmapi_adapter, tag):
    """Find a notebook with the specified tag."""
    logger.info(f"Searching for notebooks with tag '{tag}'...")

    # Check if rmapi is accessible
    if not rmapi_adapter.ping():
        logger.error("Cannot connect to reMarkable Cloud. Check authentication.")
        return None

    # Find tagged notebooks
    tagged_notebooks = rmapi_adapter.find_tagged_notebooks(tag=tag)

    if not tagged_notebooks:
        logger.warning(f"No notebooks found with tag '{tag}'")
        return None

    logger.info(f"Found {len(tagged_notebooks)} notebooks with tag '{tag}'")

    # Select the first notebook for testing
    test_notebook = tagged_notebooks[0]
    notebook_id = test_notebook.get("id")
    notebook_name = test_notebook.get("name", "Unknown")

    logger.info(f"Selected notebook '{notebook_name}' (ID: {notebook_id}) for testing")
    return test_notebook


def download_and_extract_notebook(rmapi_adapter, notebook_id, notebook_name):
    """Download and extract a notebook from reMarkable Cloud."""
    logger.info(f"Downloading notebook '{notebook_name}' (ID: {notebook_id})...")

    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp(prefix="claude_penpal_test_")

    try:
        # Download the notebook
        zip_path = os.path.join(temp_dir, f"{notebook_name}.rmdoc")
        success, message = rmapi_adapter.download_file(notebook_id, zip_path, "zip")

        if not success:
            logger.error(f"Failed to download notebook: {message}")
            return None, None

        # Extract the notebook
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Find content and metadata files
        content_file_path = None
        metadata_file_path = None

        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(".content"):
                    content_file_path = os.path.join(root, file)
                    content_id = os.path.splitext(file)[0]
                    metadata_file_path = os.path.join(root, f"{content_id}.metadata")
                    break

        if not content_file_path or not os.path.exists(content_file_path):
            logger.error(f"Content file not found in extracted notebook")
            return None, None

        if not metadata_file_path or not os.path.exists(metadata_file_path):
            logger.error(f"Metadata file not found in extracted notebook")
            return None, None

        # Load content and metadata
        with open(content_file_path, "r") as f:
            content = json.load(f)

        with open(metadata_file_path, "r") as f:
            metadata = json.load(f)

        logger.info(f"Successfully downloaded and extracted notebook")
        return temp_dir, {
            "notebook_id": notebook_id,
            "notebook_name": notebook_name,
            "zip_path": zip_path,
            "extract_dir": extract_dir,
            "content_file_path": content_file_path,
            "metadata_file_path": metadata_file_path,
            "content": content,
            "metadata": metadata,
        }

    except Exception as e:
        logger.error(f"Error downloading and extracting notebook: {e}")
        shutil.rmtree(temp_dir)
        return None, None


def insert_test_response(notebook_data):
    """Insert a test response page into the notebook."""
    logger.info("Inserting test response page...")

    try:
        # Get notebook info
        content_file_path = notebook_data["content_file_path"]
        metadata_file_path = notebook_data["metadata_file_path"]
        content = notebook_data["content"]
        metadata = notebook_data["metadata"]

        # Generate a new page ID
        response_page_id = str(uuid.uuid4())

        # Current timestamp in milliseconds (reMarkable format)
        now_ms = int(time.time() * 1000)

        # Create a test response page
        response_page = {
            "id": response_page_id,
            "visibleName": f"Test Response {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "lastModified": now_ms,
            "tags": [],
        }

        # Add response page to the content
        pages = content.get("pages", [])
        pages.append(response_page)
        content["pages"] = pages

        # Ensure pageTags exists
        if "pageTags" not in content or content["pageTags"] is None:
            content["pageTags"] = {}

        # Update notebook metadata in reMarkable format
        metadata.update(
            {
                "visibleName": notebook_data["notebook_name"],
                "type": "DocumentType",
                "parent": metadata.get("parent", ""),
                "lastModified": str(now_ms),
                "lastOpened": metadata.get("lastOpened", ""),
                "lastOpenedPage": 0,
                "version": metadata.get("version", 0) + 1,
                "pinned": False,
                "synced": True,  # Important: this must be true for reMarkable
                "modified": False,
                "deleted": False,
                "metadatamodified": False,
            }
        )

        # Create a blank .rm file for the page
        page_dir = os.path.dirname(content_file_path)
        page_file_path = os.path.join(page_dir, f"{response_page_id}.rm")

        # Write sample content to the page file (minimal .rm format)
        with open(page_file_path, "w") as f:
            f.write("Test response page content")

        # Write updated content and metadata
        with open(content_file_path, "w") as f:
            json.dump(content, f)

        with open(metadata_file_path, "w") as f:
            json.dump(metadata, f)

        logger.info(
            f"Successfully inserted test response page (ID: {response_page_id})"
        )
        return True, response_page_id

    except Exception as e:
        logger.error(f"Error inserting test response: {e}")
        return False, None


def create_modified_zip(notebook_data):
    """Create a zip file from the modified notebook."""
    logger.info("Creating modified notebook zip file...")

    try:
        # Create a temporary directory for the modified zip
        temp_dir = os.path.dirname(notebook_data["zip_path"])
        modified_path = os.path.join(
            temp_dir,
            f"modified_{notebook_data['notebook_name']}_{time.strftime('%Y%m%d_%H%M%S')}.rmdoc",
        )

        # Create the zip file
        with zipfile.ZipFile(modified_path, "w") as zipf:
            for root, _, files in os.walk(notebook_data["extract_dir"]):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(
                        file_path,
                        os.path.relpath(file_path, notebook_data["extract_dir"]),
                    )

        logger.info(f"Created modified notebook zip at {modified_path}")
        return True, modified_path

    except Exception as e:
        logger.error(f"Error creating modified zip: {e}")
        return False, None


def upload_modified_notebook(rmapi_adapter, modified_path, notebook_name):
    """Upload the modified notebook to reMarkable Cloud."""
    logger.info(f"Uploading modified notebook '{notebook_name}'...")

    try:
        # Upload the modified notebook
        success, message = rmapi_adapter.upload_file(modified_path, notebook_name)

        if not success:
            logger.error(f"Failed to upload modified notebook: {message}")
            return False

        logger.info(f"Successfully uploaded modified notebook: {message}")
        return True

    except Exception as e:
        logger.error(f"Error uploading modified notebook: {e}")
        return False


def test_claude_penpal_service(args, rmapi_path, claude_command):
    """Test the Claude Penpal Service with real notebooks."""
    logger.info("Starting Claude Penpal Service test with real notebooks...")

    # Create rmapi adapter
    rmapi_adapter = RmapiAdapter(rmapi_path)

    # Find a test notebook
    test_notebook = find_test_notebook(rmapi_adapter, args.tag)
    if not test_notebook:
        return False

    # Download and extract the notebook
    temp_dir, notebook_data = download_and_extract_notebook(
        rmapi_adapter, test_notebook.get("id"), test_notebook.get("name")
    )

    if not temp_dir or not notebook_data:
        return False

    try:
        # Insert test response
        success, response_page_id = insert_test_response(notebook_data)
        if not success:
            return False

        # Create modified zip
        success, modified_path = create_modified_zip(notebook_data)
        if not success:
            return False

        # Upload modified notebook
        success = upload_modified_notebook(
            rmapi_adapter, modified_path, notebook_data["notebook_name"]
        )

        if not success:
            return False

        logger.info("All steps completed successfully!")
        return True

    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory {temp_dir}")


def test_claude_penpal_full_workflow(args, rmapi_path, claude_command):
    """Test the full ClaudePenpalService workflow."""
    logger.info("Testing full Claude Penpal Service workflow...")

    # Create the service
    claude_penpal_service = ClaudePenpalService(
        rmapi_path=rmapi_path,
        claude_command=claude_command,
        query_tag=args.tag,
        pre_filter_tag=args.test_tag,
    )

    # Start monitoring
    logger.info("Starting monitoring...")
    claude_penpal_service.start_monitoring()

    try:
        # Wait for processing
        logger.info("Waiting for processing (30 seconds)...")
        time.sleep(30)

        # Check if any pages were processed
        processed_count = len(claude_penpal_service.processed_pages)
        logger.info(f"Processed {processed_count} pages")

        return processed_count > 0

    finally:
        # Stop monitoring
        logger.info("Stopping monitoring...")
        claude_penpal_service.stop_monitoring()


def main():
    """Main entry point."""
    args = parse_args()
    rmapi_path, claude_command = setup_environment(args)

    # Run individual test
    logger.info("=== Testing notebook metadata handling ===")
    metadata_success = test_claude_penpal_service(args, rmapi_path, claude_command)

    # Run full workflow test
    logger.info("\n=== Testing full Claude Penpal Service workflow ===")
    workflow_success = test_claude_penpal_full_workflow(
        args, rmapi_path, claude_command
    )

    # Print summary
    logger.info("\n=== Test Summary ===")
    logger.info(f"Metadata handling test: {'PASS' if metadata_success else 'FAIL'}")
    logger.info(f"Full workflow test: {'PASS' if workflow_success else 'FAIL'}")

    if metadata_success and workflow_success:
        logger.info("All tests PASSED!")
        return 0
    else:
        logger.error("Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
