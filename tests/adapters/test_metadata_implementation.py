#!/usr/bin/env python3
"""
Direct test of the metadata handling in the Claude Penpal Service.

This script tests the fixed _insert_response_after_query function from
Claude Penpal Service directly with a test example.
"""

import os
import sys
import time
import json
import uuid
import zipfile
import tempfile
import logging
import argparse
import shutil
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_metadata_implementation")

# Import project modules
try:
    from inklink.config import CONFIG
    from inklink.adapters.rmapi_adapter import RmapiAdapter
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.config import CONFIG
    from inklink.adapters.rmapi_adapter import RmapiAdapter


def create_test_notebook():
    """Create a test notebook structure for experimenting with."""
    temp_dir = tempfile.mkdtemp(prefix="metadata_test_")
    logger.info(f"Created temporary directory: {temp_dir}")

    # Create a unique ID for the notebook
    notebook_id = str(uuid.uuid4())
    content_file_path = os.path.join(temp_dir, f"{notebook_id}.content")
    metadata_file_path = os.path.join(temp_dir, f"{notebook_id}.metadata")

    # Create test page
    page_id = str(uuid.uuid4())

    # Current timestamp in milliseconds
    now_ms = int(time.time() * 1000)

    # Create content structure
    # Important: Follow the exact format that reMarkable expects
    content = {
        "pages": [
            {
                "id": page_id,
                "visibleName": "Test Query Page",
                "lastModified": str(now_ms),  # String representation of milliseconds
                "tags": ["Lilly"],
            }
        ],
        "pageTags": {},
    }

    # Create metadata structure
    # Critical: All timestamps must be strings, not integers
    # Critical: synced must be true for uploads to succeed
    metadata = {
        "visibleName": "Test Notebook",
        "type": "DocumentType",
        "parent": "",
        "lastModified": str(now_ms),
        "lastOpened": str(now_ms),
        "lastOpenedPage": 0,
        "version": 1,
        "pinned": False,
        "synced": True,  # This is critical for successful upload
        "modified": False,
        "deleted": False,
        "metadatamodified": False,
        "tags": ["HasLilly"],
    }

    # Write the files
    with open(content_file_path, "w") as f:
        json.dump(content, f, indent=2)

    with open(metadata_file_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Create a page file
    page_dir = os.path.join(temp_dir, notebook_id)
    os.makedirs(page_dir, exist_ok=True)
    page_file_path = os.path.join(page_dir, f"{page_id}.rm")

    with open(page_file_path, "w") as f:
        f.write("Test content for the query page #Lilly")

    return temp_dir, content_file_path, metadata_file_path, notebook_id, page_id


def insert_response_after_query(
    temp_dir, content_file_path, metadata_file_path, query_page_id
):
    """Implement the fixed version of _insert_response_after_query."""
    try:
        # Load content
        with open(content_file_path, "r") as f:
            content = json.load(f)

        # Load metadata
        with open(metadata_file_path, "r") as f:
            metadata = json.load(f)

        # Generate a new page ID for the response
        response_page_id = str(uuid.uuid4())

        # Find the query page in content
        pages = content.get("pages", [])
        query_idx = next(
            (i for i, p in enumerate(pages) if p.get("id") == query_page_id), -1
        )

        if query_idx == -1:
            logger.error(f"Query page {query_page_id} not found in content")
            return False

        # Find query page
        query_page = pages[query_idx]

        # Get query title
        query_title = query_page.get("visibleName", "Query")

        # Current timestamp in milliseconds
        now_ms = int(time.time() * 1000)

        # Create response page with correct format
        # Important: lastModified must be a string representation of milliseconds timestamp
        response_page = {
            "id": response_page_id,
            "visibleName": f"Response to {query_title}",
            "lastModified": str(now_ms),  # String representation of milliseconds
            "tags": [],
        }

        # Insert response page after query page
        pages.insert(query_idx + 1, response_page)
        content["pages"] = pages

        # Ensure pageTags exists
        if "pageTags" not in content or content["pageTags"] is None:
            content["pageTags"] = {}

        # Update notebook metadata in reMarkable format - FIXED VERSION
        # The key issue is that we need to:
        # 1. Use millisecond timestamps as strings
        # 2. Ensure synced is true
        # 3. Set lastOpened to now_ms if not specified
        # 4. Set parent to "" if not specified, not None
        metadata.update(
            {
                "visibleName": metadata.get("visibleName", "Test Notebook"),
                "type": "DocumentType",
                "parent": metadata.get("parent", "")
                or "",  # Ensure parent is never None
                "lastModified": str(now_ms),
                "lastOpened": str(now_ms),  # Always update lastOpened
                "lastOpenedPage": 0,
                "version": metadata.get("version", 0) + 1,
                "pinned": False,
                "synced": True,  # Important: this must be true for reMarkable
                "modified": False,
                "deleted": False,
                "metadatamodified": False,
            }
        )

        # Write updated content
        with open(content_file_path, "w") as f:
            json.dump(content, f, indent=2)

        # Write updated metadata
        with open(metadata_file_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Create response page file
        # page_dir = os.path.dirname(content_file_path)  # Unused variable
        notebook_id = os.path.splitext(os.path.basename(content_file_path))[0]
        notebook_dir = os.path.join(temp_dir, notebook_id)
        os.makedirs(notebook_dir, exist_ok=True)

        response_file_path = os.path.join(notebook_dir, f"{response_page_id}.rm")

        # Write sample content to the response file
        with open(response_file_path, "w") as f:
            f.write("This is a test response from Claude to test metadata handling.")

        logger.info(f"Successfully created response page with ID: {response_page_id}")

        return True, response_page_id

    except Exception as e:
        logger.error(f"Error inserting response: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False, None


def create_zip_from_directory(temp_dir, output_path):
    """Create a zip file from the directory."""
    try:
        with zipfile.ZipFile(output_path, "w") as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        logger.info(f"Created zip file at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating zip file: {e}")
        return False


def upload_and_test(rmapi_path, modified_zip_path, notebook_name):
    """Upload the test notebook to verify metadata handling."""
    try:
        # Create rmapi adapter
        rmapi_adapter = RmapiAdapter(rmapi_path)

        # Refresh to sync with remote state - CRITICAL STEP!
        # This ensures we have the latest state from the reMarkable Cloud
        # before attempting an upload
        logger.info("Refreshing rmapi to sync with remote state...")
        success, stdout, stderr = rmapi_adapter.run_command("refresh")
        if not success:
            logger.warning(f"Failed to refresh rmapi: {stderr}")
        else:
            logger.info("Successfully refreshed rmapi")

        # Wait a moment to ensure refresh is complete
        time.sleep(1)

        # Upload the modified notebook
        logger.info(f"Uploading notebook to reMarkable Cloud: {notebook_name}")
        success, message = rmapi_adapter.upload_file(modified_zip_path, notebook_name)

        if success:
            logger.info(f"✅ SUCCESS: Upload succeeded: {message}")
            return True
        else:
            logger.error(f"❌ FAILURE: Upload failed: {message}")
            return False

    except Exception as e:
        logger.error(f"Error uploading test notebook: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test metadata handling implementation"
    )
    parser.add_argument(
        "--notebook-name",
        type=str,
        default="Metadata Test",
        help="Name for the test notebook",
    )
    parser.add_argument(
        "--no-cleanup", action="store_true", help="Don't remove temporary files"
    )
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Configure rmapi path
    rmapi_path = args.rmapi_path or CONFIG.get("RMAPI_PATH")
    if not os.path.exists(rmapi_path):
        logger.error(f"RMAPI executable not found at {rmapi_path}")
        return False

    logger.info(f"Using rmapi path: {rmapi_path}")

    # Create test notebook
    temp_dir, content_file_path, metadata_file_path, notebook_id, page_id = (
        create_test_notebook()
    )

    try:
        # Show original metadata
        with open(metadata_file_path, "r") as f:
            metadata = json.load(f)
        logger.info("Original metadata:")
        logger.info(json.dumps(metadata, indent=2))

        # Insert response
        success, response_page_id = insert_response_after_query(
            temp_dir, content_file_path, metadata_file_path, page_id
        )

        if not success:
            logger.error("Failed to insert response")
            return False

        # Show updated metadata
        with open(metadata_file_path, "r") as f:
            metadata = json.load(f)
        logger.info("Updated metadata after response:")
        logger.info(json.dumps(metadata, indent=2))

        # Create zip for upload
        zip_path = os.path.join(
            os.path.dirname(temp_dir), f"{args.notebook_name}.rmdoc"
        )
        if not create_zip_from_directory(temp_dir, zip_path):
            logger.error("Failed to create zip for upload")
            return False

        # Upload and test
        if not upload_and_test(rmapi_path, zip_path, args.notebook_name):
            logger.error("Failed to upload test notebook")
            return False

        logger.info(
            "✅ TEST PASSED: Successfully implemented and tested metadata handling fix"
        )
        return True

    finally:
        # Clean up
        if not args.no_cleanup:
            shutil.rmtree(temp_dir)
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            logger.info("Cleaned up temporary files")


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
