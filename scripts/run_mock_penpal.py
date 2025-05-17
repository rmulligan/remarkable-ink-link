#!/usr/bin/env python3
"""
Mock Penpal script to process local notebooks without rmapi.
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
LILLY_ROOT_DIR = os.path.expanduser("~/dev")
LILLY_DIR = os.path.join(LILLY_ROOT_DIR, "Lilly")
NOTEBOOK_NAME = "Testing_Notebook"
QUERY_TAG = "Lilly"
CONTEXT_TAG = "Context"
SUBJECT_TAG = "Subject"
DEFAULT_SUBJECT = "Work"  # Use "Work" as the default subject for this test
USE_SUBJECT_DIRS = True


def process_notebook(notebook_dir):
    """Process a notebook directory to find pages with Lilly tag."""
    logger.info(f"Processing notebook: {notebook_dir}")

    # Check for extracted directory
    extract_dir = os.path.join(notebook_dir, "extracted")
    if not os.path.exists(extract_dir):
        logger.error(f"Extracted directory not found: {extract_dir}")
        return False

    # Find content file
    content_files = []
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(".content"):
                content_files.append(os.path.join(root, file))

    if not content_files:
        logger.error(f"No content file found in {extract_dir}")
        return False

    # Load content file
    content_file = content_files[0]
    logger.info(f"Found content file: {content_file}")

    try:
        with open(content_file, "r") as f:
            content_data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading content file: {e}")
        return False

    # Find pages with Lilly tag
    query_pages = []
    context_pages = []

    if "pages" in content_data:
        for page in content_data["pages"]:
            page_id = page.get("id")
            tags = page.get("tags", [])

            logger.info(f"Page {page_id} has tags: {tags}")

            if QUERY_TAG in tags:
                logger.info(f"Found query page with Lilly tag: {page_id}")
                query_pages.append(page)

            if CONTEXT_TAG in tags:
                logger.info(f"Found context page: {page_id}")
                context_pages.append(page)

    if not query_pages:
        logger.warning(f"No pages with Lilly tag found in notebook")
        return False

    # Process each query page
    for query_page in query_pages:
        logger.info(f"Processing query page: {query_page['id']}")

        # Generate Claude response
        claude_response = process_with_claude(query_page, context_pages)

        # Add response page to notebook
        add_response_to_notebook(
            content_data, content_file, query_page, claude_response
        )

    return True


def process_with_claude(query_page, context_pages):
    """Generate a response with Claude (mock implementation)."""
    query_id = query_page.get("id", "unknown")
    query_name = query_page.get("visibleName", "unnamed")

    # In a real implementation, this would call the Claude CLI
    # For this mock, we'll just generate a simple response
    response = f"""
# Response to {query_name}

Thank you for your query! I've processed your handwritten note tagged with #Lilly.

## What I understood
- You've created a handwritten note for testing
- You've tagged it with the Lilly tag

## My response
This is a placeholder response from Claude. In a real implementation, I would:
1. Use the Claude CLI to process your handwritten query
2. Generate a thoughtful, detailed response
3. Format it with proper markdown for readability

## Next steps
You can continue adding more pages to this notebook and tagging them with #Lilly to get more responses.

