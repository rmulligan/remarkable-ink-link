#!/usr/bin/env python3
"""
Fix for the Claude Penpal Service.

This script patches the ClaudePenpalService to correctly handle metadata
for reMarkable notebooks, fixing the issues with uploading modified notebooks.
"""
import logging
import shutil
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# File paths
FILE_PATH = (
    "/home/ryan/dev/remarkable-ink-link/src/inklink/services/claude_penpal_service.py"
)
BACKUP_PATH = "/home/ryan/dev/remarkable-ink-link/src/inklink/services/claude_penpal_service.py.backup"

# The function to replace
OLD_FUNCTION = """    def _insert_response_after_query(
        self,
        notebook_id,
        notebook_name,
        notebook_path,
        notebook_dir,
        query_page,
        response_text,
        all_pages
    ):
        \"\"\"Insert response page after query page in notebook.

        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook
            notebook_path: Path to downloaded notebook
            notebook_dir: Directory for notebook files
            query_page: Query page data
            response_text: Response text to insert
            all_pages: List of all pages in the notebook
        \"\"\"
        try:
            import zipfile

            # Create temporary directory for modified notebook
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract notebook
                with zipfile.ZipFile(notebook_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Find content file
                content_file_path = None
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.content'):
                            content_file_path = os.path.join(root, file)
                            break

                if not content_file_path:
                    logger.error(f"No content file found in notebook {notebook_path}")
                    return

                # Load content
                with open(content_file_path, 'r') as f:
                    content = json.load(f)

                # Find and load metadata file
                metadata_file_path = None
                content_id = os.path.splitext(os.path.basename(content_file_path))[0]
                metadata_file_path = os.path.join(os.path.dirname(content_file_path), f"{content_id}.metadata")

                metadata = {}
                if os.path.exists(metadata_file_path):
                    try:
                        with open(metadata_file_path, 'r') as f:
                            metadata = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse metadata file: {metadata_file_path}")

                # Generate a new page ID
                response_page_id = str(uuid.uuid4())

                # Find position of query page
                pages = content.get("pages", [])
                query_idx = next((i for i, p in enumerate(pages) if p.get("id") == query_page["id"]), -1)

                if query_idx == -1:
                    logger.error(f"Query page {query_page['id']} not found in notebook content")
                    return

                # Create response page metadata
                query_title = query_page.get("metadata", {}).get("visibleName", "Query")
                if not query_title or query_title == "Query":
                    query_title = query_page.get("visibleName", "Query")

                now = datetime.now().isoformat()
                response_page = {
                    "id": response_page_id,
                    "lastModified": now,
                    "lastOpened": now,
                    "lastOpenedPage": 0,
                    "pinned": False,
                    "synced": False,
                    "type": "DocumentType",
                    "visibleName": f"Response to {query_title}"
                }

                # Insert response page after query page
                pages.insert(query_idx + 1, response_page)
                content["pages"] = pages

                # Update notebook metadata
                metadata.update({
                    "lastModified": now,
                    "lastOpened": now,
                    "metadatamodified": True,
                    "modified": True,
                    "synced": False,
                    "version": metadata.get("version", 1) + 1
                })

                # Write updated content
                with open(content_file_path, 'w') as f:
                    json.dump(content, f)

                # Write updated metadata
                with open(metadata_file_path, 'w') as f:
                    json.dump(metadata, f)"""

