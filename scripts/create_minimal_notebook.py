#!/usr/bin/env python3
"""
Create a minimal notebook with just a single page and basic metadata.
This script attempts to upload a notebook with minimal structure.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

from inklink.config import CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
NOTEBOOK_NAME = "Minimal_Test_Notebook"


def run_rmapi_command(command, path=None):
    """Run rmapi command directly to work around upload issues."""
    rmapi_path = CONFIG.get("RMAPI_PATH", "./local-rmapi")

    base_cmd = [rmapi_path]
    if path:
        base_cmd.extend(["put", path])
    else:
        base_cmd.extend(command.split())

    try:
        logger.info(f"Running command: {' '.join(base_cmd)}")
        result = subprocess.run(
            base_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        # Log the output
        if result.stdout:
            logger.info(f"Command output: {result.stdout.strip()}")
        if result.stderr:
            logger.warning(f"Command error: {result.stderr.strip()}")

        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        logger.error(f"Error running rmapi command: {e}")
        return False, "", str(e)


def create_and_upload_minimal_notebook():
    """Create a minimal notebook with basic structure and upload it directly."""

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate unique IDs
        notebook_id = str(uuid.uuid4())
        page1_id = str(uuid.uuid4())

        # Use millisecond timestamp as a string (reMarkable format)
        now_ms = str(int(time.time() * 1000))

        # Create minimal notebook content file
        content_data = {"pages": [{"id": page1_id, "visibleName": "Test Page"}]}

        # Create content file
        content_file_path = os.path.join(temp_dir, f"{notebook_id}.content")
        with open(content_file_path, "w") as f:
            json.dump(content_data, f, indent=2)

        # Create minimal metadata file following existing examples
        metadata_path = os.path.join(temp_dir, f"{notebook_id}.metadata")
        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "lastModified": now_ms,
                    "lastOpened": now_ms,
                    "lastOpenedPage": 0,
                    "parent": "",
                    "pinned": False,
                    "synced": True,  # Must be true for uploads
                    "type": "DocumentType",
                    "visibleName": NOTEBOOK_NAME,
                },
                f,
                indent=2,
            )

        # Create notebook directory for pages
        pages_dir = os.path.join(temp_dir, notebook_id)
        os.makedirs(pages_dir, exist_ok=True)

        # Create a simple page file
        page_path = os.path.join(pages_dir, f"{page1_id}.rm")
        with open(page_path, "w") as f:
            f.write(f"This is a simple test page")

        # Create notebook zip
        notebook_path = os.path.join(temp_dir, f"{NOTEBOOK_NAME}.rmdoc")
        with zipfile.ZipFile(notebook_path, "w") as zipf:
            # Add content and metadata files
            zipf.write(content_file_path, os.path.basename(content_file_path))
            zipf.write(metadata_path, os.path.basename(metadata_path))

            # Add page files
            zipf.write(page_path, os.path.join(notebook_id, f"{page1_id}.rm"))

        # Make a debug copy of the rmdoc file
        debug_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "debug_upload"
        )
        os.makedirs(debug_dir, exist_ok=True)
        debug_copy = os.path.join(
            debug_dir, f"{NOTEBOOK_NAME}_{int(time.time())}.rmdoc"
        )
        shutil.copy2(notebook_path, debug_copy)
        logger.info(f"Created debug copy at: {debug_copy}")

        # First refresh rmapi to sync with remote state
        run_rmapi_command("refresh")

        time.sleep(1)  # Wait a moment for refresh to complete

        # Try to get a successful notebook download to analyze format
        success, stdout, stderr = run_rmapi_command("ls")
        if success:
            existing_notebooks = stdout.strip().split("\n")

            # Try to find an existing notebook to analyze
            for line in existing_notebooks:
                if "[f]" in line and not any(ext in line for ext in [".pdf", ".epub"]):
                    existing_name = line.replace("[f]", "").strip()
                    logger.info(f"Found existing notebook to analyze: {existing_name}")

                    # Download it
                    example_path = os.path.join(debug_dir, f"example_notebook.rmdoc")
                    download_cmd = f"get '{existing_name}'"
                    success, stdout, stderr = run_rmapi_command(download_cmd)

                    if success:
                        # Find the downloaded file
                        for root, dirs, files in os.walk("."):
                            for file in files:
                                if file.endswith(".rmdoc") and file != os.path.basename(
                                    notebook_path
                                ):
                                    logger.info(
                                        f"Found downloaded notebook: {os.path.join(root, file)}"
                                    )
                                    example_path = os.path.join(root, file)

                                    # Copy to debug dir and analyze
                                    shutil.copy2(
                                        example_path,
                                        os.path.join(
                                            debug_dir, "example_notebook.rmdoc"
                                        ),
                                    )

                                    # Analyze notebook
                                    try:
                                        with zipfile.ZipFile(
                                            example_path, "r"
                                        ) as zip_ref:
                                            files = zip_ref.namelist()
                                            logger.info(
                                                f"Example notebook contains: {files}"
                                            )

                                            # Extract metadata
                                            metadata_files = [
                                                f
                                                for f in files
                                                if f.endswith(".metadata")
                                            ]
                                            if metadata_files:
                                                with zip_ref.open(
                                                    metadata_files[0]
                                                ) as f:
                                                    metadata = json.load(f)
                                                    logger.info(
                                                        f"Example metadata: {json.dumps(metadata, indent=2)}"
                                                    )

                                                    # Update our metadata to match format
                                                    with open(metadata_path, "w") as f2:
                                                        # Copy format but update values
                                                        for key in metadata:
                                                            if key not in [
                                                                "visibleName",
                                                                "lastModified",
                                                                "lastOpened",
                                                            ]:
                                                                content_data[key] = (
                                                                    metadata[key]
                                                                )

                                                        # Update keys we care about
                                                        metadata["visibleName"] = (
                                                            NOTEBOOK_NAME
                                                        )
                                                        metadata["lastModified"] = (
                                                            now_ms
                                                        )
                                                        metadata["lastOpened"] = now_ms
                                                        metadata["synced"] = True

                                                        json.dump(
                                                            metadata, f2, indent=2
                                                        )
                                                        logger.info(
                                                            f"Updated metadata to match example format"
                                                        )

                                            # Re-create the zip with updated metadata
                                            with zipfile.ZipFile(
                                                notebook_path, "w"
                                            ) as zipf:
                                                zipf.write(
                                                    content_file_path,
                                                    os.path.basename(content_file_path),
                                                )
                                                zipf.write(
                                                    metadata_path,
                                                    os.path.basename(metadata_path),
                                                )
                                                zipf.write(
                                                    page_path,
                                                    os.path.join(
                                                        notebook_id, f"{page1_id}.rm"
                                                    ),
                                                )
                                    except Exception as e:
                                        logger.error(
                                            f"Error analyzing example notebook: {e}"
                                        )

                                    break

                    break

        # Upload with direct rmapi command
        success, stdout, stderr = run_rmapi_command(None, notebook_path)

        if not success:
            logger.error(f"Failed to upload notebook: {stderr}")

            # Examine the notebook to help with debugging
            logger.info(f"Examining notebook structure for debugging...")
            with zipfile.ZipFile(notebook_path, "r") as zip_ref:
                files = zip_ref.namelist()
                logger.info(f"Zip contains files: {files}")

                # Try to extract and examine metadata
                temp_extract = tempfile.mkdtemp()
                try:
                    zip_ref.extractall(temp_extract)

                    # Check metadata files
                    for file in files:
                        if file.endswith(".metadata"):
                            metadata_debug_path = os.path.join(temp_extract, file)
                            with open(metadata_debug_path, "r") as f:
                                metadata = json.load(f)
                                logger.info(
                                    f"Metadata content: {json.dumps(metadata, indent=2)}"
                                )

                        elif file.endswith(".content"):
                            content_debug_path = os.path.join(temp_extract, file)
                            with open(content_debug_path, "r") as f:
                                content = json.load(f)
                                logger.info(
                                    f"Content file content: {json.dumps(content, indent=2)}"
                                )
                except Exception as e:
                    logger.error(f"Error examining metadata: {e}")
                finally:
                    shutil.rmtree(temp_extract)

            return False
        logger.info(f"Successfully uploaded test notebook: {NOTEBOOK_NAME}")
        return True


if __name__ == "__main__":
    if create_and_upload_minimal_notebook():
        print(
            f"Successfully created and uploaded minimal test notebook '{NOTEBOOK_NAME}'"
        )
    else:
        print(f"Failed to create and upload minimal test notebook")
        sys.exit(1)
