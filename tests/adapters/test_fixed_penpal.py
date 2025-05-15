#!/usr/bin/env python3
"""Test script for the fixed Claude Penpal Service.

This script executes a real penpal service response on an existing reMarkable notebook.
"""

import argparse
import logging
import os
import sys
import tempfile
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_fixed_penpal")

# Import project modules
try:
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG
    from inklink.services.claude_penpal_service import ClaudePenpalService
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG
    from inklink.services.claude_penpal_service import ClaudePenpalService


class TrackedClaudePenpalService(ClaudePenpalService):
    """A version of ClaudePenpalService that tracks its methods being called."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.method_calls = []

    def _process_with_claude(self, notebook_id, prompt, new_conversation=False):
        """Override to avoid actually calling Claude and just return a test response."""
        self.method_calls.append(("_process_with_claude", notebook_id, len(prompt)))
        return "This is a test response from Claude.\n\nThe metadata fix should work correctly now."


def main():
    """Main entry point for testing."""
    parser = argparse.ArgumentParser(description="Test fixed Claude Penpal Service")
    parser.add_argument(
        "--notebook",
        type=str,
        default="Testing Notebook",
        help="Name of notebook to test with",
    )
    parser.add_argument("--tag", type=str, default="Lilly", help="Tag to search for")
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Configure rmapi path
    rmapi_path = args.rmapi_path or CONFIG.get("RMAPI_PATH")
    if not os.path.exists(rmapi_path):
        logger.error(f"RMAPI executable not found at {rmapi_path}")
        return False

    logger.info(f"Using rmapi path: {rmapi_path}")

    # Initialize components
    rmapi_adapter = RmapiAdapter(rmapi_path)

    # Test rmapi connection
    if not rmapi_adapter.ping():
        logger.error("Failed to connect to reMarkable Cloud")
        return False

    logger.info("Successfully connected to reMarkable Cloud")

    # Create temporary directory for service
    temp_dir = tempfile.mkdtemp(prefix="penpal_test_")

    try:
        # Create tracked service
        service = TrackedClaudePenpalService(
            rmapi_path=rmapi_path,
            query_tag=args.tag,
            pre_filter_tag=None,  # No pre-filtering for test
        )

        # Find notebooks with tag
        logger.info(f"Searching for notebooks with tag: {args.tag}")

        # Get all notebooks first
        success, notebooks = rmapi_adapter.list_files()
        if not success:
            logger.error("Failed to list notebooks")
            return False

        # Filter to the specific test notebook
        test_notebook = None
        for notebook in notebooks:
            if notebook.get("VissibleName") == args.notebook:
                test_notebook = notebook
                break

        if not test_notebook:
            logger.error(f"Test notebook '{args.notebook}' not found")
            return False

        logger.info(f"Found test notebook: {args.notebook}")

        # Process notebook
        logger.info(f"Processing notebook: {args.notebook}")
        service._check_notebook_for_tagged_pages(test_notebook)

        # Report results
        if service.method_calls:
            logger.info("Service methods called:")
            for method, *args in service.method_calls:
                logger.info(f"  - {method}: {args}")
            return True
        else:
            logger.warning(
                "No service methods were called, notebook might not have tagged pages"
            )
            return False

    finally:
        # Clean up
        import shutil

        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
