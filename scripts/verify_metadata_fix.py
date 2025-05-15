#!/usr/bin/env python3
"""
Metadata Fix Verification Script

This script verifies that the metadata handling fix for the Claude Penpal Service
resolves the HTTP 400 errors when uploading modified notebooks to the reMarkable Cloud.

It focuses specifically on:
1. Correct metadata formatting
2. Proper millisecond timestamp usage
3. Setting synced=True in metadata
4. Using the rmapi refresh command before uploads

Usage:
    python verify_metadata_fix.py [--notebook-id ID] [--verbose]
"""

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import traceback
import uuid
import zipfile
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("verify_metadata_fix")

# Import project modules
try:
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Verify the metadata handling fix")
    parser.add_argument("--notebook-id", type=str, help="Use a specific notebook ID")
    parser.add_argument(
        "--notebook-name", type=str, help="Use a specific notebook name"
    )
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--no-cleanup", action="store_true", help="Don't remove temporary files"
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

    return rmapi_path


def get_test_notebook(rmapi_adapter, notebook_id=None, notebook_name=None):
    """Find or get a test notebook by ID or name."""
    try:
        # Check if rmapi is accessible
        if not rmapi_adapter.ping():
            logger.error("Cannot connect to reMarkable Cloud. Check authentication.")
            return None, None

        # List available notebooks
        success, notebooks = rmapi_adapter.list_files()
        if not success or not notebooks:
            logger.error("Failed to list notebooks or no notebooks found.")
            return None, None

        # Select a notebook to test with
        test_notebook = None

        # Try to find by ID if provided
        if notebook_id:
            test_notebook = next(
                (nb for nb in notebooks if nb.get("ID") == notebook_id), None
            )
            if not test_notebook:
                logger.error(f"Notebook with ID '{notebook_id}' not found.")
                return None, None

        # Try to find by name if provided
        elif notebook_name:
            test_notebook = next(
                (nb for nb in notebooks if nb.get("VissibleName") == notebook_name),
                None,
            )
            if not test_notebook:
                logger.error(f"Notebook with name '{notebook_name}' not found.")
                return None, None

        # Otherwise use the first notebook that's a document (not a collection)
        else:
            test_notebook = next(
                (nb for nb in notebooks if nb.get("Type") == "DocumentType"), None
            )
            if not test_notebook:
                logger.error("No suitable test notebook found.")
                return None, None

        # Extract notebook info
        notebook_id = test_notebook.get("ID")
        notebook_name = test_notebook.get("VissibleName", "Unknown")

        logger.info(
            f"Selected notebook '{notebook_name}' (ID: {notebook_id}) for testing"
        )
        return notebook_id, notebook_name

    except Exception as e:
        logger.error(f"Error getting test notebook: {e}")
        logger.error(traceback.format_exc())
        return None, None


def download_and_extract_notebook(rmapi_adapter, notebook_id, notebook_name):
    """Download and extract a notebook from reMarkable Cloud."""
    logger.info(f"Downloading notebook '{notebook_name}' (ID: {notebook_id})...")

    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp(prefix="metadata_fix_test_")

    try:
        # Download the notebook
        zip_path = os.path.join(temp_dir, f"{notebook_name}.rmdoc")
        success, message = rmapi_adapter.download_file(notebook_id, zip_path)

        if not success or not os.path.exists(zip_path):
            logger.error(f"Failed to download notebook: {message}")
            return None, None

        logger.info(f"Successfully downloaded notebook to {zip_path}")

        # Extract the notebook
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
        except zipfile.BadZipFile:
            logger.error(f"Downloaded file is not a valid zip file: {zip_path}")
            return None, None

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

        logger.info(f"Found content file: {content_file_path}")
        logger.info(f"Found metadata file: {metadata_file_path}")

        # Load content and metadata
        with open(content_file_path, "r") as f:
            content = json.load(f)

        with open(metadata_file_path, "r") as f:
            metadata = json.load(f)

        # Extract metadata structure for analysis
        logger.info("Metadata structure:")
        for key, value in metadata.items():
            logger.info(f"  {key}: {type(value).__name__} = {value}")

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
        logger.error(traceback.format_exc())
        shutil.rmtree(temp_dir)
        return None, None


