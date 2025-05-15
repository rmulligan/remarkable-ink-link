#!/usr/bin/env python3
"""Complete Live Test for Claude Penpal Service.

This script executes the full process:
1. Tags a notebook with Lilly
2. Waits for service to process it
3. Reports detailed results and errors
"""

import os
import sys
import time
import logging
import json
import tempfile
import uuid
import zipfile
import argparse
import shutil
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run_live_test")

# Import project modules
try:
    from inklink.config import CONFIG
    from inklink.adapters.rmapi_adapter import RmapiAdapter  # noqa: E402
    from inklink.services.claude_penpal_service import ClaudePenpalService  # noqa: E402
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.config import CONFIG  # noqa: E402
    from inklink.adapters.rmapi_adapter import RmapiAdapter  # noqa: E402
    from inklink.services.claude_penpal_service import ClaudePenpalService  # noqa: E402


class DebugClaudePenpalService(ClaudePenpalService):
    """Debug version that tracks method calls and overrides _process_with_claude."""

    def __init__(self, *args, **kwargs):
        # Extract verbose parameter before passing to parent
        self.verbose = kwargs.pop("verbose", False)
        super().__init__(*args, **kwargs)
        self.method_calls = []
        self.errors = []
        self.last_metadata = None

    def _process_with_claude(self, notebook_id, prompt, new_conversation=False):
        """Override to provide a quick test response."""
        self.method_calls.append(("_process_with_claude", notebook_id, len(prompt)))
        logger.info(f"Intercepted Claude call for notebook: {notebook_id}")
        return f"""Thank you for your query!

This is a test response from the live test runner.
The metadata fix should now work correctly with the following changes:

1. Using millisecond timestamps as strings
2. Setting synced=true for successful uploads
3. Adding rmapi refresh before upload
4. Ensuring all required metadata fields are present

Your original prompt was {len(prompt)} characters long.
"""

    def _insert_response_after_query(self, *args, **kwargs):
        """Track metadata before calling parent method."""
        try:
            # Extract metadata from args
            notebook_path = kwargs.get(
                "notebook_path", args[2] if len(args) > 2 else None
            )

            # Find and extract content
            if (
                notebook_path
                and os.path.exists(notebook_path)
                and zipfile.is_zipfile(notebook_path)
            ):
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Extract notebook
                    with zipfile.ZipFile(notebook_path, "r") as zip_ref:
                        zip_ref.extractall(temp_dir)

                    # Find metadata file
                    metadata_file_path = None
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith(".metadata"):
                                metadata_file_path = os.path.join(root, file)
                                break

                    if metadata_file_path and os.path.exists(metadata_file_path):
                        with open(metadata_file_path, "r") as f:
                            self.last_metadata = json.load(f)
                            if self.verbose:
                                logger.info(
                                    f"Original metadata: {json.dumps(self.last_metadata, indent=2)}"
                                )

            # Call parent method with detailed error catching
            try:
                result = super()._insert_response_after_query(*args, **kwargs)
                self.method_calls.append(("_insert_response_after_query", "SUCCESS"))
                return result
            except Exception as e:
                self.method_calls.append(
                    ("_insert_response_after_query", f"ERROR: {str(e)}")
                )
                self.errors.append(("_insert_response_after_query", str(e)))
                logger.error(f"Error in _insert_response_after_query: {e}")
                import traceback

                logger.error(traceback.format_exc())
                raise

        except Exception as outer_e:
            logger.error(f"Error in instrumentation wrapper: {outer_e}")
            import traceback

            logger.error(traceback.format_exc())
            return super()._insert_response_after_query(*args, **kwargs)


