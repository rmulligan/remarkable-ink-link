#!/usr/bin/env python3
"""
Examine the format of a properly created reMarkable document.

This script creates a test file, uploads it with rmapi, downloads it back,
and examines its structure to understand the proper format.
"""

import os
import sys
import json
import logging
import tempfile
import zipfile
import subprocess
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
TEST_NOTEBOOK_NAME = "TestRemarkableFormat"
RMAPI_PATH = "/home/ryan/bin/rmapi"
OUTPUT_DIR = os.path.expanduser("~/dev/rmdoc_analysis")


def create_test_file():
    """Create a simple test file and upload it with rmapi."""
    # Create a simple PDF file (rmapi only supports PDF, epub, and reMarkable formats)
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        temp_fd, test_file_path = tempfile.mkstemp(suffix=".pdf")
        os.close(temp_fd)  # Close the file descriptor as Canvas will open it

        c = canvas.Canvas(test_file_path, pagesize=letter)
        c.drawString(100, 750, "This is a test file for reMarkable format analysis.")
        c.drawString(100, 730, "Line 2 of the test file.")
        c.drawString(100, 710, "Line 3 of the test file.")
        c.save()

        logger.info(f"Created test PDF file: {test_file_path}")
        return test_file_path
    except ImportError:
        # If reportlab isn't available, try to use a sample PDF from the project
        sample_files = [
            "/home/ryan/dev/remarkable-ink-link/docs/Remarkable Pro Terminal Research.pdf",
            "/home/ryan/dev/remarkable-ink-link/handwriting_model/cursive_sample_text.pdf",
        ]

        for file_path in sample_files:
            if os.path.exists(file_path):
                temp_fd, test_file_path = tempfile.mkstemp(suffix=".pdf")
                os.close(temp_fd)  # Close the file descriptor before copying
                shutil.copy2(file_path, test_file_path)
                logger.info(f"Using sample PDF file: {file_path} -> {test_file_path}")
                return test_file_path

        logger.error("Could not create or find a PDF file to use")
        return None


def upload_test_file(test_file_path):
    """Upload the test file to reMarkable Cloud."""
    if not test_file_path or not os.path.exists(test_file_path):
        logger.error(f"Test file not found: {test_file_path}")
        return None

    try:
        # Refresh rmapi to sync with remote changes
        refresh_cmd = f"{RMAPI_PATH} refresh"
        subprocess.run(refresh_cmd, shell=True, check=True, capture_output=True)
        logger.info("Refreshed rmapi")

        # Get the base name of the file without extension
        base_name = os.path.splitext(os.path.basename(test_file_path))[0]

        # Upload the file with rmapi
        upload_cmd = f"{RMAPI_PATH} put '{test_file_path}'"
        result = subprocess.run(
            upload_cmd, shell=True, check=True, capture_output=True, text=True
        )
        logger.info(f"Upload output: {result.stdout}")

        # Refresh again to see the new file
        refresh_cmd = f"{RMAPI_PATH} refresh"
        subprocess.run(refresh_cmd, shell=True, check=True, capture_output=True)
        logger.info("Refreshed rmapi after upload")

        # List the files to find our uploaded file
        list_cmd = f"{RMAPI_PATH} ls -l"
        list_result = subprocess.run(
            list_cmd, shell=True, check=True, capture_output=True, text=True
        )

        # Find our file in the listing
        uploaded_file = None
        for line in list_result.stdout.splitlines():
            if base_name in line:
                logger.info(f"Found uploaded file in listing: {line}")
                uploaded_file = line.strip().split()[
                    -1
                ]  # Get the last column which is the name
                break

        if not uploaded_file:
            # Try using the test file name as fallback
            uploaded_file = base_name
            logger.warning(
                f"Could not find uploaded file in listing, using {uploaded_file} as fallback"
            )

        # We'll use the uploaded file name instead of renaming it
        global TEST_NOTEBOOK_NAME
        TEST_NOTEBOOK_NAME = uploaded_file
        logger.info(f"Using uploaded file name: {TEST_NOTEBOOK_NAME}")

        return TEST_NOTEBOOK_NAME

    except subprocess.CalledProcessError as e:
        logger.error(f"Error uploading test file: {e}")
        logger.error(f"Error output: {e.stderr}")
        return None

    finally:
        # Clean up the temporary file
        os.unlink(test_file_path)