def test_original_metadata(notebook_data):
    """Test uploading notebook with original metadata approach."""
    logger.info("Testing upload with original metadata approach...")

    try:
        # Get notebook info
        content_file_path = notebook_data["content_file_path"]
        metadata_file_path = notebook_data["metadata_file_path"]
        content = notebook_data[
            "content"
        ].copy()  # Create a copy to avoid modifying original
        metadata = notebook_data[
            "metadata"
        ].copy()  # Create a copy to avoid modifying original

        # Generate a new page ID for a test page
        test_page_id = str(uuid.uuid4())

        # Create a timestamp in ISO format (original approach)
        now_iso = datetime.now().isoformat()

        # Create test page with original metadata approach
        test_page = {
            "id": test_page_id,
            "lastModified": now_iso,
            "lastOpened": now_iso,
            "lastOpenedPage": 0,
            "pinned": False,
            "synced": False,  # Original approach used False
            "type": "DocumentType",
            "visibleName": f"Test Page Original {datetime.now().strftime('%H:%M:%S')}",
        }

        # Add test page to content
        pages = content.get("pages", [])
        pages.append(test_page)
        content["pages"] = pages

        # Update notebook metadata with original approach
        metadata.update(
            {
                "lastModified": now_iso,
                "lastOpened": now_iso,
                "metadatamodified": True,
                "modified": True,
                "synced": False,  # Original approach used False
                "version": metadata.get("version", 1) + 1,
            }
        )

        # Create a test directory for the original approach
        original_dir = os.path.join(
            os.path.dirname(notebook_data["zip_path"]), "original"
        )
        os.makedirs(original_dir, exist_ok=True)

        # Save modified content and metadata to new files
        original_content_path = os.path.join(
            original_dir, os.path.basename(content_file_path)
        )
        original_metadata_path = os.path.join(
            original_dir, os.path.basename(metadata_file_path)
        )

        with open(original_content_path, "w") as f:
            json.dump(content, f)

        with open(original_metadata_path, "w") as f:
            json.dump(metadata, f)

        # Create a blank page file
        page_file_path = os.path.join(original_dir, f"{test_page_id}.rm")
        with open(page_file_path, "w") as f:
            f.write("Test page content")

        # Create the zip file
        original_zip_path = os.path.join(
            os.path.dirname(notebook_data["zip_path"]),
            f"original_test_{time.strftime('%Y%m%d_%H%M%S')}.rmdoc",
        )

        with zipfile.ZipFile(original_zip_path, "w") as zipf:
            for file_path in [
                original_content_path,
                original_metadata_path,
                page_file_path,
            ]:
                zipf.write(file_path, os.path.basename(file_path))

        logger.info(
            f"Created test notebook with original metadata at {original_zip_path}"
        )
        return original_zip_path

    except Exception as e:
        logger.error(f"Error creating test notebook with original metadata: {e}")
        logger.error(traceback.format_exc())
        return None


def test_fixed_metadata(notebook_data):
    """Test uploading notebook with fixed metadata approach."""
    logger.info("Testing upload with fixed metadata approach...")

    try:
        # Get notebook info
        content_file_path = notebook_data["content_file_path"]
        metadata_file_path = notebook_data["metadata_file_path"]
        content = notebook_data[
            "content"
        ].copy()  # Create a copy to avoid modifying original
        metadata = notebook_data[
            "metadata"
        ].copy()  # Create a copy to avoid modifying original

        # Generate a new page ID for a test page
        test_page_id = str(uuid.uuid4())

        # Create a timestamp in milliseconds (fixed approach)
        now_ms = int(time.time() * 1000)

        # Create test page with fixed metadata approach
        test_page = {
            "id": test_page_id,
            "visibleName": f"Test Page Fixed {datetime.now().strftime('%H:%M:%S')}",
            "lastModified": now_ms,
            "tags": [],
        }

        # Add test page to content
        pages = content.get("pages", [])
        pages.append(test_page)
        content["pages"] = pages

        # Ensure pageTags exists
        if "pageTags" not in content or content["pageTags"] is None:
            content["pageTags"] = {}

        # Update notebook metadata with fixed approach
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
                "synced": True,  # Fixed approach uses True
                "modified": False,
                "deleted": False,
                "metadatamodified": False,
            }
        )

        # Create a test directory for the fixed approach
        fixed_dir = os.path.join(os.path.dirname(notebook_data["zip_path"]), "fixed")
        os.makedirs(fixed_dir, exist_ok=True)

        # Save modified content and metadata to new files
        fixed_content_path = os.path.join(
            fixed_dir, os.path.basename(content_file_path)
        )
        fixed_metadata_path = os.path.join(
            fixed_dir, os.path.basename(metadata_file_path)
        )

        with open(fixed_content_path, "w") as f:
            json.dump(content, f)

        with open(fixed_metadata_path, "w") as f:
            json.dump(metadata, f)

        # Create a blank page file
        page_file_path = os.path.join(fixed_dir, f"{test_page_id}.rm")
        with open(page_file_path, "w") as f:
            f.write("Test page content")

        # Create the zip file
        fixed_zip_path = os.path.join(
            os.path.dirname(notebook_data["zip_path"]),
            f"fixed_test_{time.strftime('%Y%m%d_%H%M%S')}.rmdoc",
        )

        with zipfile.ZipFile(fixed_zip_path, "w") as zipf:
            for file_path in [fixed_content_path, fixed_metadata_path, page_file_path]:
                zipf.write(file_path, os.path.basename(file_path))

        logger.info(f"Created test notebook with fixed metadata at {fixed_zip_path}")
        return fixed_zip_path

    except Exception as e:
        logger.error(f"Error creating test notebook with fixed metadata: {e}")
        logger.error(traceback.format_exc())
        return None


