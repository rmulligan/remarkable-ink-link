"""Remarkable API adapter for InkLink.

This module provides an adapter for interacting with the reMarkable Cloud API
via the rmapi tool, including authentication handling.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RmapiAdapter:
    """Adapter for interacting with reMarkable Cloud via rmapi tool."""

    def __init__(self, rmapi_path: Optional[str] = None):
        """
        Initialize the rmapi adapter.

        Args:
            rmapi_path: Path to the rmapi executable
        """
        self.rmapi_path = rmapi_path
        self._validate_executable()

    def _validate_executable(self) -> bool:
        """
        Validate that the rmapi executable exists and is executable.
        If not available, attempts to download the ddvk fork.

        Returns:
            True if valid, False otherwise
        """
        # If rmapi exists and is executable, we're good
        if (
            self.rmapi_path
            and os.path.exists(self.rmapi_path)
            and os.access(self.rmapi_path, os.X_OK)
        ):
            return True

        # Try to download the ddvk fork of rmapi
        return self._download_ddvk_rmapi()

    def _download_ddvk_rmapi(self) -> bool:
        """
        Download the ddvk fork of rmapi if not available.

        Returns:
            True if download successful, False otherwise
        """
        import platform
        import stat

        import requests

        try:
            # Determine OS and architecture
            system = platform.system().lower()
            machine = platform.machine().lower()

            # Map to GitHub release asset names
            if system == "linux":
                asset_name = "rmapi-linuxx86-64.tar.gz"
            elif system == "darwin":
                asset_name = "rmapi-macosx.zip"
            elif system == "windows":
                asset_name = "rmapi-win64.zip"
            else:
                logger.error(f"Unsupported platform: {system} {machine}")
                return False

            # Get the latest release URL
            release_url = "https://api.github.com/repos/ddvk/rmapi/releases/latest"
            response = requests.get(release_url, timeout=10)
            response.raise_for_status()
            release_data = response.json()

            # Find the matching asset
            asset_url = None
            for asset in release_data.get("assets", []):
                if asset["name"] == asset_name:
                    asset_url = asset["browser_download_url"]
                    break

            if not asset_url:
                logger.error(f"Could not find release asset for {asset_name}")
                return False

            # Determine destination directory
            bin_dir = os.path.expanduser("~/.local/bin")
            os.makedirs(bin_dir, exist_ok=True)

            # Create a temp directory for extraction
            temp_dir = tempfile.mkdtemp(prefix="rmapi_download_")
            download_path = os.path.join(temp_dir, asset_name)
            dest_path = os.path.join(bin_dir, "rmapi")

            try:
                # Download the archive
                logger.info(f"Downloading rmapi from {asset_url} to {download_path}")
                response = requests.get(asset_url, timeout=30)
                response.raise_for_status()

                # Save the downloaded file
                with open(download_path, "wb") as f:
                    f.write(response.content)

                # Extract based on file type
                if asset_name.endswith(".tar.gz"):
                    import tarfile

                    with tarfile.open(download_path, "r:gz") as tar:
                        tar.extractall(path=temp_dir)
                    # Find the binary
                    binary_name = "rmapi"
                    binary_path = os.path.join(temp_dir, binary_name)

                elif asset_name.endswith(".zip"):
                    import zipfile

                    with zipfile.ZipFile(download_path, "r") as zip_ref:
                        zip_ref.extractall(temp_dir)
                    # For macOS, binary name might be different
                    binary_name = "rmapi"
                    binary_path = os.path.join(temp_dir, binary_name)

                # Copy the binary to destination
                if os.path.exists(binary_path):
                    shutil.copy2(binary_path, dest_path)
                else:
                    # Try to find any executable in the temp directory
                    found = False
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            if "rmapi" in file.lower() and not file.endswith(
                                (".tar.gz", ".zip")
                            ):
                                file_path = os.path.join(root, file)
                                shutil.copy2(file_path, dest_path)
                                found = True
                                break
                        if found:
                            break

                    if not found:
                        raise FileNotFoundError(
                            f"Could not find rmapi binary in extracted files"
                        )

                # Make it executable
                os.chmod(
                    dest_path,
                    os.stat(dest_path).st_mode
                    | stat.S_IXUSR
                    | stat.S_IXGRP
                    | stat.S_IXOTH,
                )

            finally:
                # Clean up temp directory
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.error(f"Failed to clean up temp directory: {e}")

            # Update the path
            self.rmapi_path = dest_path
            logger.info(f"Successfully downloaded rmapi to {dest_path}")

            return True

        except Exception as e:
            logger.error(f"Error downloading rmapi: {str(e)}")
            return False

    def authenticate_with_code(self, code: str) -> Tuple[bool, str]:
        """
        Authenticate with reMarkable Cloud using the provided one-time code.

        Args:
            code: One-time authentication code

        Returns:
            Tuple containing success status and message
        """
        if not self._validate_executable():
            return False, "rmapi path not valid"

        logger.info("Starting rmapi authentication with one-time code")

        # First try expect script approach
        try:
            result = self._authenticate_with_expect(code)
            if result[0]:
                return result
            logger.warning(f"Expect script authentication failed: {result[1]}")
        except Exception as e:
            logger.warning(f"Expect script approach failed: {str(e)}")

        # Fallback to named pipe approach
        try:
            return self._authenticate_with_pipe(code)
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, str(e)

    def _authenticate_with_expect(self, code: str) -> Tuple[bool, str]:
        """
        Authenticate using an expect script.

        Args:
            code: One-time authentication code

        Returns:
            Tuple containing success status and message
        """
        # Create a temporary expect script file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".exp", delete=False
        ) as expect_file:
            expect_path = expect_file.name
            expect_file.write(
                f"""#!/usr/bin/expect -f
                set timeout 30
                set code "{code}"

                spawn {self.rmapi_path} ls
                expect {{
                    "Enter one-time code:" {{
                        send "$code\\r"
                        exp_continue
                    }}
                    "Permanent token stored" {{
                        exit 0
                    }}
                    eof {{
                        exit 1
                    }}
                    timeout {{
                        exit 2
                    }}
                }}
                """
            )

        try:
            # Make the script executable
            os.chmod(expect_path, 0o755)

            # Run the expect script
            process = subprocess.run(
                [expect_path], capture_output=True, text=True, timeout=45
            )

            # Check if authentication was successful
            if process.returncode == 0:
                logger.info("Authentication successful using expect script")
                return True, "Authentication successful"

            # If expect script failed, log the details
            return (
                False,
                f"Expect script failed with code {process.returncode}, output: {process.stdout}",
            )

        finally:
            # Remove the temporary script
            try:
                os.unlink(expect_path)
            except Exception:
                pass

    def _authenticate_with_pipe(self, code: str) -> Tuple[bool, str]:
        """
        Authenticate using a named pipe.

        Args:
            code: One-time authentication code

        Returns:
            Tuple containing success status and message
        """
        # Create a named pipe (FIFO)
        pipe_path = os.path.join(
            tempfile.gettempdir(), f"rmapi_auth_{int(time.time())}.pipe"
        )
        try:
            os.mkfifo(pipe_path)
        except Exception as e:
            logger.error(f"Failed to create named pipe: {str(e)}")
            return False, f"Failed to create pipe: {str(e)}"

        try:
            # Start a process that will write the code to the pipe
            with open(pipe_path, "w") as fifo:
                # Write the code with a newline
                fifo.write(f"{code}\n")
                fifo.flush()

                # Run rmapi with stdin from the pipe
                process = subprocess.run(
                    [self.rmapi_path, "ls"],
                    stdin=open(pipe_path, "r"),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            # Check the result
            if process.returncode == 0:
                logger.info("Authentication successful using named pipe")
                return True, "Authentication successful"
            else:
                logger.error(f"Authentication failed: {process.stderr}")
                return False, process.stderr

        finally:
            # Remove the pipe
            try:
                os.unlink(pipe_path)
            except Exception:
                pass

    def run_command(self, command: str, *args) -> Tuple[bool, str, str]:
        """
        Run an rmapi command.

        Args:
            command: The rmapi command to run
            *args: Additional arguments for the command

        Returns:
            Tuple containing (success status, stdout, stderr)
        """
        if not self._validate_executable():
            return False, "", "rmapi path not valid"

        try:
            cmd = [self.rmapi_path, command] + list(args)
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if process.returncode == 0:
                return True, process.stdout, process.stderr
            else:
                logger.error(f"rmapi command failed: {process.stderr}")
                return False, process.stdout, process.stderr

        except Exception as e:
            logger.error(f"Error running rmapi command: {str(e)}")
            return False, "", str(e)

    def upload_file(self, file_path: str, title: str) -> Tuple[bool, str]:
        """
        Upload a file to reMarkable Cloud.

        Args:
            file_path: Path to the file to upload
            title: Title for the document in reMarkable

        Returns:
            Tuple of (success, message)
        """
        if not self._validate_executable():
            return False, "rmapi path not valid"

        # First use 'put' to upload the file
        success, stdout, stderr = self.run_command("put", file_path)
        if not success:
            return False, f"Failed to upload: {stderr}"

        # Check for document ID in output
        doc_id = None
        for line in stdout.splitlines():
            if "ID:" in line:
                parts = line.split("ID:")
                if len(parts) > 1:
                    doc_id = parts[1].strip()

        if doc_id:
            # If we found an ID, try to rename the document
            success, _, stderr = self.run_command("mv", doc_id, title)
            if not success:
                return (
                    True,
                    f"Document uploaded to reMarkable but renaming failed: {stderr}",
                )
            return True, f"Document '{title}' uploaded successfully"
        else:
            # No ID found, but upload seems successful
            return True, "Document uploaded to reMarkable"

    def download_file(
        self, doc_id_or_name: str, output_path: str, export_format: str = "pdf"
    ) -> Tuple[bool, str]:
        """
        Download a file from reMarkable Cloud.

        Args:
            doc_id_or_name: Document ID or name to download
            output_path: Path where to save the downloaded file
            export_format: Format to export (pdf, epub, etc.)

        Returns:
            Tuple of (success, message)
        """
        if not self._validate_executable():
            return False, "rmapi path not valid"

        # Log the download attempt
        logger.info(
            f"Attempting to download document '{doc_id_or_name}' to '{output_path}'"
        )

        # Get the directory where the file will be downloaded
        output_dir = os.path.dirname(output_path)
        if not output_dir:
            output_dir = "."

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Create a working directory
        with tempfile.TemporaryDirectory() as working_dir:
            success = False

            try:
                # Use single quotes around the notebook name and absolute path for rmapi
                rmapi_abs_path = os.path.abspath(self.rmapi_path)
                cmd = f"{rmapi_abs_path} get '{doc_id_or_name}'"

                # Change to the working directory to execute the command
                original_dir = os.getcwd()
                os.chdir(working_dir)

                logger.info(
                    f"Running download command: {cmd} in directory {working_dir}"
                )
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=60
                )
                logger.info(f"Command output: {result.stdout}")
                logger.info(f"Command error (if any): {result.stderr}")

                # Check what files were actually downloaded
                downloaded_files = os.listdir(working_dir)
                logger.info(
                    f"Files in working directory after download: {downloaded_files}"
                )

                if downloaded_files:
                    # Find a possible match - prefer .rmdoc files
                    rmdoc_files = [f for f in downloaded_files if f.endswith(".rmdoc")]
                    if rmdoc_files:
                        downloaded_file = rmdoc_files[0]
                    else:
                        # Just use the first file
                        downloaded_file = downloaded_files[0]

                    # Copy to the output path
                    src_path = os.path.join(working_dir, downloaded_file)
                    logger.info(f"Copying {src_path} to {output_path}")
                    shutil.copy2(src_path, output_path)
                    success = True
                else:
                    logger.error(f"No files were downloaded for '{doc_id_or_name}'")

                # Restore original directory
                os.chdir(original_dir)

            except Exception as e:
                logger.error(f"Error executing download command: {e}")
                try:
                    os.chdir(original_dir)  # Make sure we restore the directory
                except Exception:
                    pass
                return False, f"Failed to download: {str(e)}"

        # Verify successful download
        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(
                f"Successfully downloaded document to {output_path} ({os.path.getsize(output_path)} bytes)"
            )
            return True, f"Downloaded document {doc_id_or_name}"

        # If download failed, return failure instead of masking it
        logger.error(
            f"Failed to download document '{doc_id_or_name}' to '{output_path}'"
        )
        return False, f"Failed to download document {doc_id_or_name}"

    def ping(self) -> bool:
        """
        Check if the reMarkable Cloud API is available and authenticated.

        Returns:
            True if API is accessible, False otherwise
        """
        if not self._validate_executable():
            return False

        # Try to run a simple 'ls' command
        success, _, _ = self.run_command("ls")
        return success

    def list_files(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        List all files and notebooks on the reMarkable Cloud.

        Returns:
            Tuple of (success, list of documents)
        """
        if not self._validate_executable():
            logger.error("rmapi path not valid")
            return False, []

        try:
            # Run the ls command to list files
            success, stdout, stderr = self.run_command("ls")
            if not success:
                logger.error(f"Failed to list documents: {stderr}")
                return False, []

            # Debug output for troubleshooting
            logger.info(f"Raw output from rmapi ls command:")
            for line in stdout.split("\n"):
                if line.strip():
                    logger.info(f"  {line}")

            # Process the output
            documents = []

            logger.info("Processing file listing")
            for line in stdout.split("\n"):
                line = line.strip()
                if not line:
                    continue

                logger.info(f"Processing line: {line}")

                # Extract name and type
                if line.startswith("[f]"):
                    # Format: [f] filename
                    name = line[3:].strip()
                    doc_type = "DocumentType"
                    logger.info(f"Found file: {name}")
                elif line.startswith("[d]"):
                    # Format: [d] directory
                    name = line[3:].strip()
                    doc_type = "CollectionType"
                    logger.info(f"Found directory: {name}")
                else:
                    # Some other format, try to handle generically
                    name = line
                    doc_type = "DocumentType"
                    if "/" in name:
                        doc_type = "CollectionType"
                    logger.info(
                        f"Found item with unknown format: {name}, treating as {doc_type}"
                    )

                # Create document entry, using name as ID when no ID is available
                doc_entry = {
                    "ID": name,  # Use name as ID when no ID is available
                    "VissibleName": name,
                    "Type": doc_type,
                }

                documents.append(doc_entry)
                logger.info(f"Added document: {doc_entry}")

            logger.info(f"Found {len(documents)} documents")

            # If no documents found but stdout contains data, there might be a parsing issue
            if not documents and stdout.strip():
                logger.warning("No documents parsed but output exists. Raw output:")
                logger.warning(stdout)

            return True, documents

        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return False, []

    def find_tagged_notebooks(
        self, tag: str = "Cass", pre_filter_tag: str = None
    ) -> List[Dict[str, Any]]:
        """
        Find all notebooks that have the specified tag.

        Args:
            tag: Tag to search for, defaults to "Cass"
            pre_filter_tag: Optional tag to pre-filter notebooks (e.g., "HasLilly")
                            This avoids downloading every notebook for checking.

        Returns:
            List of dictionaries with notebook info including IDs and metadata
        """
        if not self._validate_executable():
            logger.error("rmapi path not valid")
            return []

        tagged_notebooks = []

        # Use improved list_files method to get all documents
        success, documents = self.list_files()
        if not success:
            logger.error("Failed to list documents")
            return []

        # Log the number of documents found
        logger.info(f"Found {len(documents)} documents to check for tag '{tag}'")
        if pre_filter_tag:
            logger.info(f"Using pre-filter tag '{pre_filter_tag}' to reduce downloads")

        try:
            # Process each document to check for tags
            for doc in documents:
                # Get document details
                doc_id = doc.get("ID")
                name = doc.get("VissibleName", doc_id)
                doc_type = doc.get("Type", "Unknown")

                logger.info(
                    f"Checking document: {name} (ID: {doc_id}, Type: {doc_type})"
                )

                # Skip certain document types that are unlikely to be notebooks
                if name.lower().endswith((".png", ".jpg", ".jpeg", ".pdf", ".epub")):
                    logger.info(
                        f"Skipping document with name suggesting non-notebook: {name}"
                    )
                    continue

                # If pre-filtering is enabled, first check if notebook has the pre-filter tag
                # This avoids downloading every notebook for detailed tag checking
                if pre_filter_tag:
                    # For pre-filtering, we can use "ls -l" to check document-level tags
                    # without downloading the entire notebook
                    success, stdout, _ = self.run_command("ls", "-l")
                    has_prefilter_tag = False

                    if success:
                        # Look for the notebook name in the output and check if the tag is there
                        lines = stdout.split("\n")
                        for line in lines:
                            if f"[f]\t{name}" in line or f"[f] {name}" in line:
                                # If this is the line for our notebook, check for the tag
                                # Tags are typically shown after the name in the detailed listing
                                if pre_filter_tag in line:
                                    has_prefilter_tag = True
                                    logger.info(
                                        f"Document {name} has pre-filter tag '{pre_filter_tag}'"
                                    )
                                    break

                    if not has_prefilter_tag:
                        logger.info(
                            f"Document {name} does not have pre-filter tag '{pre_filter_tag}', skipping detailed check"
                        )
                        continue

                # Get detailed metadata for this document
                has_tag, metadata = self._check_document_for_tag(doc_id, tag)

                if has_tag:
                    # Construct notebook info with rich metadata
                    notebook_info = {
                        "id": doc_id,
                        "name": name,
                        "metadata": metadata,
                        "tags": metadata.get("tags", []),
                    }

                    # Add page information if available
                    if "pages" in metadata:
                        notebook_info["pages"] = []
                        for page in metadata["pages"]:
                            page_info = {
                                "id": page.get("id"),
                                "name": page.get("visibleName", "Unnamed page"),
                                "tags": page.get("tags", []),
                            }
                            notebook_info["pages"].append(page_info)

                    tagged_notebooks.append(notebook_info)
                    logger.info(f"Found tagged notebook: {name} ({doc_id})")
                else:
                    logger.info(f"Document {name} does not have tag '{tag}'")

            # Log a summary of found notebooks
            if tagged_notebooks:
                logger.info(
                    f"Found {len(tagged_notebooks)} notebooks with tag '{tag}':"
                )
                for nb in tagged_notebooks:
                    nb_name = nb.get("name", "Unknown")
                    nb_id = nb.get("id", "Unknown")
                    logger.info(f"  - {nb_name} ({nb_id})")
            else:
                logger.warning(f"No notebooks found with tag '{tag}'")

            return tagged_notebooks

        except Exception as e:
            logger.error(f"Error finding tagged notebooks: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return []

    def _check_document_for_tag(
        self, doc_id_or_name: str, tag: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a document has the specified tag by downloading and examining its content file.

        Args:
            doc_id_or_name: Document ID or name
            tag: Tag to search for

        Returns:
            Tuple of (has_tag, metadata)
        """
        if not doc_id_or_name:
            logger.warning("Empty document ID or name provided")
            return False, {}

        # Skip files with certain extensions that are unlikely to be notebooks
        skip_extensions = (
            ".pdf",
            ".epub",
            ".html",
            ".txt",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
        )
        if isinstance(doc_id_or_name, str) and any(
            doc_id_or_name.lower().endswith(ext) for ext in skip_extensions
        ):
            logger.debug(f"Skipping non-notebook file: {doc_id_or_name}")
            return False, {}

        # Create a unique temporary directory for this operation
        temp_dir = tempfile.mkdtemp(prefix=f"remarkable_{int(time.time())}_")
        zip_path = os.path.join(temp_dir, f"{doc_id_or_name}.rmdoc")

        try:
            # Download the document by name or ID
            logger.info(f"Downloading document: {doc_id_or_name}")
            success, message = self.download_file(doc_id_or_name, zip_path, "zip")

            if not success:
                logger.warning(f"Failed to download document: {message}")
                return False, {}

            # Verify the file exists
            if not os.path.exists(zip_path):
                logger.error(
                    f"Download claimed success but file not found at {zip_path}"
                )

                # List files in temp directory to check what we actually got
                files_in_temp = os.listdir(temp_dir)
                logger.info(f"Files in temp directory: {files_in_temp}")

                # If we have any files that look like rmdoc or zip files, use the first one
                rmdoc_files = [
                    f
                    for f in files_in_temp
                    if f.endswith(".rmdoc") or f.endswith(".zip")
                ]
                if rmdoc_files:
                    actual_file = os.path.join(temp_dir, rmdoc_files[0])
                    logger.info(f"Using alternate file: {actual_file}")
                    zip_path = actual_file
                else:
                    return False, {}

            if not os.path.getsize(zip_path) > 0:
                logger.error(f"Downloaded file is empty: {zip_path}")
                return False, {}

            logger.info(
                f"Successfully downloaded document to {zip_path} ({os.path.getsize(zip_path)} bytes)"
            )

            # Check if it's a valid zip file before attempting to extract
            if not zipfile.is_zipfile(zip_path):
                logger.error(f"Downloaded file is not a valid zip file: {zip_path}")

                # Try to read the first few bytes to see what it might be
                with open(zip_path, "rb") as f:
                    header = f.read(20)
                logger.error(f"File header: {header}")

                # Try to auto-detect format and convert if needed (simple check)
                # If it's a PDF or EPUB, we can't process tags anyway
                file_type = None
                if header.startswith(b"%PDF"):
                    file_type = "PDF"
                elif header.startswith(b"PK\x03\x04"):
                    # It might be an EPUB which is also a ZIP file
                    file_type = "EPUB or ZIP"

                logger.warning(
                    f"File appears to be {file_type or 'unknown type'}, not a reMarkable notebook"
                )
                return False, {}

            # Extract the content file
            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    # Check if there are any entries in the zip file
                    if not zip_ref.namelist():
                        logger.error(f"Zip file is empty: {zip_path}")
                        return False, {}

                    # List all entries for debugging
                    logger.info(f"Zip contents: {zip_ref.namelist()}")

                    # Find all content files
                    content_files = [
                        f for f in zip_ref.namelist() if f.endswith(".content")
                    ]

                    if not content_files:
                        logger.warning(
                            f"No content file found in document {doc_id_or_name}"
                        )
                        return False, {}

                    # Extract the content file
                    content_file = content_files[0]
                    zip_ref.extract(content_file, temp_dir)
            except zipfile.BadZipFile:
                logger.error(f"Bad zip file: {zip_path}")
                return False, {}

            # Read the content file
            content_path = os.path.join(temp_dir, content_file)
            try:
                with open(content_path, "r") as f:
                    content_data = json.load(f)
            except json.JSONDecodeError as je:
                logger.error(f"Error parsing content file: {je}")
                # Try to read the raw content for debugging
                with open(content_path, "r") as f:
                    raw_content = f.read(200)  # First 200 chars
                logger.error(f"Content file start: {raw_content}")
                return False, {}
            except Exception as e:
                logger.error(f"Error reading content file: {e}")
                return False, {}

            # Check for tags in content and also in page metadata
            has_tag = False
            tags = content_data.get("tags", [])
            logger.info(f"Document {doc_id_or_name} has document-level tags: {tags}")

            # Check document-level tags
            if tag in tags:
                logger.info(f"Found exact tag match '{tag}' at document level")
                has_tag = True
            # Also check for case-insensitive match at document level
            elif any(t.lower() == tag.lower() for t in tags):
                logger.info(
                    f"Found case-insensitive tag match for '{tag}' at document level"
                )
                matching_tag = next(t for t in tags if t.lower() == tag.lower())
                logger.info(
                    f"Tag in document is '{matching_tag}', but we're looking for '{tag}'"
                )
                has_tag = True

            # Also check page-level tags
            if not has_tag and "pages" in content_data:
                for page in content_data["pages"]:
                    page_tags = page.get("tags", [])
                    page_name = page.get("visibleName", page.get("id", "Unknown"))

                    logger.info(f"Page '{page_name}' has tags: {page_tags}")

                    if tag in page_tags:
                        logger.info(
                            f"Found exact tag match '{tag}' in page '{page_name}'"
                        )
                        has_tag = True
                        break
                    # Also check for case-insensitive match
                    elif any(t.lower() == tag.lower() for t in page_tags):
                        logger.info(
                            f"Found case-insensitive tag match for '{tag}' in page '{page_name}'"
                        )
                        matching_tag = next(
                            t for t in page_tags if t.lower() == tag.lower()
                        )
                        logger.info(
                            f"Tag in page is '{matching_tag}', but we're looking for '{tag}'"
                        )
                        has_tag = True
                        break

            # Log all the tags for debugging purposes
            log_dir = os.path.join(os.path.expanduser("~"), ".claude", "logs")
            os.makedirs(log_dir, exist_ok=True)
            try:
                log_path = os.path.join(log_dir, "all_tags.txt")
                with open(log_path, "a") as log_file:
                    log_file.write(
                        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Document '{doc_id_or_name}' has document-level tags: {tags}\n"
                    )
                    if "pages" in content_data:
                        for page in content_data["pages"]:
                            page_name = page.get(
                                "visibleName", page.get("id", "Unknown")
                            )
                            page_tags = page.get("tags", [])
                            log_file.write(
                                f"  - Page '{page_name}' has tags: {page_tags}\n"
                            )
            except Exception as e:
                logger.error(f"Error writing to log file: {e}")

            return has_tag, content_data

        except Exception as e:
            logger.error(f"Error checking document for tag: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return False, {}

        finally:
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temp directory: {e}")
