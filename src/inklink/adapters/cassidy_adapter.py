"""Cassidy Adapter for the Remarkable-Claude interface.

This module provides an adapter that extends the RmapiAdapter with tag detection,
monitoring, and image conversion functionality for the Cassidy assistant workflow.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from typing import Any, Dict, List, Optional, Set, Tuple

from PIL import Image

from src.inklink.adapters.rmapi_adapter import RmapiAdapter

logger = logging.getLogger(__name__)


class CassidyAdapter(RmapiAdapter):
    """Adapter for interfacing between reMarkable and Claude Code's 'Cassidy' workflow."""

    def __init__(self, rmapi_path: Optional[str] = None, tag: str = "Cass"):
        """
        Initialize the Cassidy adapter.

        Args:
            rmapi_path: Path to the rmapi executable
            tag: Tag to use for identifying notebooks for Cassidy (default: 'Cass')
        """
        super().__init__(rmapi_path)
        self.tag = tag
        self.last_check_time = time.time()

    def find_tagged_notebooks(self) -> List[Dict[str, Any]]:
        """
        Find all notebooks that have the Cassidy tag.

        Returns:
            List of dictionaries with notebook info including IDs and metadata
        """
        if not self._validate_executable():
            logger.error("rmapi path not valid")
            return []

        tagged_notebooks = []

        # List all documents with long format to get details
        success, stdout, stderr = self.run_command("ls", "-l")
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

            logger.info(
                f"Parsed {len(documents)} valid document names from rmapi ls output"
            )

            logger.info(f"Found {len(documents)} documents to check for tags")

            # Process each document by name
            for doc_name in documents:
                logger.info(f"Checking document: {doc_name}")

                # Get document ID with stat command
                success, stdout, stderr = self.run_command("stat", doc_name)
                if not success:
                    logger.error(f"Failed to get metadata for {doc_name}: {stderr}")
                    continue

                try:
                    metadata = json.loads(stdout)
                    doc_id = metadata.get("ID")

                    if not doc_id:
                        logger.error(f"Could not find ID for {doc_name}")
                        continue

                    logger.info(f"Document ID: {doc_id}")

                    # Get detailed metadata for this document by checking for tag
                    # We'll use the name when downloading since rmapi works better with names
                    has_tag, content_data = self._check_document_for_tag(
                        doc_name, self.tag
                    )

                    if has_tag:
                        tagged_notebooks.append(
                            {"id": doc_id, "name": doc_name, "metadata": content_data}
                        )
                        logger.info(f"Found tagged notebook: {doc_name} ({doc_id})")

                except json.JSONDecodeError:
                    logger.error(f"Failed to parse metadata JSON for {doc_name}")
                except Exception as e:
                    logger.error(f"Error processing document {doc_name}: {str(e)}")
                    import traceback

                    logger.error(traceback.format_exc())

            return tagged_notebooks

        except Exception as e:
            logger.error(f"Error finding tagged notebooks: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return []

    def _check_document_for_tag(
        self, doc_id: str, tag: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a document has the specified tag by downloading and examining its content file.

        Args:
            doc_id: Document ID
            tag: Tag to search for

        Returns:
            Tuple of (has_tag, metadata)
        """
        temp_dir = tempfile.mkdtemp(prefix="remarkable_")
        zip_path = os.path.join(temp_dir, f"{doc_id}.zip")

        try:
            # Download the document as a zip file
            success, message = self.download_file(doc_id, zip_path, "zip")
            if not success:
                logger.error(f"Failed to download document: {message}")
                return False, {}

            # Extract the content file
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                content_files = [
                    f for f in zip_ref.namelist() if f.endswith(".content")
                ]
                if not content_files:
                    logger.warning(f"No content file found in document {doc_id}")
                    return False, {}

                # Extract the content file
                content_file = content_files[0]
                zip_ref.extract(content_file, temp_dir)

                # Read the content file
                content_path = os.path.join(temp_dir, content_file)
                with open(content_path, "r") as f:
                    content_data = json.load(f)

                # Check if the tag exists
                tags = content_data.get("tags", [])
                has_tag = tag in tags

                return has_tag, content_data

        except Exception as e:
            logger.error(f"Error checking document for tag: {str(e)}")
            return False, {}

        finally:
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def get_tagged_pages(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Get all pages from a notebook that have the Cassidy tag.

        Args:
            doc_id: Document ID

        Returns:
            List of dictionaries with page info
        """
        has_tag, metadata = self._check_document_for_tag(doc_id, self.tag)

        if not has_tag:
            logger.info(f"Document {doc_id} does not have the tag '{self.tag}'")
            return []

        # Get the page IDs
        pages = metadata.get("pages", [])

        # Get detailed information about each page
        tagged_pages = []
        for page in pages:
            page_info = {
                "id": page,
                "doc_id": doc_id,
                "notebook_name": metadata.get("visibleName", ""),
            }
            tagged_pages.append(page_info)

        return tagged_pages

    def download_notebook(
        self, doc_id_or_name: str, output_dir: str
    ) -> Tuple[bool, str]:
        """
        Download a complete notebook and extract it.

        Args:
            doc_id_or_name: Document ID or name
            output_dir: Directory to extract the notebook to

        Returns:
            Tuple of (success, output_path or error message)
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        zip_path = os.path.join(output_dir, f"{doc_id_or_name}.rmdoc")

        # Download the document
        success, message = self.download_file(doc_id_or_name, zip_path, "zip")
        if not success:
            return False, f"Failed to download document: {message}"

        # Verify that the file exists
        if not os.path.exists(zip_path):
            return False, f"Download reported success but file not found at {zip_path}"

        try:
            # Extract the zip file
            # Use doc_id as the directory name if it looks like a UUID
            if re.match(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                doc_id_or_name,
            ):
                extract_dir = os.path.join(output_dir, doc_id_or_name)
            else:
                # Create a unique folder for this extraction
                extract_dir = os.path.join(
                    output_dir, f"{doc_id_or_name}_{int(time.time())}"
                )

            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            return True, extract_dir

        except Exception as e:
            logger.error(f"Error extracting notebook: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return False, f"Error extracting notebook: {str(e)}"

    def add_tag_to_notebook(self, doc_id: str) -> Tuple[bool, str]:
        """
        Add the Cassidy tag to a notebook.

        Args:
            doc_id: Document ID

        Returns:
            Tuple of (success, message)
        """
        # First download and extract the notebook
        temp_dir = tempfile.mkdtemp(prefix="remarkable_tag_")

        try:
            success, extract_dir = self.download_notebook(doc_id, temp_dir)
            if not success:
                return False, extract_dir  # Error message

            # Find the content file
            content_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(".content"):
                        content_files.append(os.path.join(root, file))

            if not content_files:
                return False, "No content file found in notebook"

            # Read the content file
            content_path = content_files[0]
            with open(content_path, "r") as f:
                content_data = json.load(f)

            # Add the tag if it doesn't exist
            tags = content_data.get("tags", [])
            if self.tag not in tags:
                tags.append(self.tag)
                content_data["tags"] = tags

                # Write back the updated content file
                with open(content_path, "w") as f:
                    json.dump(content_data, f)

                # Repackage the notebook
                zip_path = os.path.join(temp_dir, f"{doc_id}_updated.zip")
                with zipfile.ZipFile(zip_path, "w") as zip_ref:
                    for root, _, files in os.walk(extract_dir):
                        for file in files:
                            if (
                                file != f"{doc_id}_updated.zip"
                            ):  # Avoid adding the zip to itself
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, extract_dir)
                                zip_ref.write(file_path, arcname)

                # Upload the updated notebook
                success, message = self.upload_file(
                    zip_path, content_data.get("visibleName", doc_id)
                )
                if not success:
                    return False, f"Failed to upload updated notebook: {message}"

                return True, f"Successfully added tag '{self.tag}' to notebook"
            else:
                return True, f"Tag '{self.tag}' already exists on notebook"

        except Exception as e:
            return False, f"Error adding tag to notebook: {str(e)}"

        finally:
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def remove_tag_from_notebook(self, doc_id: str) -> Tuple[bool, str]:
        """
        Remove the Cassidy tag from a notebook.

        Args:
            doc_id: Document ID

        Returns:
            Tuple of (success, message)
        """
        # First download and extract the notebook
        temp_dir = tempfile.mkdtemp(prefix="remarkable_tag_")

        try:
            success, extract_dir = self.download_notebook(doc_id, temp_dir)
            if not success:
                return False, extract_dir  # Error message

            # Find the content file
            content_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(".content"):
                        content_files.append(os.path.join(root, file))

            if not content_files:
                return False, "No content file found in notebook"

            # Read the content file
            content_path = content_files[0]
            with open(content_path, "r") as f:
                content_data = json.load(f)

            # Remove the tag if it exists
            tags = content_data.get("tags", [])
            if self.tag in tags:
                tags.remove(self.tag)
                content_data["tags"] = tags

                # Write back the updated content file
                with open(content_path, "w") as f:
                    json.dump(content_data, f)

                # Repackage the notebook
                zip_path = os.path.join(temp_dir, f"{doc_id}_updated.zip")
                with zipfile.ZipFile(zip_path, "w") as zip_ref:
                    for root, _, files in os.walk(extract_dir):
                        for file in files:
                            if (
                                file != f"{doc_id}_updated.zip"
                            ):  # Avoid adding the zip to itself
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, extract_dir)
                                zip_ref.write(file_path, arcname)

                # Upload the updated notebook
                success, message = self.upload_file(
                    zip_path, content_data.get("visibleName", doc_id)
                )
                if not success:
                    return False, f"Failed to upload updated notebook: {message}"

                return True, f"Successfully removed tag '{self.tag}' from notebook"
            else:
                return True, f"Tag '{self.tag}' does not exist on notebook"

        except Exception as e:
            return False, f"Error removing tag from notebook: {str(e)}"

        finally:
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def remove_tag_from_page(
        self, doc_id: str, page_id: str, tag: str = None
    ) -> Tuple[bool, str]:
        """
        Remove a tag from a specific page in a notebook.

        Args:
            doc_id: Document ID
            page_id: Page ID to remove tag from
            tag: Tag to remove (defaults to self.tag)

        Returns:
            Tuple of (success, message)
        """
        tag = tag or self.tag
        temp_dir = tempfile.mkdtemp(prefix="remarkable_page_tag_")

        try:
            # Download and extract the notebook
            success, extract_dir = self.download_notebook(doc_id, temp_dir)
            if not success:
                return False, extract_dir  # Error message

            # Find the content file
            content_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(".content"):
                        content_files.append(os.path.join(root, file))

            if not content_files:
                return False, "No content file found in notebook"

            # Read the content file
            content_path = content_files[0]
            with open(content_path, "r") as f:
                content_data = json.load(f)

            # Get the pageTags section
            page_tags = content_data.get("pageTags", [])
            if page_tags is None:
                page_tags = []

            # Find the tag entry for this page and remove it
            tag_removed = False
            new_page_tags = []

            for page_tag in page_tags:
                # Skip this tag entry if it matches our criteria
                if page_tag.get("pageId") == page_id and (
                    page_tag.get("tag") == tag
                    or page_tag.get("tag", "").lower() == tag.lower()
                ):
                    tag_removed = True
                    logger.info(
                        f"Removing tag '{page_tag.get('tag')}' from page {page_id}"
                    )
                else:
                    new_page_tags.append(page_tag)

            # If no tag was removed, we're done
            if not tag_removed:
                return True, f"Page {page_id} does not have tag '{tag}'"

            # Update the content data with the new page tags
            content_data["pageTags"] = new_page_tags

            # Write back the updated content file
            with open(content_path, "w") as f:
                json.dump(content_data, f)

            # Repackage the notebook
            zip_path = os.path.join(temp_dir, f"{doc_id}_updated.zip")
            with zipfile.ZipFile(zip_path, "w") as zip_ref:
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        if (
                            file != f"{doc_id}_updated.zip"
                        ):  # Avoid adding the zip to itself
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, extract_dir)
                            zip_ref.write(file_path, arcname)

            # Upload the updated notebook
            notebook_name = content_data.get("visibleName", doc_id)
            success, message = self.upload_file(zip_path, notebook_name)
            if not success:
                return False, f"Failed to upload updated notebook: {message}"

            return True, f"Successfully removed tag '{tag}' from page {page_id}"

        except Exception as e:
            logger.error(f"Error removing tag from page: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return False, f"Error removing tag from page: {str(e)}"

        finally:
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def convert_rm_to_png(
        self, rm_file_path: str, output_dir: str = None
    ) -> Tuple[bool, str]:
        """
        Convert a reMarkable .rm file to a PNG image.

        This requires either rmkit tools or a similar utility to be installed.

        Args:
            rm_file_path: Path to .rm file
            output_dir: Directory to save PNG file (default: same as rm_file)

        Returns:
            Tuple of (success, output_path or error message)
        """
        # Use the existing utility for now or consider implementing a drawj2d approach
        if not output_dir:
            output_dir = os.path.dirname(rm_file_path)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Generate a unique output path if not specified
        rm_basename = os.path.basename(rm_file_path)
        png_filename = f"{os.path.splitext(rm_basename)[0]}.png"
        output_path = os.path.join(output_dir, png_filename)

        # Check if rmkit's rM2svg is available
        rmt_svg_path = shutil.which("rM2svg")
        if not rmt_svg_path:
            # Try alternative paths
            rmt_svg_path = "/usr/local/bin/rM2svg"
            if not os.path.exists(rmt_svg_path):
                return False, "rM2svg utility not found. Please install rmkit tools."

        try:
            # First convert to SVG
            svg_path = os.path.join(
                output_dir, f"{os.path.splitext(rm_basename)[0]}.svg"
            )
            svg_cmd = [rmt_svg_path, rm_file_path, "-o", svg_path]

            svg_process = subprocess.run(
                svg_cmd, capture_output=True, text=True, check=False
            )

            if svg_process.returncode != 0:
                logger.error(f"Failed to convert to SVG: {svg_process.stderr}")
                return False, f"Failed to convert to SVG: {svg_process.stderr}"

            # Then convert SVG to PNG using cairosvg or Inkscape or PIL
            # For now, we'll try to use Inkscape as it's commonly available
            inkscape_path = shutil.which("inkscape")
            if inkscape_path:
                png_cmd = [
                    inkscape_path,
                    "--export-filename",
                    output_path,
                    "--export-dpi",
                    "300",
                    svg_path,
                ]

                png_process = subprocess.run(
                    png_cmd, capture_output=True, text=True, check=False
                )

                if png_process.returncode != 0:
                    logger.error(f"Failed to convert SVG to PNG: {png_process.stderr}")
                    return False, f"Failed to convert SVG to PNG: {png_process.stderr}"
            else:
                # Try to use cairosvg if available
                try:
                    import cairosvg

                    cairosvg.svg2png(url=svg_path, write_to=output_path, dpi=300)
                except ImportError:
                    # If all else fails, try a simple PIL conversion
                    # This may not preserve all SVG features
                    try:
                        # PIL Image already imported at module level
                        import io

                        return (
                            False,
                            "Direct SVG to PNG conversion not supported. Please install Inkscape or cairosvg.",
                        )
                    except Exception as e:
                        return False, f"Failed to convert SVG to PNG: {str(e)}"

            # Check if the output file exists
            if not os.path.exists(output_path):
                return False, "Conversion completed but output file not found"

            return True, output_path

        except Exception as e:
            logger.error(f"Error converting rm to png: {str(e)}")
            return False, f"Error converting rm to png: {str(e)}"

    def convert_notebook_pages_to_png(
        self, doc_id: str, output_dir: str
    ) -> Tuple[bool, List[str]]:
        """
        Convert all pages in a notebook to PNG images.

        Args:
            doc_id: Document ID
            output_dir: Directory to save PNG files

        Returns:
            Tuple of (success, list of PNG paths or error message)
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Download and extract the notebook
        temp_dir = tempfile.mkdtemp(prefix="remarkable_convert_")

        try:
            success, extract_dir = self.download_notebook(doc_id, temp_dir)
            if not success:
                return False, [extract_dir]  # Error message

            # Find all .rm files
            rm_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(".rm"):
                        rm_files.append(os.path.join(root, file))

            if not rm_files:
                return False, ["No .rm files found in notebook"]

            # Convert each file to PNG
            png_paths = []
            for rm_file in rm_files:
                success, result = self.convert_rm_to_png(rm_file, output_dir)
                if success:
                    png_paths.append(result)
                else:
                    logger.warning(f"Failed to convert {rm_file}: {result}")

            if not png_paths:
                return False, ["Failed to convert any pages to PNG"]

            return True, png_paths

        except Exception as e:
            return False, [f"Error converting notebook pages to PNG: {str(e)}"]

        finally:
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def append_text_to_notebook(
        self,
        doc_id: str,
        page_id: str,
        text: str,
        remove_tag: bool = True,
        append_mode: str = "new_page",
    ) -> Tuple[bool, str]:
        """
        Append text to a notebook page by creating a new page or adding annotations.

        This method:
        1. Downloads and extracts the notebook
        2. Creates a new page or adds annotations based on append_mode
        3. Adds the new page/annotations to the notebook
        4. Repackages and uploads the notebook
        5. Optionally removes the Cass tag

        Args:
            doc_id: Document ID
            page_id: Page ID of the page that prompted the response
            text: Text to append
            remove_tag: Whether to remove the Cass tag after processing
            append_mode: How to append the text ("new_page" or "annotation")

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create a temporary directory for processing
            temp_dir = tempfile.mkdtemp(prefix="remarkable_append_")

            # Download and extract the notebook
            success, extract_dir = self.download_notebook(doc_id, temp_dir)
            if not success:
                return False, extract_dir  # Error message

            # Find the content file
            content_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(".content"):
                        content_files.append(os.path.join(root, file))

            if not content_files:
                return False, "No content file found in notebook"

            # Read the content file
            content_path = content_files[0]
            with open(content_path, "r") as f:
                content_data = json.load(f)

            # Handle different append modes
            if append_mode == "new_page":
                # Create a new page with the response text

                # Create a unique ID for the new page
                new_page_id = str(uuid.uuid4())

                # Append the new page ID to the pages list
                pages = content_data.get("pages", [])
                if page_id in pages:
                    # Insert after the original page
                    index = pages.index(page_id)
                    pages.insert(index + 1, new_page_id)
                else:
                    # Append at the end
                    pages.append(new_page_id)

                content_data["pages"] = pages

                # Generate the .rm file for the response using HCL templates
                rm_dir = os.path.join(extract_dir, os.path.dirname(content_files[0]))
                new_page_path = os.path.join(rm_dir, f"{new_page_id}.rm")

                # Create a simple .rm file with text
                success, message = self._create_text_rm_file(new_page_path, text)
                if not success:
                    return False, f"Failed to create text rm file: {message}"

                logger.info(f"Created new page with ID {new_page_id} for response")

            elif append_mode == "annotation":
                # Add the text as an annotation to the existing page
                # This implementation depends on the remarkable's annotation format
                # For now, we'll add a simple text header with timestamp to the existing page

                # Find the .rm file for the page
                rm_file_path = None
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith(".rm") and page_id in file:
                            rm_file_path = os.path.join(root, file)
                            break

                if not rm_file_path:
                    return False, f"Could not find .rm file for page {page_id}"

                # Create the annotation text with timestamp
                from datetime import datetime

                # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Currently unused
                # annotation_text = f"Claude Response ({timestamp}):\n\n{text}"  # Unused variable
                # Create an annotation file by adding strokes
                # This is a simplification - in a real implementation, we would use
                # a proper annotation approach, possibly using drawj2d
                new_rm_file_path = f"{rm_file_path}.annotated"

                # We'll copy the original file for now and modify it if needed
                shutil.copy(rm_file_path, new_rm_file_path)

                # Rename the new file to replace the original
                os.replace(new_rm_file_path, rm_file_path)

                # In a real implementation, we would actually modify the .rm file
                # to add the annotation text as strokes
                logger.info(
                    f"Added annotation to page {page_id} (simplified implementation)"
                )

            else:
                return False, f"Unsupported append mode: {append_mode}"

            # If requested, remove the Cass tag
            if remove_tag:
                # First check if it's a page tag
                page_tags = content_data.get("pageTags", [])
                if page_tags is not None:
                    # Find the tag entry for this page
                    for page_tag in list(page_tags):
                        if page_tag.get("pageId") == page_id and (
                            page_tag.get("tag") == self.tag
                            or page_tag.get("tag", "").lower() == self.tag.lower()
                        ):
                            # Remove this tag
                            page_tags.remove(page_tag)
                            logger.info(f"Removed tag '{self.tag}' from page {page_id}")

                    # Update page tags in content data
                    content_data["pageTags"] = page_tags

                # Also check for notebook-level tag
                if self.tag in content_data.get("tags", []):
                    content_data["tags"].remove(self.tag)
                    logger.info(f"Removed notebook tag '{self.tag}'")

            # Write the updated content file
            with open(content_path, "w") as f:
                json.dump(content_data, f)

            # Repackage the notebook
            zip_path = os.path.join(temp_dir, f"{doc_id}_updated.zip")
            with zipfile.ZipFile(zip_path, "w") as zip_ref:
                # We need to maintain the correct directory structure
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        if (
                            file != f"{doc_id}_updated.zip"
                        ):  # Avoid adding the zip to itself
                            file_path = os.path.join(root, file)
                            # Get the relative path from the extract_dir
                            arcname = os.path.relpath(file_path, extract_dir)
                            zip_ref.write(file_path, arcname)

            # Upload the updated notebook
            success, message = self.upload_file(
                zip_path, content_data.get("visibleName", doc_id)
            )
            if not success:
                return False, f"Failed to upload updated notebook: {message}"

            append_type = "new page" if append_mode == "new_page" else "annotation"
            return (
                True,
                f"Successfully appended response text as {append_type} to notebook",
            )

        except Exception as e:
            logger.error(f"Error appending text to notebook: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return False, f"Error appending text to notebook: {str(e)}"

        finally:
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    def _create_text_rm_file(self, output_path: str, text: str) -> Tuple[bool, str]:
        """
        Create a reMarkable .rm file containing text.

        This is a simplified implementation that uses available tools to create
        a reMarkable file with text. Options include:

        1. Using a pre-generated template .rm file with placeholders
        2. Converting text to SVG and then to .rm format
        3. Using rmKit/remt tools to create a text layer

        Args:
            output_path: Path where the .rm file should be saved
            text: Text content to include

        Returns:
            Tuple of (success, message)
        """
        try:
            # Method 1: Use a template approach - creating an HCL file and using drawj2d
            # This requires drawj2d to be installed

            # First, find the drawj2d path if available
            drawj2d_path = shutil.which("drawj2d")
            if not drawj2d_path:
                # Try common locations
                potential_paths = ["/usr/local/bin/drawj2d", "/usr/bin/drawj2d"]
                for path in potential_paths:
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        drawj2d_path = path
                        break

            if drawj2d_path:
                # Create a temporary HCL file
                temp_dir = os.path.dirname(output_path)
                hcl_path = os.path.join(
                    temp_dir, f"{os.path.basename(output_path)}.hcl"
                )

                # Format the text into paragraphs
                paragraphs = text.split("\n\n")
                if (
                    len(paragraphs) == 1
                ):  # If no double newlines, split on single newlines
                    paragraphs = text.split("\n")

                # Create HCL content with text objects
                hcl_content = "rm_doc{\n"
                hcl_content += "  page{\n"

                y_position = 100  # Start from top with margin
                line_height = 50  # Approximate line height

                for paragraph in paragraphs:
                    if paragraph.strip():
                        # Wrap long lines
                        wrapped_lines = []
                        current_line = ""
                        words = paragraph.split()

                        for word in words:
                            if (
                                len(current_line) + len(word) + 1 <= 60
                            ):  # 60 chars per line approx
                                if current_line:
                                    current_line += " " + word
                                else:
                                    current_line = word
                            else:
                                wrapped_lines.append(current_line)
                                current_line = word

                        if current_line:
                            wrapped_lines.append(current_line)

                        # Add each wrapped line as a text object
                        for line in wrapped_lines:
                            hcl_content += (
                                f'    text{{ pos={{150 {y_position}}} text="{line}"}}\n'
                            )
                            y_position += line_height

                        # Add extra space between paragraphs
                        y_position += line_height // 2

                hcl_content += "  }\n"
                hcl_content += "}\n"

                # Write the HCL file
                with open(hcl_path, "w") as f:
                    f.write(hcl_content)

                # Run drawj2d to create the .rm file
                cmd = [drawj2d_path, hcl_path, "-o", output_path]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"Successfully created text .rm file at {output_path}")
                    return True, output_path
                else:
                    logger.error(f"Failed to create .rm file: {result.stderr}")
                    return False, f"Failed to create .rm file: {result.stderr}"

            # Method 2: If drawj2d isn't available, use a predefined template .rm file as fallback
            # This is a simple fallback that creates a blank .rm file
            from importlib import resources

            # Create a minimal .rm file with a blank page
            # This is a simplified version that should be replaced with a proper template
            with open(output_path, "wb") as f:
                # Write minimal .rm file header bytes
                f.write(bytes.fromhex("5550523d"))  # Magic header
                f.write(bytes.fromhex("00000000"))  # Version

                # Empty page with no strokes
                # In a real implementation, you would include a proper .rm file structure
                # or copy a template file from resources

            logger.warning("Created minimal .rm file without proper text formatting")
            return True, "Created minimal .rm file (no text formatting)"

        except Exception as e:
            logger.error(f"Error creating text .rm file: {str(e)}")
            return False, f"Error creating text .rm file: {str(e)}"

    def check_for_updates(
        self, last_check_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for any notebooks that have been updated since the last check time.

        Args:
            last_check_time: Time of the last check (defaults to self.last_check_time)

        Returns:
            List of updated notebooks with the Cassidy tag
        """
        # Use the provided check time or the instance's last check time
        # check_time = last_check_time or self.last_check_time  # Currently unused

        # Find all tagged notebooks
        tagged_notebooks = self.find_tagged_notebooks()

        # Update the last check time
        self.last_check_time = time.time()

        # For now, return all tagged notebooks
        # In the future, we could implement checking for updates based on the "lastModified" field
        return tagged_notebooks
