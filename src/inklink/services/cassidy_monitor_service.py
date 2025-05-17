"""Cassidy Monitor Service for InkLink.

This module provides a service that monitors reMarkable Cloud for notebooks
tagged with 'Cass' and processes them with Claude Code.
"""

import json
import logging
import os
import shutil
import tempfile
import threading
import time
import zipfile
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from inklink.adapters.cassidy_adapter import CassidyAdapter
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class CassidyMonitor:
    """Service that monitors reMarkable Cloud for notebooks tagged with 'Cass'."""

    def __init__(
        self,
        adapter: Optional[CassidyAdapter] = None,
        rmapi_path: str = None,
        polling_interval: int = 60,
        output_dir: str = None,
        tag: str = "Cass",
        callback: Optional[Callable] = None,
    ):
        """
        Initialize the monitoring service.

        Args:
            adapter: CassidyAdapter instance (optional)
            rmapi_path: Path to rmapi executable
            polling_interval: Time between polls in seconds
            output_dir: Directory to store downloaded notebooks and images
            tag: Tag to search for
            callback: Function to call when a tagged notebook is found
        """
        self.rmapi_path = (
            rmapi_path or os.environ.get("RMAPI_PATH") or CONFIG.get("RMAPI_PATH")
        )
        self.adapter = adapter or CassidyAdapter(self.rmapi_path, tag)
        self.polling_interval = polling_interval
        self.output_dir = output_dir or os.path.join(
            CONFIG.get("TEMP_DIR", "/tmp"), "cassidy_monitor"
        )
        self.tag = tag
        self.callback = callback

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # State tracking
        self.running = False
        self.last_check_time = time.time()
        self.known_notebooks: Dict[str, Dict[str, Any]] = {}  # ID -> metadata
        self.monitoring_thread = None

        # Timestamps file for persistent tracking
        self.timestamps_file = os.path.join(self.output_dir, "notebook_timestamps.json")
        self._load_timestamps()

    def _load_timestamps(self):
        """Load notebook timestamps from file, if it exists."""
        if os.path.exists(self.timestamps_file):
            try:
                with open(self.timestamps_file, "r") as f:
                    self.known_notebooks = json.load(f)
                logger.info(
                    f"Loaded {len(self.known_notebooks)} notebook timestamps from file"
                )
            except Exception as e:
                logger.error(f"Failed to load timestamps file: {e}")
                self.known_notebooks = {}

    def _save_timestamps(self):
        """Save notebook timestamps to file."""
        try:
            with open(self.timestamps_file, "w") as f:
                json.dump(self.known_notebooks, f)
        except Exception as e:
            logger.error(f"Failed to save timestamps file: {e}")

    def start(self):
        """Start the monitoring service in a background thread."""
        if self.running:
            logger.warning("Monitoring service already running")
            return

        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitoring_thread.start()
        logger.info(f"Started monitoring for notebooks tagged with '{self.tag}'")

    def stop(self):
        """Stop the monitoring service."""
        if not self.running:
            logger.warning("Monitoring service not running")
            return

        self.running = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
        logger.info("Stopped monitoring service")
        self._save_timestamps()

    def _monitoring_loop(self):
        """Background loop for monitoring notebooks."""
        while self.running:
            try:
                # Check for tagged notebooks
                self._check_for_tagged_notebooks()

                # Sleep until next check
                for _ in range(int(self.polling_interval)):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                # Sleep before retry on error
                time.sleep(10)

    def _check_for_tagged_notebooks(self):
        """Check for notebooks tagged with 'Cass' at notebook or page level."""
        try:
            # Find all tagged notebooks
            tagged_notebooks = self.find_tagged_documents(self.tag)

            if tagged_notebooks:
                logger.info(
                    f"Found {len(tagged_notebooks)} documents with tag '{self.tag}'"
                )

                # Process each tagged notebook
                for doc in tagged_notebooks:
                    self._process_tagged_document(doc)

                # Save timestamps after processing
                self._save_timestamps()
            else:
                logger.info(f"No documents found with tag '{self.tag}'")

        except Exception as e:
            logger.error(f"Error checking for tagged notebooks: {e}")
            import traceback

            logger.error(traceback.format_exc())

    def find_tagged_documents(self, tag: str = "Cass") -> List[Dict[str, Any]]:
        """
        Find all documents that have a specific tag (notebook or page level).

        Args:
            tag: Tag to check for

        Returns:
            List of dictionaries with document info
        """
        tagged_docs = []

        # Get all documents from rmapi
        success, stdout, stderr = self.adapter.run_command("ls", "-l")
        if not success:
            logger.error(f"Failed to list documents: {stderr}")
            return []

        try:
            # Process the text output to get document names
            documents = []
            for line in stdout.split("\n"):
                line = line.strip()
                if line and line.startswith("[f]"):
                    # Extract document name
                    doc_name = line[3:].strip()

                    # Skip empty or "Unnamed" documents
                    if doc_name and doc_name != "Unnamed":
                        documents.append(doc_name)
                    else:
                        logger.info(f"Skipping empty or unnamed document: '{doc_name}'")

            logger.info(f"Found {len(documents)} documents to check for tags")

            # Process each document by name
            for doc_name in documents:
                try:
                    logger.info(f"Checking document: {doc_name}")

                    # Get document ID with stat command
                    success, stdout, stderr = self.adapter.run_command("stat", doc_name)
                    if not success:
                        logger.error(f"Failed to get metadata for {doc_name}: {stderr}")
                        continue

                    metadata = json.loads(stdout)
                    doc_id = metadata.get("ID")

                    if not doc_id:
                        logger.error(f"Could not find ID for {doc_name}")
                        continue

                    # Check for the tag at notebook level
                    has_notebook_tag, notebook_content = self._check_document_for_tag(
                        doc_name, tag
                    )

                    # Check for the tag at page level
                    tagged_pages = self._check_document_for_page_tags(
                        doc_name, tag, notebook_content
                    )

                    # Update known notebooks
                    self.known_notebooks[doc_id] = metadata

                    # If the document has tags at either level, add it to the result
                    if has_notebook_tag or tagged_pages:
                        tagged_docs.append(
                            {
                                "id": doc_id,
                                "name": doc_name,
                                "metadata": metadata,
                                "has_notebook_tag": has_notebook_tag,
                                "tagged_pages": tagged_pages,
                                "content": notebook_content,
                            }
                        )
                except Exception as e:
                    logger.error(f"Error processing document {doc_name}: {e}")
                    import traceback

                    logger.error(traceback.format_exc())

            return tagged_docs

        except Exception as e:
            logger.error(f"Error finding tagged notebooks: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return []

    def _check_document_for_tag(
        self, doc_name: str, tag: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a document has the specified tag at notebook level.

        Args:
            doc_name: Document name
            tag: Tag to search for

        Returns:
            Tuple of (has_tag, content_data)
        """
        # Create a temporary directory for the document
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary subdirectory for downloading
            # rmapi puts files in the current directory
            current_dir = os.getcwd()
            try:
                # Change to temp dir for download
                os.chdir(temp_dir)

                # First download the document by name to current directory
                expected_file = f"{doc_name}.rmdoc"
                logger.info(
                    f"Downloading {doc_name} to {os.path.join(temp_dir, expected_file)}"
                )
                success, stdout, stderr = self.adapter.run_command("get", doc_name, ".")
                if not success:
                    logger.error(f"Failed to download {doc_name}: {stderr}")
                    return False, {}

                # Verify file was downloaded
                if not os.path.exists(expected_file):
                    logger.error(
                        f"Download reported success but file not found at {expected_file}"
                    )

                    # Try to find any .rmdoc files in the temp directory
                    rmdoc_files = [f for f in os.listdir(".") if f.endswith(".rmdoc")]
                    if rmdoc_files:
                        logger.info(
                            f"Found alternative downloaded file: {rmdoc_files[0]}"
                        )
                        expected_file = rmdoc_files[0]
                    else:
                        logger.error("No .rmdoc files found in temp directory")
                        return False, {}

                # Set zip_path to the actual downloaded file
                zip_path = os.path.join(temp_dir, expected_file)
                logger.info(f"Found downloaded file at {zip_path}")

                # Extract and check for the tag
                content_data = {}
                try:
                    # See if there's a content file
                    with zipfile.ZipFile(zip_path, "r") as zipf:
                        content_files = [
                            f for f in zipf.namelist() if f.endswith(".content")
                        ]

                        if not content_files:
                            logger.warning(f"No content file found in {doc_name}")
                            return False, {}

                        # Extract and check the first content file
                        content_file = content_files[0]
                        zipf.extract(content_file, temp_dir)

                        # Read the content file
                        content_path = os.path.join(temp_dir, content_file)
                        with open(content_path, "r") as f:
                            content_data = json.load(f)

                        # Check for tags
                        tags = content_data.get("tags", [])
                        logger.info(f"Document {doc_name} has notebook tags: {tags}")

                        # Write all tags to a log file for debugging
                        try:
                            with open(
                                "/home/ryan/Cassidy/all_tags.txt", "a"
                            ) as log_file:
                                log_file.write(
                                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Document '{doc_name}' has notebook tags: {tags}\n"
                                )
                        except Exception as e:
                            logger.error(f"Error writing to log file: {e}")

                        if tag in tags:
                            logger.info(
                                f"Document '{doc_name}' has notebook tag '{tag}'"
                            )
                            # Write to special log file
                            try:
                                with open(
                                    "/home/ryan/Cassidy/tagged_docs.txt", "a"
                                ) as log_file:
                                    log_file.write(
                                        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Found document '{doc_name}' with notebook tag '{tag}'\n"
                                    )
                            except Exception:
                                pass
                            return True, content_data

                        # If we're looking for tag 'Cass' but it's not in tags, check case variations
                        if tag.lower() == "cass":
                            for t in tags:
                                if t.lower() == "cass":
                                    logger.info(
                                        f"Document '{doc_name}' has tag with case variation: {t}"
                                    )
                                    try:
                                        with open(
                                            "/home/ryan/Cassidy/case_issues.txt", "a"
                                        ) as log_file:
                                            log_file.write(
                                                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Document '{doc_name}' has tag '{t}' instead of '{tag}'\n"
                                            )
                                    except Exception:
                                        pass
                                    return (
                                        True,
                                        content_data,
                                    )  # Return true for case-insensitive matches too

                        return False, content_data

                except Exception as e:
                    logger.error(f"Error checking {doc_name} for tag: {e}")
                    import traceback

                    logger.error(traceback.format_exc())
                    return False, {}

            finally:
                # Change back to original directory
                os.chdir(current_dir)

    @staticmethod
    def _check_document_for_page_tags(
        doc_name: str, tag: str, content_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check if a document has pages with the specified tag.

        Args:
            doc_name: Document name
            tag: Tag to search for
            content_data: Content data dictionary from the document

        Returns:
            List of dictionaries with page info
        """
        tagged_pages = []

        # If we don't have content data, return empty list
        if not content_data:
            return []

        # Check for pageTags section
        page_tags = content_data.get("pageTags", [])
        if page_tags is None:
            page_tags = []

        # Get page IDs that have the tag
        tagged_page_ids = []
        for page_tag in page_tags:
            # Case-sensitive check
            if page_tag.get("tag") == tag:
                tagged_page_ids.append(page_tag.get("pageId"))
            # Case-insensitive check
            elif page_tag.get("tag", "").lower() == tag.lower():
                tagged_page_ids.append(page_tag.get("pageId"))

        # If no tagged pages, return empty list
        if not tagged_page_ids:
            return []

        # Get page information for tagged pages
        if "pages" in content_data.get("cPages", {}):
            for i, page in enumerate(content_data["cPages"]["pages"]):
                page_id = page.get("id")
                if page_id in tagged_page_ids:
                    page_info = {
                        "index": i,
                        "id": page_id,
                        "template": page.get("template", {}).get("value", "Unknown"),
                    }
                    tagged_pages.append(page_info)
                    logger.info(
                        f"Document '{doc_name}' has page {i} (ID: {page_id}) with tag '{tag}'"
                    )

                    # Write to special log file
                    try:
                        with open(
                            "/home/ryan/Cassidy/tagged_pages.txt", "a"
                        ) as log_file:
                            log_file.write(
                                f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Found page {i} (ID: {page_id}) in document '{doc_name}' with tag '{tag}'\n"
                            )
                    except Exception:
                        pass

        return tagged_pages

    def _process_tagged_document(self, doc: Dict[str, Any]):
        """
        Process a document that has been tagged with 'Cass'.

        Args:
            doc: Document data including ID, name, metadata and tag info
        """
        doc_id = doc.get("id")
        doc_name = doc.get("name")

        if not doc_id or not doc_name:
            logger.error("Missing document ID or name")
            return

        logger.info(f"Processing tagged document: {doc_name} ({doc_id})")

        # Write to special log file
        try:
            with open("/home/ryan/Cassidy/processing_documents.txt", "a") as log_file:
                log_file.write(
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Processing tagged document: {doc_name} ({doc_id})\n"
                )
        except Exception:
            pass

        # Create directory for this document if it doesn't exist
        document_dir = os.path.join(self.output_dir, doc_id)
        os.makedirs(document_dir, exist_ok=True)

        # If document has notebook tag, process the whole notebook
        if doc.get("has_notebook_tag", False):
            self._process_notebook(doc)

        # Process each tagged page
        tagged_pages = doc.get("tagged_pages", [])
        for page in tagged_pages:
            self._process_page(doc, page)

    def _process_notebook(self, doc: Dict[str, Any]):
        """
        Process a notebook that has the Cass tag at notebook level.

        Args:
            doc: Document data including ID, name, metadata and tag info
        """
        doc_id = doc.get("id")
        doc_name = doc.get("name")

        logger.info(f"Processing notebook: {doc_name} ({doc_id})")

        # Create directory for this notebook if it doesn't exist
        notebook_dir = os.path.join(self.output_dir, doc_id)
        os.makedirs(notebook_dir, exist_ok=True)

        # Download and extract the notebook
        success, extract_dir = self.adapter.download_notebook(doc_name, notebook_dir)
        if not success:
            logger.error(
                f"Failed to download and extract notebook {doc_name}: {extract_dir}"
            )
            return

        # Convert pages to PNG
        success, png_paths = self.adapter.convert_notebook_pages_to_png(
            doc_id, notebook_dir
        )
        if not success:
            logger.error(f"Failed to convert notebook {doc_name} to PNG: {png_paths}")
            return

        logger.info(f"Converted {len(png_paths)} pages of {doc_name} to PNG")

        # If we have a callback, call it with the notebook info
        if self.callback:
            notebook_info = {
                "id": doc_id,
                "name": doc_name,
                "metadata": doc.get("metadata", {}),
                "png_paths": png_paths,
                "notebook_dir": notebook_dir,
                "type": "notebook",
            }
            self.callback(notebook_info)

        # After processing, remove the tag (optional, depends on workflow)
        # For now, we'll keep the tag so the notebook remains in the list
        # success, message = self.adapter.remove_tag_from_notebook(doc_id, self.tag)
        # if not success:
        #     logger.error(f"Failed to remove tag from {doc_name}: {message}")

    def _process_page(self, doc: Dict[str, Any], page: Dict[str, Any]):
        """
        Process a single page that has the Cass tag.

        Args:
            doc: Document data including ID, name, metadata and tag info
            page: Page data including ID, index, and template
        """
        doc_id = doc.get("id")
        doc_name = doc.get("name")
        page_id = page.get("id")
        page_index = page.get("index")

        logger.info(
            f"Processing page {page_index} (ID: {page_id}) in document {doc_name} ({doc_id})"
        )

        # Create directory for this page if it doesn't exist
        page_dir = os.path.join(self.output_dir, doc_id, page_id)
        os.makedirs(page_dir, exist_ok=True)

        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary subdirectory for downloading
            current_dir = os.getcwd()
            try:
                # Change to temp dir for download
                os.chdir(temp_dir)

                # Download the document
                expected_file = f"{doc_name}.rmdoc"
                logger.info(
                    f"Downloading {doc_name} to {os.path.join(temp_dir, expected_file)}"
                )
                success, stdout, stderr = self.adapter.run_command("get", doc_name, ".")
                if not success:
                    logger.error(f"Failed to download {doc_name}: {stderr}")
                    return

                # Verify file was downloaded
                if not os.path.exists(expected_file):
                    logger.error(
                        f"Download reported success but file not found at {expected_file}"
                    )

                    # Try to find any .rmdoc files in the temp directory
                    rmdoc_files = [f for f in os.listdir(".") if f.endswith(".rmdoc")]
                    if rmdoc_files:
                        logger.info(
                            f"Found alternative downloaded file: {rmdoc_files[0]}"
                        )
                        expected_file = rmdoc_files[0]
                    else:
                        logger.error("No .rmdoc files found in temp directory")
                        return

                # Set zip_path to the actual downloaded file
                zip_path = os.path.join(temp_dir, expected_file)
                logger.info(f"Found downloaded file at {zip_path}")

                # Extract the specific page
                with zipfile.ZipFile(zip_path, "r") as zipf:
                    # Look for .rm file with the page ID
                    rm_paths = [
                        f for f in zipf.namelist() if f.endswith(".rm") and page_id in f
                    ]

                    if not rm_paths:
                        logger.error(f"No .rm file found for page ID {page_id}")
                        return

                    # Extract the .rm file
                    rm_path = rm_paths[0]
                    zipf.extract(rm_path, temp_dir)

                    # Get path to the extracted file
                    extracted_rm_path = os.path.join(temp_dir, rm_path)
                    logger.info(f"Extracted page file to {extracted_rm_path}")

                    # Copy the file to the page directory
                    shutil.copy(extracted_rm_path, page_dir)

                    # Convert the page to PNG
                    rm_file_name = os.path.basename(rm_path)
                    success, result = self.adapter.convert_rm_to_png(
                        extracted_rm_path, page_dir
                    )

                    if not success:
                        logger.error(f"Failed to convert page to PNG: {result}")
                        return

                    logger.info(f"Converted page to PNG: {result}")

                    # If we have a callback, call it with the page info
                    if self.callback:
                        page_info = {
                            "doc_id": doc_id,
                            "doc_name": doc_name,
                            "page_id": page_id,
                            "page_index": page_index,
                            "rm_path": os.path.join(page_dir, rm_file_name),
                            "png_path": result,
                            "type": "page",
                        }
                        self.callback(page_info)

                    # After processing, remove the tag (optional)
                    # success, message = self.adapter.remove_tag_from_page(doc_id, page_id, self.tag)
                    # if not success:
                    #     logger.error(f"Failed to remove tag from page {page_id}: {message}")

            finally:
                # Change back to original directory
                os.chdir(current_dir)

    def check_now(self) -> List[Dict[str, Any]]:
        """
        Immediately check for tagged notebooks.

        Returns:
            List of processed notebooks
        """
        processed_notebooks = []

        # Define a callback to collect processed notebooks
        def collect_notebook(notebook_info):
            processed_notebooks.append(notebook_info)

        # Save the original callback and replace it
        original_callback = self.callback
        self.callback = collect_notebook

        # Perform the check
        self._check_for_tagged_notebooks()

        # Restore the original callback
        self.callback = original_callback

        return processed_notebooks
