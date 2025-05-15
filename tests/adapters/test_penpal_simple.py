#!/usr/bin/env python3
"""Simple test of Claude Penpal Service without tagging."""

import os
import sys
import time
import logging
import json
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_penpal_simple")

# Import project modules
try:
    from inklink.config import CONFIG
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.services.claude_penpal_service import ClaudePenpalService
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.config import CONFIG
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.services.claude_penpal_service import ClaudePenpalService

class MockClaudePenpalService(ClaudePenpalService):
    """Mock version that uses a test response instead of calling Claude."""
    
    def _process_with_claude(self, notebook_id, prompt, new_conversation=False):
        """Return a test response without calling Claude."""
        logger.info(f"Mock Claude call for notebook: {notebook_id}")
        return f"""Thank you for your query!

This is a test response to verify the notebook upload process works correctly.

Your prompt was: {prompt[:100]}...

The Claude Penpal Service is working correctly!
"""

def main():
    """Main entry point for simple test."""
    parser = argparse.ArgumentParser(description="Simple test for Claude Penpal Service")
    parser.add_argument("--notebook-id", type=str, required=True, help="Notebook ID to test with")
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
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
        query_tag="Test",  # simplified tag
        pre_filter_tag="Test",  # simplified tag
    )
    
    # Test processing a query
    logger.info(f"Testing Claude processing for notebook: {args.notebook_id}")
    response = service._process_with_claude(args.notebook_id, "This is a test query")
    logger.info(f"Got response: {response[:100]}...")
    
    # Now test the upload process
    logger.info("Testing notebook modification and upload...")
    
    # First get notebook info
    success, notebooks = rmapi_adapter.list_files()
    if not success:
        logger.error("Failed to list notebooks")
        return 1
        
    target_notebook = None
    for notebook in notebooks:
        if notebook.get("ID") == args.notebook_id:
            target_notebook = notebook
            break
            
    if not target_notebook:
        logger.error(f"Notebook not found: {args.notebook_id}")
        return 1
        
    logger.info(f"Found notebook: {target_notebook.get('VissibleName')} (ID: {args.notebook_id})")
    
    try:
        # Try to process it
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