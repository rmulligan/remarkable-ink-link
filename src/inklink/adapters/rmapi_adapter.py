"""Remarkable API adapter for InkLink.

This module provides an adapter for interacting with the reMarkable Cloud API
via the rmapi tool, including authentication handling.
"""

import os
import subprocess
import tempfile
import time
import logging
import json
import zipfile
import shutil
import re
from typing import Optional, Tuple, List, Dict, Any, Set

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
        if self.rmapi_path and os.path.exists(self.rmapi_path) and os.access(self.rmapi_path, os.X_OK):
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
        import requests
        import stat
        
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
                            if "rmapi" in file.lower() and not file.endswith((".tar.gz", ".zip")):
                                file_path = os.path.join(root, file)
                                shutil.copy2(file_path, dest_path)
                                found = True
                                break
                        if found:
                            break
                    
                    if not found:
                        raise FileNotFoundError(f"Could not find rmapi binary in extracted files")
                
                # Make it executable
                os.chmod(dest_path, os.stat(dest_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                
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

        # Get the directory where the file will be downloaded
        output_dir = os.path.dirname(output_path)
        if not output_dir:
            output_dir = "."

        # Use 'get' to download the file to the directory
        success, stdout, stderr = self.run_command("get", doc_id_or_name, output_dir)
        if not success:
            return False, f"Failed to download: {stderr}"

        # rmapi renames files to their original name + .rmdoc
        # We need to find the downloaded file and rename it if necessary
        if doc_id_or_name.endswith('.pdf') or doc_id_or_name.endswith('.epub'):
            expected_filename = os.path.join(output_dir, doc_id_or_name)
        else:
            expected_filename = os.path.join(output_dir, f"{doc_id_or_name}.rmdoc")

        if os.path.exists(expected_filename):
            # If the file exists with the expected name, move it to the requested output path
            if expected_filename != output_path:
                os.rename(expected_filename, output_path)
            return True, f"Downloaded document {doc_id_or_name}"
        else:
            # Try to find the file in the output directory
            files = os.listdir(output_dir)
            rmdoc_files = [f for f in files if f.endswith('.rmdoc')]

            if rmdoc_files:
                # Use the first .rmdoc file found
                downloaded_file = os.path.join(output_dir, rmdoc_files[0])
                os.rename(downloaded_file, output_path)
                return True, f"Downloaded document {doc_id_or_name}"
            else:
                return False, "Download appeared successful but file not found"

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
            # Run the list command
            success, stdout, stderr = self.run_command("ls")
            if not success:
                logger.error(f"Failed to list documents: {stderr}")
                return False, []
                
            # Process the output
            documents = []
            for line in stdout.split('\n'):
                line = line.strip()
                if line and '[' in line and ']' in line:
                    # Extract ID from "[id]" in the line
                    id_match = re.search(r'\[(.*?)\]', line)
                    if id_match:
                        doc_id = id_match.group(1)
                        # Extract the file type flag (f=file, d=directory)
                        file_type = doc_id
                        
                        # Remove type prefix from name if present
                        if line.startswith('[f]') or line.startswith('[d]'):
                            name = line[3:].strip()
                        else:
                            name = line.split('[')[0].strip()
                            
                        document_type = "DocumentType"
                        
                        # Check if it's a collection (folder) or directory flag
                        if "/" in line or doc_id == 'd':
                            document_type = "CollectionType"
                            
                        documents.append({
                            "ID": name,  # Use the name as ID for better rmapi compatibility
                            "VissibleName": name,  # Using same spelling as reMarkable API
                            "Type": document_type
                        })
            
            return True, documents
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, []

    def find_tagged_notebooks(self, tag: str = "Cass") -> List[Dict[str, Any]]:
        """
        Find all notebooks that have the specified tag.

        Args:
            tag: Tag to search for, defaults to "Cass"

        Returns:
            List of dictionaries with notebook info including IDs and metadata
        """
        if not self._validate_executable():
            logger.error("rmapi path not valid")
            return []

        tagged_notebooks = []
        
        # List all documents
        success, stdout, stderr = self.run_command("ls")
        if not success:
            logger.error(f"Failed to list documents: {stderr}")
            return []
        
        try:
            # Process the text output
            documents = []
            for line in stdout.split('\n'):
                line = line.strip()
                if line and '[' in line and ']' in line:
                    # Extract ID from "[id]" in the line
                    id_match = re.search(r'\[(.*?)\]', line)
                    if id_match:
                        doc_id = id_match.group(1)
                        name = line.split('[')[0].strip()
                        documents.append({
                            "ID": doc_id,
                            "VissibleName": name,
                            "Type": "CollectionType"  # Assume all are collections
                        })
            
            # Process each document
            for doc in documents:
                # Process each document
                doc_id = doc.get("ID")
                name = doc.get("VissibleName")
                
                # Get detailed metadata for this document
                has_tag, metadata = self._check_document_for_tag(doc_id, tag)
                
                if has_tag:
                    tagged_notebooks.append({
                        "id": doc_id,
                        "name": name,
                        "metadata": metadata
                    })
                    logger.info(f"Found tagged notebook: {name} ({doc_id})")
            
            return tagged_notebooks
            
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response from rmapi")
            return []
        except Exception as e:
            logger.error(f"Error finding tagged notebooks: {str(e)}")
            return []

    def _check_document_for_tag(self, doc_id_or_name: str, tag: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a document has the specified tag by downloading and examining its content file.

        Args:
            doc_id_or_name: Document ID or name
            tag: Tag to search for

        Returns:
            Tuple of (has_tag, metadata)
        """
        # Skip files with certain extensions that are unlikely to be notebooks
        skip_extensions = ('.pdf', '.epub', '.html', '.txt', '.png', '.jpg', '.jpeg', '.gif')
        if any(doc_id_or_name.lower().endswith(ext) for ext in skip_extensions):
            logger.debug(f"Skipping non-notebook file: {doc_id_or_name}")
            return False, {}
            
        temp_dir = tempfile.mkdtemp(prefix="remarkable_")
        zip_path = os.path.join(temp_dir, f"{doc_id_or_name}.rmdoc")

        try:
            # Download the document by name or ID
            # First try by name (which is more reliable with rmapi)
            success, message = self.download_file(doc_id_or_name, zip_path, "zip")
            if not success:
                logger.warning(f"Failed to download document: {message}")
                return False, {}

            # Verify the file exists
            if not os.path.exists(zip_path):
                logger.error(f"Download claimed success but file not found at {zip_path}")
                return False, {}

            logger.info(f"Successfully downloaded document to {zip_path}")

            # Extract the content file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                content_files = [f for f in zip_ref.namelist() if f.endswith('.content')]
                if not content_files:
                    logger.warning(f"No content file found in document {doc_id_or_name}")
                    return False, {}

                # Extract the content file
                content_file = content_files[0]
                zip_ref.extract(content_file, temp_dir)

                # Read the content file
                content_path = os.path.join(temp_dir, content_file)
                with open(content_path, 'r') as f:
                    content_data = json.load(f)

                # Check if the tag exists
                tags = content_data.get('tags', [])
                logger.info(f"Document {doc_id_or_name} has tags: {tags}")

                has_tag = tag in tags

                # Also check for case-insensitive match
                if not has_tag and any(t.lower() == tag.lower() for t in tags):
                    logger.info(f"Found case-insensitive tag match for '{tag}' in document {doc_id_or_name}")
                    matching_tag = next(t for t in tags if t.lower() == tag.lower())
                    logger.info(f"Tag in document is '{matching_tag}', but we're looking for '{tag}'")

                # Write all tags to a log file for debugging
                try:
                    with open('/home/ryan/Cassidy/all_tags.txt', 'a') as log_file:
                        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Document '{doc_id_or_name}' has tags: {tags}\n")
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
            except Exception:
                pass