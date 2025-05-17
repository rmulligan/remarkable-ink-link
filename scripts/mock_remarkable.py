#!/usr/bin/env python3
"""
Mock implementation for testing the Remarkable Service.

This module provides a temporary mock that overrides the RemarkableService
initialization in the container.py file to allow the application to start
for testing purposes.
"""

import importlib
import inspect
import logging
import os
import sys
from functools import wraps
from unittest.mock import MagicMock

# Add the project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.inklink.adapters.rmapi_adapter import RmapiAdapter  # noqa: E402
from src.inklink.services.remarkable_service import RemarkableService  # noqa: E402

logger = logging.getLogger(__name__)

# Path to the container module
CONTAINER_PATH = "src.inklink.di.container"


# Mock the RmapiAdapter class
class MockRmapiAdapter:
    """Mock implementation of RmapiAdapter for testing."""

    def __init__(self, *args, **kwargs):
        logger.info("Created MockRmapiAdapter")

    def ping(self):
        """Mock ping method."""
        return True

    @staticmethod
    def upload(self, *args, **kwargs):
        """Mock upload method."""
        return True, "Mock upload successful"


# Patch the Container.create_provider method
def patch_container():
    """Patch the Container.create_provider method to use mock services."""
    try:
        # Import the container module
        container_module = importlib.import_module(CONTAINER_PATH)
        Container = container_module.Container

        # Store the original method
        original_create_provider = Container.create_provider

        @wraps(original_create_provider)
        def patched_create_provider(cls, config=None):
            """Patched version of create_provider that uses mock services."""
            provider = original_create_provider(cls, config)

            # Create mock RmapiAdapter
            mock_rmapi = MockRmapiAdapter()

            # Register mock RmapiAdapter
            provider.register_factory(RmapiAdapter, lambda: mock_rmapi)

            # Register mock RemarkableService with the mock adapter
            provider.register_factory(
                RemarkableService, lambda: RemarkableService(adapter=mock_rmapi)
            )

            logger.info("Successfully patched container with mock RemarkableService")
            return provider

        # Replace the original method with our patched version
        Container.create_provider = classmethod(patched_create_provider)
        logger.info("Successfully monkey-patched Container.create_provider")

        return True
    except Exception as e:
        logger.error(f"Failed to patch container: {e}")
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Patch the container
    patch_success = patch_container()
    print(f"Patch {'succeeded' if patch_success else 'failed'}")

    # If successful, import and run the app
    if patch_success:
        from src.inklink.main import server

        server("127.0.0.1", 9999)
