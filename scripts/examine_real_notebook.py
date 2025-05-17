#!/usr/bin/env python3
"""
Download and examine a real notebook from reMarkable Cloud.
This script will help us understand the correct structure.
"""

import json
import logging
import os
import subprocess
import zipfile

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def download_and_examine(notebook_name="Question Box"):
    """Download a real notebook and examine its structure."""

    rmapi_path = "/home/ryan/dev/remarkable-ink-link/local-rmapi"

    # Create local temp directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(project_dir, "temp_examine")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Change to temp directory
        os.chdir(temp_dir)

        # Download the notebook
        logger.info(f"Downloading notebook: {notebook_name}")
        cmd = f'{rmapi_path} get "{notebook_name}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Failed to download: {result.stderr}")
            return

        logger.info(f"Download output: {result.stdout}")

        # Find the downloaded file
        downloaded_files = os.listdir(temp_dir)
        rmdoc_file = None

        for file in downloaded_files:
            if file.endswith(".rmdoc"):
                rmdoc_file = file
                break

        if not rmdoc_file:
            logger.error("No .rmdoc file found after download")
            return

        logger.info(f"Found downloaded file: {rmdoc_file}")

        # Extract and examine the notebook
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(rmdoc_file, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        logger.info(f"Extracted files: {os.listdir(extract_dir)}")

        # Examine each file
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, extract_dir)
                logger.info(f"\n--- Examining file: {rel_path} ---")

                # Get file size
                file_size = os.path.getsize(file_path)
                logger.info(f"Size: {file_size} bytes")

                # If it's a JSON file, show its content
                if file.endswith((".metadata", ".content")):
                    try:
                        with open(file_path, "r") as f:
                            content = json.load(f)
                        logger.info(f"JSON content:\n{json.dumps(content, indent=2)}")
                    except Exception as e:
                        logger.error(f"Error reading JSON: {e}")

                        # Read first few bytes
                        with open(file_path, "rb") as f:
                            header = f.read(50)
                        logger.info(f"File header (hex): {header.hex()}")

                # For .rm files, show first few bytes
                elif file.endswith(".rm"):
                    with open(file_path, "rb") as f:
                        header = f.read(50)
                    logger.info(f"RM file header (hex): {header.hex()}")

        # Copy the notebook to debug directory for further analysis
        debug_dir = os.path.join(project_dir, "debug_upload")
        import shutil

        debug_copy = os.path.join(
            debug_dir, f"real_{notebook_name.replace(' ', '_')}.rmdoc"
        )
        shutil.copy2(rmdoc_file, debug_copy)
        logger.info(f"Copied to debug directory: {debug_copy}")

    finally:
        # Clean up
        os.chdir(project_dir)

        # Keep the temp directory for now for further inspection
        logger.info(f"Temporary files kept in: {temp_dir}")


if __name__ == "__main__":
    download_and_examine()
