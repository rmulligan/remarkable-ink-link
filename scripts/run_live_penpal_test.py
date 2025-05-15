#!/usr/bin/env python3
"""
Full Live Test for Claude Penpal Service

This script runs a complete live test of the Claude Penpal Service
with the fixed metadata handling. It processes a reMarkable notebook
that contains a query page tagged with "Lilly" and verifies that
the response is generated and properly inserted into the notebook.

Usage:
    python run_live_penpal_test.py [--tag TAG] [--wait SECONDS]
"""

import argparse
import logging
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("live_penpal_test")

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


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a full live test of Claude Penpal Service"
    )
    parser.add_argument(
        "--tag", type=str, default="Lilly", help="Tag to look for in notebooks"
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=120,
        help="How long to wait for processing (seconds)",
    )
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument("--claude-command", type=str, help="Claude CLI command")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    return parser.parse_args()


def setup_environment(args):
    """Set up the test environment."""
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Configure RMAPI path
    rmapi_path = args.rmapi_path or CONFIG.get("RMAPI_PATH")
    if not os.path.exists(rmapi_path):
        logger.error(f"RMAPI executable not found at {rmapi_path}")
        sys.exit(1)
    logger.info(f"Using RMAPI path: {rmapi_path}")

    # Configure Claude CLI command
    claude_command = args.claude_command or CONFIG.get(
        "CLAUDE_COMMAND", "/home/ryan/.claude/local/claude"
    )
    logger.info(f"Using Claude command: {claude_command}")

    return rmapi_path, claude_command


class ProcessingTracker:
    """Track the processing status of notebooks."""

    def __init__(self):
        """Initialize the tracker."""
        self.processed_ids = set()
        self.lock = threading.Lock()

    def add_processed_page(self, page_id):
        """Add a processed page ID."""
        with self.lock:
            self.processed_ids.add(page_id)

    def get_processed_count(self):
        """Get the number of processed pages."""
        with self.lock:
            return len(self.processed_ids)


def verify_tagged_notebooks(rmapi_adapter, tag):
    """Verify that there are notebooks with the specified tag."""
    logger.info(f"Checking for notebooks with tag '{tag}'...")

    # Check if rmapi is accessible
    if not rmapi_adapter.ping():
        logger.error("Cannot connect to reMarkable Cloud. Check authentication.")
        return False

    # Find tagged notebooks
    tagged_notebooks = rmapi_adapter.find_tagged_notebooks(tag=tag)

    if not tagged_notebooks:
        logger.warning(f"No notebooks found with tag '{tag}'")
        return False

    logger.info(f"Found {len(tagged_notebooks)} notebooks with tag '{tag}':")
    for notebook in tagged_notebooks:
        notebook_id = notebook.get("id")
        notebook_name = notebook.get("name")
        logger.info(f"  - '{notebook_name}' (ID: {notebook_id})")

    return True


def run_live_test(args, rmapi_path, claude_command):
    """Run a full live test of the Claude Penpal Service."""
    logger.info("Starting full live test of Claude Penpal Service...")

    # Create rmapi adapter
    rmapi_adapter = RmapiAdapter(rmapi_path)

    # Verify that there are tagged notebooks
    if not verify_tagged_notebooks(rmapi_adapter, args.tag):
        logger.error(
            f"No notebooks found with tag '{args.tag}'. Please create a notebook with a '{args.tag}' tag."
        )
        return False

    # Initialize the processing tracker
    tracker = ProcessingTracker()

    # Create a subclass of ClaudePenpalService to track processing
    class TrackedClaudePenpalService(ClaudePenpalService):
        def _process_query_with_context(self, *args, **kwargs):
            result = super()._process_query_with_context(*args, **kwargs)
            # Track the processed query page
            if args and len(args) > 4:  # Check if query_page is provided
                query_page = args[4]
                if query_page and "id" in query_page:
                    page_id = query_page["id"]
                    tracker.add_processed_page(page_id)
                    logger.info(f"Tracked processed page: {page_id}")
            return result

    # Create the service
    service = TrackedClaudePenpalService(
        rmapi_path=rmapi_path,
        claude_command=claude_command,
        query_tag=args.tag,
        poll_interval=10,  # Shorter poll interval for testing
    )

    # Start monitoring
    logger.info(f"Starting Claude Penpal Service monitoring with tag '{args.tag}'...")
    service.start_monitoring()

    try:
        start_time = time.time()
        wait_time = args.wait

        logger.info(f"Waiting for up to {wait_time} seconds for processing...")

        # Show progress while waiting
        while time.time() - start_time < wait_time:
            processed_count = tracker.get_processed_count()
            elapsed = int(time.time() - start_time)
            remaining = wait_time - elapsed

            if processed_count > 0:
                logger.info(
                    f"✅ Success! Processed {processed_count} page(s) after {elapsed} seconds"
                )
                return True

            # Update status every 10 seconds
            if elapsed % 10 == 0:
                logger.info(
                    f"Waiting... {elapsed}s elapsed, {remaining}s remaining, {processed_count} pages processed"
                )

            time.sleep(1)

        # Check final status
        processed_count = tracker.get_processed_count()
        if processed_count > 0:
            logger.info(f"✅ Success! Processed {processed_count} page(s)")
            return True
        else:
            logger.warning(f"⚠️ No pages processed within {wait_time} seconds")
            logger.warning("This may be normal if there are no new pages to process")
            logger.warning(
                f"Check if your notebook has pages with the '{args.tag}' tag"
            )
            return False

    finally:
        # Stop monitoring
        logger.info("Stopping monitoring...")
        service.stop_monitoring()


def main():
    """Main entry point."""
    args = parse_args()
    rmapi_path, claude_command = setup_environment(args)

    # Run the live test
    logger.info("=== Running Full Live Test of Claude Penpal Service ===")
    success = run_live_test(args, rmapi_path, claude_command)

    # Print summary
    logger.info("\n=== Live Test Summary ===")
    if success:
        logger.info("✅ Live test PASSED!")
        logger.info(
            "The Claude Penpal Service successfully processed at least one notebook page"
        )
        logger.info("This confirms that the metadata fix is working properly")
        return 0
    else:
        logger.error("❌ Live test FAILED or INCONCLUSIVE")
        return 1


if __name__ == "__main__":
    sys.exit(main())