# The fixed function
NEW_FUNCTION = """    def _insert_response_after_query(
        self,
        notebook_id,
        notebook_name,
        notebook_path,
        notebook_dir,
        query_page,
        response_text,
        all_pages
    ):
        \"\"\"Insert response page after query page in notebook.

        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook
            notebook_path: Path to downloaded notebook
            notebook_dir: Directory for notebook files
            query_page: Query page data
            response_text: Response text to insert
            all_pages: List of all pages in the notebook
        \"\"\"
        try:
            import zipfile

            # Create temporary directory for modified notebook
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract notebook
                with zipfile.ZipFile(notebook_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Find content file
                content_file_path = None
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.content'):
                            content_file_path = os.path.join(root, file)
                            break

                if not content_file_path:
                    logger.error(f"No content file found in notebook {notebook_path}")
                    return

                # Load content
                with open(content_file_path, 'r') as f:
                    content = json.load(f)

                # Find and load metadata file
                metadata_file_path = None
                content_id = os.path.splitext(os.path.basename(content_file_path))[0]
                metadata_file_path = os.path.join(os.path.dirname(content_file_path), f"{content_id}.metadata")

                metadata = {}
                if os.path.exists(metadata_file_path):
                    try:
                        with open(metadata_file_path, 'r') as f:
                            metadata = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse metadata file: {metadata_file_path}")

                # Generate a new page ID
                response_page_id = str(uuid.uuid4())

                # Find position of query page
                pages = content.get("pages", [])
                query_idx = next((i for i, p in enumerate(pages) if p.get("id") == query_page["id"]), -1)

                if query_idx == -1:
                    logger.error(f"Query page {query_page['id']} not found in notebook content")
                    return

                # Create response page metadata
                query_title = query_page.get("metadata", {}).get("visibleName", "Query")
                if not query_title or query_title == "Query":
                    query_title = query_page.get("visibleName", "Query")

                # Current timestamp in milliseconds (reMarkable format)
                now_ms = int(time.time() * 1000)

                # Format for reMarkable metadata
                response_page = {
                    "id": response_page_id,
                    "visibleName": f"Response to {query_title}",
                    "lastModified": now_ms,
                    "tags": []
                }

                # Insert response page after query page
                pages.insert(query_idx + 1, response_page)
                content["pages"] = pages

                # Update content file with proper structure
                if "pageTags" not in content or content["pageTags"] is None:
                    content["pageTags"] = {}

                # Update notebook metadata in reMarkable format
                metadata.update({
                    "visibleName": notebook_name,
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
                    "metadatamodified": False
                })

                # Write updated content
                with open(content_file_path, 'w') as f:
                    json.dump(content, f)

                # Write updated metadata
                with open(metadata_file_path, 'w') as f:
                    json.dump(metadata, f)"""


def backup_file():
    """Create a backup of the original file."""
    shutil.copy2(FILE_PATH, BACKUP_PATH)
    logger.info(f"Created backup at {BACKUP_PATH}")


def update_file():
    """Update the file with the fixed function."""
    with open(FILE_PATH, "r") as f:
        content = f.read()

    # Replace the function
    new_content = content.replace(OLD_FUNCTION, NEW_FUNCTION)

    # Write updated content
    with open(FILE_PATH, "w") as f:
        f.write(new_content)

    logger.info(f"Updated {FILE_PATH} with fixed metadata handling")


def add_refresh_to_rmapi_adapter():
    """Add refresh command to rmapi_adapter.py."""
    adapter_path = (
        "/home/ryan/dev/remarkable-ink-link/src/inklink/adapters/rmapi_adapter.py"
    )

    # Look for upload_file method
    with open(adapter_path, "r") as f:
        content = f.read()

    # Add refresh before upload
    if (
        "def upload_file" in content
        and "# First use 'put' to upload the file" in content
    ):
        # Replace the upload_file method to include refresh
        old_upload = """    def upload_file(self, file_path: str, title: str) -> Tuple[bool, str]:
        \"\"\"
        Upload a file to reMarkable Cloud.

        Args:
            file_path: Path to the file to upload
            title: Title for the document in reMarkable

        Returns:
            Tuple of (success, message)
        \"\"\"
        if not self._validate_executable():
            return False, "rmapi path not valid"

        # First use 'put' to upload the file
        success, stdout, stderr = self.run_command("put", file_path)"""

        new_upload = """    def upload_file(self, file_path: str, title: str) -> Tuple[bool, str]:
        \"\"\"
        Upload a file to reMarkable Cloud.

        Args:
            file_path: Path to the file to upload
            title: Title for the document in reMarkable

        Returns:
            Tuple of (success, message)
        \"\"\"
        if not self._validate_executable():
            return False, "rmapi path not valid"

        # Refresh to sync with remote changes
        success, stdout, stderr = self.run_command("refresh")
        if not success:
            logger.warning(f"Failed to refresh rmapi: {stderr}")

        logger.info("Refreshed rmapi before upload")

        # First use 'put' to upload the file
        success, stdout, stderr = self.run_command("put", file_path)"""

        updated_content = content.replace(old_upload, new_upload)

        with open(adapter_path, "w") as f:
            f.write(updated_content)

        logger.info(f"Added refresh command to {adapter_path}")
    else:
        logger.warning(f"Could not find upload_file method in {adapter_path}")


def main():
    """Main entry point."""
    try:
        # Create backup
        backup_file()

        # Update the file
        update_file()

        # Add refresh to rmapi_adapter
        add_refresh_to_rmapi_adapter()

        logger.info("Successfully applied fixes to Claude Penpal service")
        return 0
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