def tag_test_notebook(notebook_name, rmapi_adapter):
    """Tag a test notebook with HasLilly and Lilly for testing.

    Args:
        notebook_name: Name of notebook to tag
        rmapi_adapter: RmapiAdapter instance

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if notebook exists
        success, notebooks = rmapi_adapter.list_files()
        if not success:
            logger.error("Failed to list notebooks")
            return False

        target_notebook = None
        for notebook in notebooks:
            if notebook.get("VissibleName") == notebook_name:
                target_notebook = notebook
                break

        if not target_notebook:
            logger.error(f"Notebook not found: {notebook_name}")
            return False

        notebook_id = target_notebook.get("ID")
        logger.info(f"Found notebook: {notebook_name} (ID: {notebook_id})")

        # Create temporary directory for download and modification
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download the notebook
            download_path = os.path.join(temp_dir, f"{notebook_name}.rmdoc")
            success, message = rmapi_adapter.download_file(notebook_id, download_path)

            if not success:
                logger.error(f"Failed to download notebook: {message}")
                return False

            logger.info(f"Downloaded notebook to {download_path}")

            # Extract the notebook
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(download_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find or create content and metadata files
            content_file = None
            metadata_file = None

            for file in os.listdir(extract_dir):
                if file.endswith(".content"):
                    content_file = os.path.join(extract_dir, file)
                elif file.endswith(".metadata"):
                    metadata_file = os.path.join(extract_dir, file)

            # If no content file, create one
            if not content_file:
                # Generate a UUID for the notebook if needed
                if not metadata_file:
                    notebook_uuid = str(uuid.uuid4())
                else:
                    notebook_uuid = os.path.splitext(os.path.basename(metadata_file))[0]

                content_file = os.path.join(extract_dir, f"{notebook_uuid}.content")

                # Create basic content
                content = {"pages": [], "pageTags": {}}

                # If metadata file exists, load it, otherwise create it
                if metadata_file:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                else:
                    metadata_file = os.path.join(
                        extract_dir, f"{notebook_uuid}.metadata"
                    )
                    now_ms = str(int(time.time() * 1000))

                    # Create basic metadata
                    metadata = {
                        "visibleName": notebook_name,
                        "type": "DocumentType",
                        "parent": "",
                        "lastModified": now_ms,
                        "lastOpened": now_ms,
                        "lastOpenedPage": 0,
                        "version": 1,
                        "pinned": False,
                        "synced": True,
                        "modified": False,
                        "deleted": False,
                        "metadatamodified": False,
                    }
            else:
                # Load existing content
                with open(content_file, "r") as f:
                    content = json.load(f)

                # If metadata file doesn't exist, create it
                if not metadata_file:
                    notebook_uuid = os.path.splitext(os.path.basename(content_file))[0]
                    metadata_file = os.path.join(
                        extract_dir, f"{notebook_uuid}.metadata"
                    )
                    now_ms = str(int(time.time() * 1000))

                    # Create basic metadata
                    metadata = {
                        "visibleName": notebook_name,
                        "type": "DocumentType",
                        "parent": "",
                        "lastModified": now_ms,
                        "lastOpened": now_ms,
                        "lastOpenedPage": 0,
                        "version": 1,
                        "pinned": False,
                        "synced": True,
                        "modified": False,
                        "deleted": False,
                        "metadatamodified": False,
                    }
                else:
                    # Load existing metadata
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)

            # Add HasLilly tag to notebook metadata
            if "tags" not in metadata:
                metadata["tags"] = []

            if "HasLilly" not in metadata["tags"]:
                metadata["tags"].append("HasLilly")
                logger.info("Added HasLilly tag to notebook metadata")

            # Create a test page with Lilly tag if no pages exist
            pages = content.get("pages", [])
            if not pages:
                # Create a new page
                page_id = str(uuid.uuid4())
                now_ms = str(int(time.time() * 1000))

                test_page = {
                    "id": page_id,
                    "visibleName": "Test Query Page",
                    "lastModified": now_ms,
                    "tags": ["Lilly"],
                }

                pages.append(test_page)
                content["pages"] = pages

                # Create page directory and file
                notebook_uuid = os.path.splitext(os.path.basename(content_file))[0]
                page_dir = os.path.join(extract_dir, notebook_uuid)
                os.makedirs(page_dir, exist_ok=True)

                # Write test content
                with open(os.path.join(page_dir, f"{page_id}.rm"), "w") as f:
                    f.write("This is a test query for the Lilly assistant. #Lilly")

                logger.info(f"Created new test page with ID: {page_id}")
            else:
                # If pages exist, add Lilly tag to first page
                first_page = pages[0]
                if "tags" not in first_page:
                    first_page["tags"] = []

                if "Lilly" not in first_page["tags"]:
                    first_page["tags"].append("Lilly")
                    logger.info(
                        f"Added Lilly tag to existing page: {first_page.get('id')}"
                    )

            # Write updated content and metadata
            with open(content_file, "w") as f:
                json.dump(content, f, indent=2)

            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            # Create modified zip
            modified_path = os.path.join(temp_dir, f"{notebook_name}_modified.rmdoc")

            with zipfile.ZipFile(modified_path, "w") as zipf:
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, extract_dir)
                        zipf.write(file_path, arcname)

            # Upload the modified notebook
            logger.info("Refreshing rmapi before upload...")
            rmapi_adapter.run_command("refresh")

            logger.info(f"Uploading modified notebook: {notebook_name}")
            success, message = rmapi_adapter.upload_file(modified_path, notebook_name)

            if success:
                logger.info(f"Successfully tagged notebook: {notebook_name}")
                return True
            else:
                logger.error(f"Failed to upload modified notebook: {message}")
                return False

    except Exception as e:
        logger.error(f"Error tagging notebook: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point for live test."""
    parser = argparse.ArgumentParser(
        description="Complete live test for Claude Penpal Service"
    )
    parser.add_argument(
        "--notebook",
        type=str,
        default="Test_Claude_Penpal_Notebook",
        help="Notebook to use for testing",
    )
    parser.add_argument(
        "--tag", type=str, default="Lilly", help="Tag to use for query pages"
    )
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--skip-tagging", action="store_true", help="Skip notebook tagging step"
    )
    parser.add_argument(
        "--timeout", type=int, default=120, help="Maximum timeout in seconds"
    )
    parser.add_argument(
        "--poll-interval", type=int, default=5, help="Polling interval in seconds"
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
        return 1

    logger.info(f"Using rmapi path: {rmapi_path}")

    # Initialize rmapi adapter
    rmapi_adapter = RmapiAdapter(rmapi_path)

    # Verify connection
    if not rmapi_adapter.ping():
        logger.error("Failed to connect to reMarkable Cloud")
        return 1

    logger.info("Successfully connected to reMarkable Cloud")

    # Tag test notebook if needed
    if not args.skip_tagging:
        logger.info(f"Tagging notebook: {args.notebook}")
        if not tag_test_notebook(args.notebook, rmapi_adapter):
            logger.error("Failed to tag test notebook")
            return 1

        logger.info(
            f"Successfully tagged notebook {args.notebook} with HasLilly and Lilly tags"
        )
        # Wait a moment for tags to register
        time.sleep(5)
    else:
        logger.info("Skipping notebook tagging step")

    # Initialize debug service
    logger.info("Initializing debug Claude Penpal Service")
    service = DebugClaudePenpalService(
        rmapi_path=rmapi_path,
        query_tag=args.tag,
        pre_filter_tag="HasLilly",
        verbose=args.verbose,
    )

    # Process the notebook directly
    logger.info(f"Processing notebook: {args.notebook}")

    # Get notebook info
    success, notebooks = rmapi_adapter.list_files()
    if not success:
        logger.error("Failed to list notebooks")
        return 1

    target_notebook = None
    for notebook in notebooks:
        if notebook.get("VissibleName") == args.notebook:
            target_notebook = notebook
            break

    if not target_notebook:
        logger.error(f"Notebook not found: {args.notebook}")
        return 1

    # Process the notebook
    try:
        logger.info(f"Processing notebook: {args.notebook}")
        service._check_notebook_for_tagged_pages(target_notebook)

        # Check if processing succeeded based on method calls
        if not service.method_calls:
            logger.error("No methods were called, processing may have failed")
            return 1

        # Print method calls for debugging
        logger.info("Method calls during processing:")
        for method_name, *args in service.method_calls:
            logger.info(f"  - {method_name}: {args}")

        # Print any errors
        if service.errors:
            logger.error("Errors during processing:")
            for method_name, error in service.errors:
                logger.error(f"  - {method_name}: {error}")
            return 1

        logger.info("✅ Processing completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Error processing notebook: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