Response ID: {uuid.uuid4()}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """

    logger.info(f"Generated Claude response for page {query_id}")
    return response


def add_response_to_notebook(content_data, content_file, query_page, response_text):
    """Add a response page to the notebook."""
    # Generate a new page ID
    response_page_id = str(uuid.uuid4())
    query_id = query_page.get("id", "unknown")

    # Create response page metadata
    query_name = query_page.get("visibleName", "Query")
    now = datetime.now().isoformat()
    response_page = {
        "id": response_page_id,
        "visibleName": f"Response to {query_name}",
        "lastModified": now,
        "tags": [],
    }

    # Add response page to content
    pages = content_data.get("pages", [])

    # Find query page index
    query_idx = next((i for i, p in enumerate(pages) if p.get("id") == query_id), -1)

    if query_idx >= 0:
        # Insert response page after query page
        pages.insert(query_idx + 1, response_page)

        # Update content file
        with open(content_file, "w") as f:
            json.dump(content_data, f, indent=2)

        # Create response page file
        notebook_id = content_data.get("ID", "")
        if notebook_id:
            extract_dir = os.path.dirname(content_file)
            response_rm_file = os.path.join(
                extract_dir, notebook_id, f"{response_page_id}.rm"
            )

            # Create directory if needed
            os.makedirs(os.path.dirname(response_rm_file), exist_ok=True)

            # Write response file
            with open(response_rm_file, "w") as f:
                f.write(response_text)

            logger.info(f"Added response page {response_page_id} to notebook")
            return True

    logger.error(f"Failed to add response page to notebook")
    return False


def sanitize_name(name):
    """Sanitize a name for use as a directory name."""
    # Replace non-alphanumeric characters (except spaces, hyphens, and underscores) with underscores
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
    # Replace spaces with underscores for better directory naming
    safe_name = safe_name.replace(" ", "_")
    return safe_name


def get_notebook_directory(notebook_name, subject=None):
    """Get or create directory for a notebook with subject-based organization."""
    # Sanitize notebook name for directory use
    safe_notebook_name = sanitize_name(notebook_name)

    # Determine subject
    if subject is None:
        subject = DEFAULT_SUBJECT

    # Sanitize subject name
    safe_subject = sanitize_name(subject)

    # Create directory path based on whether we're using subject dirs
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


def setup_test_notebook():
    """Set up a test notebook with Lilly-tagged page for testing."""
    # Create directories
    os.makedirs(LILLY_DIR, exist_ok=True)

    # Get notebook directory with subject organization
    notebook_dir = get_notebook_directory(NOTEBOOK_NAME)
    extracted_dir = os.path.join(notebook_dir, "extracted")
    os.makedirs(extracted_dir, exist_ok=True)

    # Create a UUID for the notebook
    notebook_uuid = str(uuid.uuid4())

    # Create a test content file
    content_data = {
        "ID": notebook_uuid,
        "VissibleName": NOTEBOOK_NAME,
        "Type": "DocumentType",
        "tags": [f"{SUBJECT_TAG}:{DEFAULT_SUBJECT}"],
        "pages": [
            {"id": "page-1", "visibleName": "Title Page", "tags": []},
            {"id": "page-2", "visibleName": "Test Query Page", "tags": [QUERY_TAG]},
            {
                "id": "page-3",
                "visibleName": "Context Information",
                "tags": [CONTEXT_TAG],
            },
        ],
    }

    # Write content file
    content_file = os.path.join(extracted_dir, f"{notebook_uuid}.content")
    with open(content_file, "w") as f:
        json.dump(content_data, f, indent=2)

    # Create directory for pages
    pages_dir = os.path.join(extracted_dir, notebook_uuid)
    os.makedirs(pages_dir, exist_ok=True)

    # Create mock page files
    for page in content_data["pages"]:
        page_file = os.path.join(pages_dir, f"{page['id']}.rm")
        with open(page_file, "w") as f:
            f.write(f"Mock content for page {page['id']}")

    # Create a notebook file
    notebook_file = os.path.join(notebook_dir, f"{NOTEBOOK_NAME}.rmdoc")
    with open(notebook_file, "w") as f:
        f.write(f"Mock notebook file for {NOTEBOOK_NAME}")

    logger.info(f"Created test notebook at {notebook_dir}")

    return notebook_dir


def main():
    """Main entry point."""
    # Check if Lilly directory exists, create if not
    os.makedirs(LILLY_DIR, exist_ok=True)

    # Set up test notebook with subject structure
    notebook_dir = setup_test_notebook()

    # Process the test notebook
    success = process_notebook(notebook_dir)

    if success:
        logger.info(f"Successfully processed notebook: {NOTEBOOK_NAME}")
        return 0
    logger.error(f"Failed to process notebook: {NOTEBOOK_NAME}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