def download_and_analyze():
    """Download the test notebook and analyze its structure."""
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Refresh to ensure we see the latest files
    refresh_cmd = f"{RMAPI_PATH} refresh"
    subprocess.run(refresh_cmd, shell=True, check=True, capture_output=True)
    logger.info("Refreshed rmapi before download")

    # Create a temporary directory for the download
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download the notebook
        # download_path = os.path.join(temp_dir, f"{TEST_NOTEBOOK_NAME}.zip")  # Unused variable
        download_cmd = f"{RMAPI_PATH} get '{TEST_NOTEBOOK_NAME}'"

        original_dir = os.getcwd()
        try:
            # Change to the temp directory for the download
            os.chdir(temp_dir)

            # Run download command
            result = subprocess.run(
                download_cmd, shell=True, check=True, capture_output=True, text=True
            )
            logger.info(f"Download output: {result.stdout}")

            # Check if download succeeded
            downloaded_files = os.listdir(temp_dir)
            if not downloaded_files:
                logger.error("No files downloaded")
                return False

            # Find the .rmdoc file
            rmdoc_file = None
            for file in downloaded_files:
                if file.endswith(".rmdoc"):
                    rmdoc_file = file
                    break

            if not rmdoc_file:
                logger.error("No .rmdoc file found after download")
                return False

            rmdoc_path = os.path.join(temp_dir, rmdoc_file)
            logger.info(f"Downloaded .rmdoc file: {rmdoc_path}")

            # Extract the .rmdoc file to the analysis directory
            extracted_dir = os.path.join(OUTPUT_DIR, "extracted")
            os.makedirs(extracted_dir, exist_ok=True)

            with zipfile.ZipFile(rmdoc_path, "r") as zip_ref:
                zip_ref.extractall(extracted_dir)

            # List all files in the extracted directory
            logger.info("Files in extracted directory:")
            for root, _, files in os.walk(extracted_dir):
                for file in files:
                    logger.info(f"  {os.path.join(root, file)}")

            # Copy the .rmdoc file to the output directory
            shutil.copy2(rmdoc_path, os.path.join(OUTPUT_DIR, rmdoc_file))

            # Analyze the metadata and content files
            content_files = []
            metadata_files = []

            for root, _, files in os.walk(extracted_dir):
                for file in files:
                    if file.endswith(".content"):
                        content_files.append(os.path.join(root, file))
                    elif file.endswith(".metadata"):
                        metadata_files.append(os.path.join(root, file))

            # Analyze content files
            for content_file in content_files:
                try:
                    with open(content_file, "r") as f:
                        content_data = json.load(f)

                    logger.info(f"Content file structure: {content_file}")
                    for key, value in content_data.items():
                        if isinstance(value, dict) or isinstance(value, list):
                            logger.info(
                                f"  {key}: {type(value).__name__} of length {len(value)}"
                            )
                        else:
                            logger.info(f"  {key}: {value}")

                    # Save pretty-printed content to a file
                    pretty_file = os.path.join(OUTPUT_DIR, "content_structure.json")
                    with open(pretty_file, "w") as f:
                        json.dump(content_data, f, indent=2)

                except Exception as e:
                    logger.error(f"Error analyzing content file: {e}")

            # Analyze metadata files
            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)

                    logger.info(f"Metadata file structure: {metadata_file}")
                    for key, value in metadata.items():
                        logger.info(f"  {key}: {value}")

                    # Save pretty-printed metadata to a file
                    pretty_file = os.path.join(OUTPUT_DIR, "metadata_structure.json")
                    with open(pretty_file, "w") as f:
                        json.dump(metadata, f, indent=2)

                except Exception as e:
                    logger.error(f"Error analyzing metadata file: {e}")

            logger.info(f"Analysis completed. Results saved to {OUTPUT_DIR}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Error downloading test notebook: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False

        finally:
            # Change back to the original directory
            os.chdir(original_dir)


def cleanup():
    """Delete the test notebook from reMarkable Cloud."""
    try:
        # Refresh to ensure we see the latest files
        refresh_cmd = f"{RMAPI_PATH} refresh"
        subprocess.run(refresh_cmd, shell=True, check=True, capture_output=True)
        logger.info("Refreshed rmapi before cleanup")

        delete_cmd = f"{RMAPI_PATH} rm '{TEST_NOTEBOOK_NAME}'"
        subprocess.run(delete_cmd, shell=True, check=True)
        logger.info(f"Deleted test notebook: {TEST_NOTEBOOK_NAME}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error deleting test notebook: {e}")
        return False


def main():
    """Main entry point."""
    logger.info("Step 1: Creating test file")
    test_file_path = create_test_file()
    if not test_file_path:
        logger.error("Failed to create test file")
        return 1

    logger.info("Step 2: Uploading test file")
    test_notebook = upload_test_file(test_file_path)
    if not test_notebook:
        logger.error("Failed to upload test notebook")
        return 1

    logger.info("Step 3: Downloading and analyzing file structure")
    success = download_and_analyze()
    if not success:
        logger.error("Failed to analyze notebook structure")
        return 1

    logger.info("Step 4: Cleaning up")
    cleanup()

    logger.info(f"Analysis complete. Check {OUTPUT_DIR} for results.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
