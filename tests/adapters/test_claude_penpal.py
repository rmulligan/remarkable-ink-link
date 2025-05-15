#!/usr/bin/env python3
"""Test script for Claude Penpal Service.

This script starts the Claude Penpal Service with the new directory structure
and pre-filtering functionality to process handwritten queries.
"""

import os
import sys
import time
import logging
import argparse
from inklink.services.claude_penpal_service import ClaudePenpalService
from inklink.config import CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Start the Claude Penpal Service with specified configuration."""
    parser = argparse.ArgumentParser(description="Run Claude Penpal Service")
    parser.add_argument("--query-tag", default="Lilly", help="Tag to identify query pages")
    parser.add_argument("--context-tag", default="Context", help="Tag to identify context pages")
    parser.add_argument("--subject-tag", default="Subject", help="Tag prefix for subject classification")
    parser.add_argument("--default-subject", default="General", help="Default subject if none specified")
    parser.add_argument("--use-subject-dirs", action="store_true", default=True, help="Organize notebooks by subject")
    parser.add_argument("--pre-filter-tag", default="HasLilly", help="Document-level tag for pre-filtering")
    parser.add_argument("--no-pre-filter", action="store_true", help="Disable pre-filtering")
    parser.add_argument("--poll-interval", type=int, default=10, help="Polling interval in seconds")
    parser.add_argument("--rmapi-path", default=None, help="Path to rmapi executable")
    
    args = parser.parse_args()
    
    # Configure the service
    service = ClaudePenpalService(
        rmapi_path=args.rmapi_path,
        query_tag=args.query_tag,
        context_tag=args.context_tag,
        subject_tag=args.subject_tag,
        default_subject=args.default_subject,
        use_subject_dirs=args.use_subject_dirs,
        pre_filter_tag=None if args.no_pre_filter else args.pre_filter_tag,
        poll_interval=args.poll_interval
    )
    
    logger.info(f"Starting Claude Penpal Service with:")
    logger.info(f"  Query tag: {args.query_tag}")
    logger.info(f"  Context tag: {args.context_tag}")
    logger.info(f"  Subject tag: {args.subject_tag}")
    logger.info(f"  Default subject: {args.default_subject}")
    logger.info(f"  Use subject dirs: {args.use_subject_dirs}")
    logger.info(f"  Pre-filter tag: {None if args.no_pre_filter else args.pre_filter_tag}")
    logger.info(f"  Poll interval: {args.poll_interval}s")
    
    try:
        # Start monitoring
        service.start_monitoring()
        
        # Keep running until Ctrl+C
        logger.info("Service running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping service...")
        service.stop_monitoring()
        logger.info("Service stopped.")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())