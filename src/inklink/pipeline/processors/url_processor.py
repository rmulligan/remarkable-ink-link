"""URL validation processor for InkLink.

This module provides a processor for validating URLs.
"""

import logging
from typing import Dict, Any, Optional

from inklink.pipeline.processor import Processor, PipelineContext
from inklink.utils import is_safe_url

logger = logging.getLogger(__name__)


class URLProcessor(Processor):
    """Validates URLs and extracts metadata."""

    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context by validating the URL.

        Args:
            context: Pipeline context with url

        Returns:
            Updated pipeline context
        """
        url = context.url

        # Validate URL
        if not url:
            context.add_error("No URL provided", processor=str(self))
            return context

        # Check if URL is safe
        if not is_safe_url(url):
            context.add_error(f"URL is not safe: {url}", processor=str(self))
            return context

        # URL is valid, add to metadata
        context.metadata["url"] = url
        logger.info(f"URL validated: {url}")

        return context
