#!/usr/bin/env python3
"""Test Claude Penpal Service with properly structured notebook."""

import argparse
import json
import logging
import os
import sys
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_penpal_with_proper_notebook")

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


class MockClaudePenpalService(ClaudePenpalService):
    """Mock version that uses a test response instead of calling Claude."""

    def _process_with_claude(self, notebook_id, prompt, new_conversation=False):
        """Return a test response without calling Claude."""
        logger.info(f"Mock Claude call for notebook: {notebook_id}")
        return f"""Thank you for your query!

This is a test response to verify the notebook structure is working correctly.

Your prompt was: {prompt[:100]}...

The Claude Penpal Service is processing notebooks with proper tags!
"""


def main():
    """Main entry point for test."""
    parser = argparse.ArgumentParser(
        description="Test Claude Penpal Service with proper notebook"
    )
    parser.add_argument(
        "--notebook-name",
        type=str,
        default="Tagged_Test_Notebook",
        help="Notebook name to test with",
    )
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
        return 1

    logger.info(f"Using rmapi path: {rmapi_path}")

    # Initialize rmapi adapter
    rmapi_adapter = RmapiAdapter(rmapi_path)

    # Verify connection
    if not rmapi_adapter.ping():
        logger.error("Failed to connect to reMarkable Cloud")
        return 1

    logger.info("Successfully connected to reMarkable Cloud")

    # Initialize mock service
    logger.info("Initializing mock Claude Penpal Service")
    service = MockClaudePenpalService(
        rmapi_path=rmapi_path,
        query_tag="Lilly",
        pre_filter_tag="HasLilly",
    )

    # Find the notebook
    success, notebooks = rmapi_adapter.list_files()
    if not success:
        logger.error("Failed to list notebooks")
        return 1

    target_notebook = None
    for notebook in notebooks:
        if notebook.get("VissibleName") == args.notebook_name:
            target_notebook = notebook
            break

    if not target_notebook:
        logger.error(f"Notebook not found: {args.notebook_name}")
        return 1

    logger.info(
        f"Found notebook: {target_notebook.get('VissibleName')} (ID: {target_notebook.get('ID')})"
    )

    try:
        # Try to process it
        logger.info("Processing notebook for tagged pages...")
        service._check_notebook_for_tagged_pages(target_notebook)
        logger.info("✅ Successfully processed notebook")
        return 0

    except Exception as e:
        logger.error(f"Error processing notebook: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
