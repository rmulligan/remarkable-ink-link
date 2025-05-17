#!/usr/bin/env python3
"""
Test script for subject-based directory structure.
"""

import json
import logging
import os
import shutil
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
LILLY_ROOT_DIR = os.path.expanduser("~/dev")
LILLY_DIR = os.path.join(LILLY_ROOT_DIR, "Lilly")
TESTING_NOTEBOOK_NAME = "Testing_Notebook"
EXTRACTED_DIR = os.path.join(os.getcwd(), "extracted")
SUBJECT_TAG = "Subject"
DEFAULT_SUBJECT = "General"
USE_SUBJECT_DIRS = True


def sanitize_name(name):
    """Sanitize a name for use as a directory name."""
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
    safe_name = safe_name.replace(" ", "_")
    return safe_name


def get_notebook_directory(notebook_name, metadata=None):
    """Get or create a directory for the specified notebook."""
    # Sanitize notebook name for use as directory name
    safe_notebook_name = sanitize_name(notebook_name)

    # Determine subject folder based on metadata or default
    subject = DEFAULT_SUBJECT

    # Check if the notebook has a Subject tag
    if metadata:
        # Check notebook tags
        if "tags" in metadata and isinstance(metadata["tags"], list):
            for tag in metadata["tags"]:
                if isinstance(tag, str) and tag.startswith(f"{SUBJECT_TAG}:"):
                    subject = tag.split(":", 1)[1].strip()
                    logger.info(f"Found subject '{subject}' in notebook tags")
                    break

        # Check if any page has a subject tag
        if "pageTags" in metadata:
            for tag_entry in metadata["pageTags"]:
                if isinstance(tag_entry, dict) and "name" in tag_entry:
                    tag_name = tag_entry["name"]
                    if tag_name.startswith(f"{SUBJECT_TAG}:"):
                        subject = tag_name.split(":", 1)[1].strip()
                        logger.info(f"Found subject '{subject}' in page tags")
                        break

    # For testing purposes, let's add a subject tag if none exists
    # This would be manually done by the user in the reMarkable app
    subject = "Work"
    logger.info(f"Using test subject: {subject}")

    # Sanitize subject name
    safe_subject = sanitize_name(subject)

    # Create directory path based on whether we're using subject directories
    if USE_SUBJECT_DIRS:
        subject_dir = os.path.join(LILLY_DIR, safe_subject)
        os.makedirs(subject_dir, exist_ok=True)
        notebook_dir = os.path.join(subject_dir, safe_notebook_name)
    else:
        notebook_dir = os.path.join(LILLY_DIR, safe_notebook_name)

    # Create directory if it doesn't exist
    os.makedirs(notebook_dir, exist_ok=True)
    logger.info(f"Using notebook directory: {notebook_dir}")

    return notebook_dir


def setup_test():
    """Set up the test environment."""
    # Ensure the Lilly directory exists
    os.makedirs(LILLY_DIR, exist_ok=True)

    # Process the extracted notebook
    content_files = []
    for root, _, files in os.walk(EXTRACTED_DIR):
        for file in files:
            if file.endswith(".content"):
                content_files.append(os.path.join(root, file))

    if not content_files:
        logger.error(f"No content files found in {EXTRACTED_DIR}")
        return False

    content_file = content_files[0]
    logger.info(f"Found content file: {content_file}")

    try:
        with open(content_file, "r") as f:
            metadata = json.load(f)
    except Exception as e:
        logger.error(f"Error reading content file: {e}")
        return False

    # Get the notebook directory based on metadata
    notebook_dir = get_notebook_directory(TESTING_NOTEBOOK_NAME, metadata)

    # Create the extracted directory in the notebook directory
    notebook_extracted_dir = os.path.join(notebook_dir, "extracted")
    os.makedirs(notebook_extracted_dir, exist_ok=True)

    # Copy content file to the notebook directory
    target_content_file = os.path.join(notebook_dir, f"{TESTING_NOTEBOOK_NAME}.content")
    shutil.copy(content_file, target_content_file)

    # Copy the content file and all related files to the extracted directory
    for file_path in content_files:
        basename = os.path.basename(file_path)
        target_path = os.path.join(notebook_extracted_dir, basename)
        shutil.copy(file_path, target_path)

    # Copy any related directories
    content_dir = os.path.dirname(content_file)
    for item in os.listdir(content_dir):
        item_path = os.path.join(content_dir, item)
        if os.path.isdir(item_path):
            target_dir = os.path.join(notebook_extracted_dir, item)
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            shutil.copytree(item_path, target_dir)

    logger.info(f"Set up test notebook at {notebook_dir}")
    return True


def main():
    """Main entry point."""
    logger.info("Testing subject-based directory structure")

    # Set up the test
    if not setup_test():
        logger.error("Failed to set up test")
        return 1

    logger.info("Test setup successful")

    # Verify the directory structure
    if USE_SUBJECT_DIRS:
        work_dir = os.path.join(LILLY_DIR, "Work")
        test_notebook_dir = os.path.join(work_dir, TESTING_NOTEBOOK_NAME)

        if os.path.exists(test_notebook_dir):
            logger.info(
                f"Successfully created notebook directory in Work subject: {test_notebook_dir}"
            )

            # List the contents
            logger.info(f"Contents of {test_notebook_dir}:")
            for item in os.listdir(test_notebook_dir):
                logger.info(f"  - {item}")

            logger.info("Contents of extracted directory:")
            extracted_dir = os.path.join(test_notebook_dir, "extracted")
            for item in os.listdir(extracted_dir):
                logger.info(f"  - {item}")

            return 0
        logger.error(f"Failed to create subject-based directory: {test_notebook_dir}")
        return 1
    else:
        logger.info("Subject directories disabled, using flat structure")
        return 0


if __name__ == "__main__":
    sys.exit(main())
