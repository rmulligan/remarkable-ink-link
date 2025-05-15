#!/usr/bin/env python3
"""
Debugging script for reMarkable Cloud API issues.
This script checks the reMarkable Cloud API configuration and tries various operations.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_rmapi_command(cmd):
    """Run rmapi command and capture output."""
    rmapi_path = "/home/ryan/dev/remarkable-ink-link/local-rmapi"
    if not os.path.exists(rmapi_path):
        rmapi_path = "/home/ryan/bin/rmapi"

    try:
        logger.info(f"Running command: {rmapi_path} {cmd}")
        process = subprocess.run(
            f"{rmapi_path} {cmd}", shell=True, capture_output=True, text=True
        )

        logger.info(f"Return code: {process.returncode}")
        if process.stdout:
            logger.info(f"STDOUT: {process.stdout}")
        if process.stderr:
            logger.info(f"STDERR: {process.stderr}")

        return process.returncode == 0, process.stdout, process.stderr
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return False, "", str(e)


def check_rmapi_config():
    """Check the rmapi configuration files."""
    config_dir = os.path.expanduser("~/.config/rmapi")
    logger.info(f"Checking configuration in: {config_dir}")

    if not os.path.exists(config_dir):
        logger.warning(f"Config directory does not exist: {config_dir}")
        return

    for file in os.listdir(config_dir):
        file_path = os.path.join(config_dir, file)

        if not os.path.isfile(file_path):
            continue

        try:
            logger.info(f"Found configuration file: {file}")

            # Check if it's a JSON file
            if file.endswith(".json"):
                with open(file_path, "r") as f:
                    data = json.load(f)
                logger.info(f"Config file {file} contains valid JSON")
            else:
                # Just read it as text
                with open(file_path, "r") as f:
                    data = f.read()
                logger.info(f"Config file {file} size: {len(data)} bytes")

        except Exception as e:
            logger.error(f"Error reading config file {file}: {e}")


def test_upload_operations():
    """Test upload operations with different approaches."""
    logger.info("Testing upload operations")

    # Create a temporary test file
    tmp_dir = tempfile.mkdtemp()
    try:
        # Create a minimal test file
        test_file = os.path.join(tmp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("This is a test file for rmapi upload")

        logger.info(f"Created test file: {test_file}")

        # Try to upload with the regular put command
        logger.info("Testing basic text file upload")
        run_rmapi_command(f'put "{test_file}" "test_{int(time.time())}.txt"')

        # Create a minimal rmdoc
        rmdoc_dir = os.path.join(tmp_dir, "rmdoc")
        os.makedirs(rmdoc_dir, exist_ok=True)

        # Create unique IDs
        import uuid

        notebook_id = str(uuid.uuid4())
        page_id = str(uuid.uuid4())

        # Create a content file
        content_file = os.path.join(rmdoc_dir, f"{notebook_id}.content")
        with open(content_file, "w") as f:
            json.dump(
                {
                    "pages": [
                        {
                            "id": page_id,
                            "visibleName": "Test Page",
                            "lastModified": str(int(time.time() * 1000)),
                        }
                    ]
                },
                f,
                indent=2,
            )

        # Create a metadata file
        metadata_file = os.path.join(rmdoc_dir, f"{notebook_id}.metadata")
        with open(metadata_file, "w") as f:
            json.dump(
                {
                    "lastModified": str(int(time.time() * 1000)),
                    "lastOpened": str(int(time.time() * 1000)),
                    "lastOpenedPage": 0,
                    "parent": "",
                    "pinned": False,
                    "synced": True,
                    "type": "DocumentType",
                    "visibleName": f"Test Notebook {int(time.time())}",
                },
                f,
                indent=2,
            )

        # Create page directory
        page_dir = os.path.join(rmdoc_dir, notebook_id)
        os.makedirs(page_dir, exist_ok=True)

        # Create page file
        page_file = os.path.join(page_dir, f"{page_id}.rm")
        with open(page_file, "w") as f:
            f.write("Test content for page")

        # Create a zip file
        import zipfile

        rmdoc_file = os.path.join(tmp_dir, f"test_{int(time.time())}.rmdoc")
        with zipfile.ZipFile(rmdoc_file, "w") as zipf:
            zipf.write(content_file, os.path.basename(content_file))
            zipf.write(metadata_file, os.path.basename(metadata_file))
            zipf.write(page_file, os.path.join(notebook_id, f"{page_id}.rm"))

        logger.info(f"Created test rmdoc: {rmdoc_file}")

        # Try to upload the rmdoc
        logger.info("Testing rmdoc upload")
        run_rmapi_command(f'put "{rmdoc_file}"')

    finally:
        # Clean up
        import shutil

        shutil.rmtree(tmp_dir)


def debug_api():
    """Debug reMarkable Cloud API issues."""
    logger.info("Starting reMarkable Cloud API debugging")

    # Check rmapi version
    logger.info("Checking rmapi version")
    run_rmapi_command("version")

    # Check rmapi configuration
    check_rmapi_config()

    # Check connection to reMarkable Cloud
    logger.info("Testing connection to reMarkable Cloud")
    run_rmapi_command("ls")

    # Check if docs directory is working
    logger.info("Testing docs directory")
    run_rmapi_command("cd /")
    run_rmapi_command("ls")

    # Test download
    logger.info("Testing download with various approaches")
    with tempfile.TemporaryDirectory() as temp_dir:
        # Try getting a simple file if it exists (create one if needed)
        success, stdout, _ = run_rmapi_command("ls")

        if success:
            # Find a file that might be a document
            target = None
            for line in stdout.splitlines():
                if "[f]" in line and not any(ext in line for ext in [".pdf", ".epub"]):
                    target = line.replace("[f]", "").strip()
                    break

            if target:
                logger.info(f"Found potential target: {target}")
                run_rmapi_command(f'get "{target}"')

                # Try alternative get approach
                os.chdir(temp_dir)
                run_rmapi_command(f'get "{target}"')

    # Try putting operations
    test_upload_operations()

    logger.info("Debugging complete")


if __name__ == "__main__":
    debug_api()
