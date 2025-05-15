"""Lilly Monitor Service for InkLink.

This module provides a service that monitors reMarkable Cloud for notebooks
tagged with 'Lilly' and processes them with Claude Code using Claude's vision capabilities.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from inklink.adapters.cassidy_adapter import CassidyAdapter
from inklink.config import CONFIG
from inklink.services.cassidy_monitor_service import CassidyMonitor

logger = logging.getLogger(__name__)


class LillyMonitor(CassidyMonitor):
    """Service that monitors reMarkable Cloud for notebooks tagged with 'Lilly'."""

    def __init__(
        self,
        adapter: Optional[CassidyAdapter] = None,
        rmapi_path: str = None,
        polling_interval: int = 60,
        output_dir: str = None,
        tag: str = "Lilly",
        callback: Optional[Callable] = None,
        claude_command: str = "claude",
        lilly_workspace: str = None,
    ):
        """
        Initialize the Lilly monitoring service.

        Args:
            adapter: CassidyAdapter instance (optional)
            rmapi_path: Path to rmapi executable
            polling_interval: Time between polls in seconds
            output_dir: Directory to store downloaded notebooks and images
            tag: Tag to search for (default: "Lilly")
            callback: Function to call when a tagged notebook is found
            claude_command: Command to run Claude (default: "claude")
            lilly_workspace: Path to Lilly's workspace directory
        """
        # Initialize the parent CassidyMonitor class
        super().__init__(
            adapter=adapter,
            rmapi_path=rmapi_path,
            polling_interval=polling_interval,
            output_dir=output_dir
            or os.path.join(CONFIG.get("TEMP_DIR", "/tmp"), "lilly_monitor"),
            tag=tag,
            callback=callback,
        )

        # Lilly-specific configuration
        self.claude_command = claude_command
        self.lilly_workspace = lilly_workspace or os.path.join(
            os.path.expanduser("~"), "dev", "remarkable-ink-link", "lilly"
        )

        # Create Lilly-specific directories
        os.makedirs(
            os.path.join(self.lilly_workspace, "workspace", "remarkable_sync"),
            exist_ok=True,
        )

        logger.info(f"Initialized Lilly Monitor with tag '{tag}'")
        logger.info(f"Using Claude command: {claude_command}")
        logger.info(f"Lilly workspace: {self.lilly_workspace}")

    def process_with_claude_vision(
        self, image_path: str, prompt: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Process an image with Claude vision capabilities.

        Args:
            image_path: Path to the image file
            prompt: Optional custom prompt for Claude

        Returns:
            Tuple of (success, result)
        """
        # Default prompt for processing handwritten notes
        if not prompt:
            prompt = """
            Please analyze this handwritten note from a reMarkable tablet.

            1. Transcribe the handwritten text, maintaining the formatting structure
            2. Identify any key concepts, entities, or topics mentioned
            3. Extract any tasks or action items
            4. Identify any questions that need answers
            5. Provide thoughtful insights or helpful information based on the content

            Structure your response clearly with appropriate headings.
            """

        logger.info(f"Processing image with Claude vision: {image_path}")

        # Create a temporary file for the prompt
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_file.write(prompt)
            prompt_file_path = temp_file.name

        try:
            # Run Claude with the image and prompt
            claude_result = subprocess.run(
                [self.claude_command, image_path, "--prompt-file", prompt_file_path],
                capture_output=True,
                text=True,
            )

            # Remove the temporary prompt file
            os.unlink(prompt_file_path)

            if claude_result.returncode != 0:
                logger.error(f"Error calling Claude: {claude_result.stderr}")
                return False, f"Error: {claude_result.stderr}"

            return True, claude_result.stdout

        except Exception as e:
            logger.error(f"Exception when calling Claude: {str(e)}")

            # Clean up temp file if it exists
            if os.path.exists(prompt_file_path):
                os.unlink(prompt_file_path)

            return False, f"Exception: {str(e)}"

    def update_knowledge_graph(
        self, image_path: str, claude_response: str, notebook_info: Dict[str, Any]
    ) -> bool:
        """
        Update the Neo4j knowledge graph with content from the image and Claude's response.

        Args:
            image_path: Path to the PNG image
            claude_response: Claude's response text
            notebook_info: Dictionary with notebook metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            # Path to the knowledge graph script
            kg_script = os.path.join(
                self.lilly_workspace, "tools", "process_handwriting.py"
            )

            # Run the script with the --kg flag to update the knowledge graph
            result = subprocess.run(
                [kg_script, image_path, "--content-type", "mixed", "--kg"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"Error updating knowledge graph: {result.stderr}")
                return False

            logger.info(f"Knowledge graph updated successfully: {result.stdout}")
            return True

        except Exception as e:
            logger.error(f"Exception updating knowledge graph: {str(e)}")
            return False

    def _process_tagged_document(self, doc: Dict[str, Any]):
        """
        Override the parent method to process a document that has been tagged with 'Lilly'.

        Args:
            doc: Document data including ID, name, metadata and tag info
        """
        doc_id = doc.get("id")
        doc_name = doc.get("name")

        if not doc_id or not doc_name:
            logger.error("Missing document ID or name")
            return

        logger.info(f"Processing tagged document: {doc_name} ({doc_id})")

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
        Process a notebook that has the Lilly tag at notebook level.

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

        # Process all pages in the notebook
        all_pages_processed = True

        for png_path in png_paths:
            # Process the page with Claude vision
            success, claude_response = self.process_with_claude_vision(png_path)

            if not success:
                logger.error(
                    f"Failed to process page {png_path} with Claude: {claude_response}"
                )
                all_pages_processed = False
                continue

            # Save the response to a file
            response_path = f"{os.path.splitext(png_path)[0]}_response.md"
            with open(response_path, "w") as f:
                f.write(claude_response)
            logger.info(f"Saved response to: {response_path}")

            # Update the knowledge graph
            kg_success = self.update_knowledge_graph(png_path, claude_response, doc)
            if not kg_success:
                logger.warning(f"Failed to update knowledge graph for {png_path}")
                # Don't mark as failure - knowledge graph is optional

            # Append response to the notebook
            try:
                page_id = os.path.splitext(os.path.basename(png_path))[0]
                success, message = self.adapter.append_text_to_notebook(
                    doc_id=doc_id,
                    page_id=page_id,
                    text=claude_response,
                    remove_tag=False,
                )

                if success:
                    logger.info(
                        f"Successfully appended response to notebook: {message}"
                    )
                else:
                    logger.error(f"Failed to append response to notebook: {message}")
                    all_pages_processed = False
            except Exception as e:
                logger.error(f"Error appending response to notebook: {str(e)}")
                all_pages_processed = False

        # If callback is defined, call it with the notebook info
        if self.callback:
            notebook_info = {
                "id": doc_id,
                "name": doc_name,
                "metadata": doc.get("metadata", {}),
                "png_paths": png_paths,
                "notebook_dir": notebook_dir,
                "type": "notebook",
                "all_pages_processed": all_pages_processed,
            }
            self.callback(notebook_info)

        # If all pages were processed successfully, remove the tag
        if all_pages_processed:
            try:
                success, message = self.adapter.remove_tag_from_notebook(
                    doc_id, self.tag
                )
                if success:
                    logger.info(f"Removed '{self.tag}' tag from notebook: {message}")
                else:
                    logger.error(f"Failed to remove tag from notebook: {message}")
            except Exception as e:
                logger.error(f"Error removing tag from notebook: {str(e)}")

    def _process_page(self, doc: Dict[str, Any], page: Dict[str, Any]):
        """
        Process a single page that has the Lilly tag.

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

        # Extract the page and convert to PNG
        with tempfile.TemporaryDirectory() as temp_dir:
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

                # Find the downloaded file
                if not os.path.exists(expected_file):
                    rmdoc_files = [f for f in os.listdir(".") if f.endswith(".rmdoc")]
                    if rmdoc_files:
                        expected_file = rmdoc_files[0]
                    else:
                        logger.error("No .rmdoc files found in temp directory")
                        return

                # Extract the specific page
                with tempfile.TemporaryDirectory() as extract_dir:
                    # Extract the .rm file for this page
                    success, rm_path = self._extract_page_file(
                        os.path.join(temp_dir, expected_file), page_id, extract_dir
                    )
                    if not success:
                        logger.error(f"Failed to extract page file: {rm_path}")
                        return

                    # Copy the file to the page directory
                    rm_file_in_page_dir = os.path.join(
                        page_dir, os.path.basename(rm_path)
                    )
                    shutil.copy(rm_path, rm_file_in_page_dir)

                    # Convert the page to PNG
                    # png_path = os.path.join(  # Currently unused
                    #     page_dir,
                    #     f"{os.path.splitext(os.path.basename(rm_path))[0]}.png",
                    # )
                    success, result = self.adapter.convert_rm_to_png(rm_path, page_dir)

                    if not success:
                        logger.error(f"Failed to convert page to PNG: {result}")
                        return

                    logger.info(f"Converted page to PNG: {result}")

                    # Process the page with Claude vision
                    success, claude_response = self.process_with_claude_vision(result)

                    if not success:
                        logger.error(
                            f"Failed to process page with Claude: {claude_response}"
                        )
                        return

                    # Save the response to a file
                    response_path = f"{os.path.splitext(result)[0]}_response.md"
                    with open(response_path, "w") as f:
                        f.write(claude_response)
                    logger.info(f"Saved response to: {response_path}")

                    # Update the knowledge graph
                    kg_success = self.update_knowledge_graph(
                        result, claude_response, doc
                    )
                    if not kg_success:
                        logger.warning(f"Failed to update knowledge graph for {result}")

                    # Append response to the notebook
                    try:
                        success, message = self.adapter.append_text_to_notebook(
                            doc_id=doc_id,
                            page_id=page_id,
                            text=claude_response,
                            remove_tag=True,  # Remove the tag after processing
                        )

                        if success:
                            logger.info(
                                f"Successfully appended response to notebook and removed tag: {message}"
                            )
                        else:
                            logger.error(
                                f"Failed to append response to notebook: {message}"
                            )
                    except Exception as e:
                        logger.error(f"Error appending response to notebook: {str(e)}")

                    # If callback is defined, call it with the page info
                    if self.callback:
                        page_info = {
                            "doc_id": doc_id,
                            "doc_name": doc_name,
                            "page_id": page_id,
                            "page_index": page_index,
                            "rm_path": rm_file_in_page_dir,
                            "png_path": result,
                            "response_path": response_path,
                            "type": "page",
                        }
                        self.callback(page_info)

            finally:
                # Change back to original directory
                os.chdir(current_dir)

    def _extract_page_file(
        self, zip_path: str, page_id: str, extract_dir: str
    ) -> Tuple[bool, str]:
        """
        Extract a specific page file from a reMarkable notebook.

        Args:
            zip_path: Path to the .rmdoc file
            page_id: ID of the page to extract
            extract_dir: Directory to extract to

        Returns:
            Tuple of (success, path/error_message)
        """
        try:
            import zipfile

            with zipfile.ZipFile(zip_path, "r") as zipf:
                # Look for .rm file with the page ID
                rm_paths = [
                    f for f in zipf.namelist() if f.endswith(".rm") and page_id in f
                ]

                if not rm_paths:
                    return False, f"No .rm file found for page ID {page_id}"

                # Extract the .rm file
                rm_path = rm_paths[0]
                zipf.extract(rm_path, extract_dir)

                # Get path to the extracted file
                extracted_rm_path = os.path.join(extract_dir, rm_path)
                logger.info(f"Extracted page file to {extracted_rm_path}")

                return True, extracted_rm_path

        except Exception as e:
            logger.error(f"Error extracting page file: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return False, str(e)