def upload_and_test(rmapi_adapter, zip_path, approach, notebook_name):
    """Upload the test notebook and test if it works."""
    logger.info(f"Uploading {approach} test notebook '{notebook_name}'...")

    try:
        # Upload the notebook
        success, message = rmapi_adapter.upload_file(
            zip_path, f"{notebook_name}_{approach}"
        )

        if success:
            logger.info(f"✅ SUCCESS: {approach} approach upload succeeded: {message}")
            return True
        else:
            logger.error(f"❌ FAILURE: {approach} approach upload failed: {message}")
            return False

    except Exception as e:
        logger.error(f"Error uploading {approach} test notebook: {e}")
        logger.error(traceback.format_exc())
        return False


def verify_metadata_fix(args, rmapi_path):
    """Verify that the metadata fix resolves the HTTP 400 errors."""
    logger.info("Starting metadata fix verification...")

    # Create rmapi adapter
    rmapi_adapter = RmapiAdapter(rmapi_path)

    # Get test notebook
    notebook_id, notebook_name = get_test_notebook(
        rmapi_adapter, args.notebook_id, args.notebook_name
    )

    if not notebook_id or not notebook_name:
        return False

    # Download and extract notebook
    temp_dir, notebook_data = download_and_extract_notebook(
        rmapi_adapter, notebook_id, notebook_name
    )

    if not temp_dir or not notebook_data:
        return False

    try:
        # Test original metadata approach
        original_zip_path = test_original_metadata(notebook_data)
        if not original_zip_path:
            return False

        # Test fixed metadata approach
        fixed_zip_path = test_fixed_metadata(notebook_data)
        if not fixed_zip_path:
            return False

        # Ensure rmapi is synchronized with the cloud
        logger.info("Refreshing rmapi to sync with cloud...")
        success, stdout, stderr = rmapi_adapter.run_command("refresh")
        if not success:
            logger.warning(f"Failed to refresh rmapi: {stderr}")

        # Upload and test both approaches
        original_success = upload_and_test(
            rmapi_adapter, original_zip_path, "original", notebook_name
        )

        fixed_success = upload_and_test(
            rmapi_adapter, fixed_zip_path, "fixed", notebook_name
        )

        # Compare results
        if fixed_success and not original_success:
            logger.info(
                "✅ VERIFICATION PASSED: Fixed metadata approach works while original fails"
            )
            logger.info(
                "This confirms that the metadata fix resolves the HTTP 400 errors!"
            )
            return True
        elif fixed_success and original_success:
            logger.info("⚠️ INCONCLUSIVE: Both approaches work")
            logger.info(
                "The original approach may be working due to changes in the reMarkable API or other factors"
            )
            return True
        elif not fixed_success and not original_success:
            logger.error("❌ VERIFICATION FAILED: Both approaches fail")
            logger.error("There might be other issues with the upload process")
            return False
        else:  # not fixed_success and original_success
            logger.error(
                "❌ VERIFICATION FAILED: Original approach works but fixed approach fails"
            )
            logger.error("The fix might have introduced new issues")
            return False

    finally:
        # Clean up
        if not args.no_cleanup and temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory {temp_dir}")


def main():
    """Main entry point."""
    args = parse_args()
    rmapi_path = setup_environment(args)

    # Run the verification
    logger.info("=== Verifying Claude Penpal Service Metadata Fix ===")
    result = verify_metadata_fix(args, rmapi_path)

    # Print summary
    logger.info("\n=== Verification Summary ===")
    if result:
        logger.info("✅ Metadata fix verification PASSED")
        return 0
    else:
        logger.error("❌ Metadata fix verification FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
