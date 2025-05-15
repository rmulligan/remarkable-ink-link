#!/usr/bin/env python3
"""
Direct approach to download and re-upload a notebook using the rmapi CLI.
This avoids the RmapiAdapter class and works directly with the CLI.
"""

import os
import sys
import subprocess
import tempfile
import shutil
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_rmapi_command(cmd_args, cwd=None):
    """Run rmapi command directly."""
    rmapi_path = "/home/ryan/dev/remarkable-ink-link/local-rmapi"
    if not os.path.exists(rmapi_path):
        rmapi_path = os.path.expanduser("~/bin/rmapi")

    cmd = [rmapi_path] + cmd_args.split()

    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            cwd=cwd,
        )

        if result.stdout:
            logger.info(f"Command output: {result.stdout.strip()}")
        if result.stderr:
            logger.warning(f"Command error: {result.stderr.strip()}")

        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        logger.error(f"Error running rmapi command: {e}")
        return False, "", str(e)


def main():
    """Main function to download and re-upload a notebook."""
    if len(sys.argv) != 2:
        print("Usage: python download_and_reupload_direct.py <notebook_name>")
        return 1

    notebook_name = sys.argv[1]
    logger.info(f"Working with notebook: {notebook_name}")

    # List files first to confirm the notebook exists
    success, stdout, stderr = run_rmapi_command("ls")
    if not success:
        logger.error(f"Failed to list notebooks: {stderr}")
        return 1

    files = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("[f]"):
            file_name = line[3:].strip()
            files.append(file_name)

    logger.info(f"Available notebooks: {files}")

    if notebook_name not in files:
        logger.error(f"Notebook '{notebook_name}' not found in available files")
        return 1

    logger.info(f"Confirmed notebook '{notebook_name}' exists")

    # Create working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Using temporary directory: {temp_dir}")

        # Refresh rmapi first
        run_rmapi_command("refresh")

        # Download the notebook
        success, stdout, stderr = run_rmapi_command(
            f'get "{notebook_name}"', cwd=temp_dir
        )

        if not success:
            logger.error(f"Failed to download notebook: {stderr}")
            return 1

        # Check what files were downloaded
        files = os.listdir(temp_dir)
        if not files:
            logger.error("No files were downloaded")
            return 1

        logger.info(f"Downloaded files: {files}")

        # Find the downloaded rmdoc file
        rmdoc_file = None
        for file in files:
            if file.endswith(".rmdoc"):
                rmdoc_file = file
                break

        if not rmdoc_file:
            logger.error("No .rmdoc file found in downloaded files")
            return 1

        logger.info(f"Found rmdoc file: {rmdoc_file}")

        # Make a debug copy to analyze
        debug_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "debug_upload"
        )
        os.makedirs(debug_dir, exist_ok=True)
        debug_copy = os.path.join(debug_dir, f"debug_download_{int(time.time())}.rmdoc")
        shutil.copy2(os.path.join(temp_dir, rmdoc_file), debug_copy)
        logger.info(f"Created debug copy at: {debug_copy}")

        # Create a modified output name
        timestamp = int(time.time())
        modified_name = f"{notebook_name}_Modified_{timestamp}"

        # Refresh again before upload
        run_rmapi_command("refresh")

        time.sleep(1)  # Wait a moment for refresh to complete

        # Upload the file with a new name
        upload_path = os.path.join(temp_dir, rmdoc_file)
        success, stdout, stderr = run_rmapi_command(f'put "{upload_path}"')

        if not success:
            logger.error(f"Failed to upload notebook: {stderr}")
            return 1

        # Try to find the ID of the uploaded document
        doc_id = None
        for line in stdout.splitlines():
            if "ID:" in line:
                parts = line.split("ID:")
                if len(parts) > 1:
                    doc_id = parts[1].strip()
                    break

        if doc_id:
            # Rename the uploaded document
            success, stdout, stderr = run_rmapi_command(
                f'mv "{doc_id}" "{modified_name}"'
            )
            if success:
                logger.info(
                    f"Successfully renamed uploaded notebook to {modified_name}"
                )
            else:
                logger.warning(f"Failed to rename uploaded notebook: {stderr}")

        logger.info("Successfully completed download-upload cycle")
        return 0


if __name__ == "__main__":
    sys.exit(main())
