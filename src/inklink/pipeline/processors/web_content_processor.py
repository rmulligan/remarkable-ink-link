"""Web content processor for InkLink.

This module provides a processor for fetching and processing web content.
"""

import logging
from typing import Dict, Any, Optional

from inklink.pipeline.processor import Processor, PipelineContext
from inklink.services.interfaces import IWebScraperService, IPDFService

logger = logging.getLogger(__name__)


class WebContentProcessor(Processor):
    """Fetches and processes web content."""

    def __init__(self, web_scraper: IWebScraperService, pdf_service: IPDFService):
        """
        Initialize with web scraper and PDF service.

        Args:
            web_scraper: Web scraper service for fetching content
            pdf_service: PDF service for handling PDFs
        """
        self.web_scraper = web_scraper
        self.pdf_service = pdf_service

    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context by fetching and processing web content.

        Args:
            context: Pipeline context with url

        Returns:
            Updated pipeline context with content
        """
        url = context.url

        # Skip if URL is not valid
        if not url or context.has_errors():
            return context

        try:
            # Check if URL is a PDF
            if self.pdf_service.is_pdf_url(url):
                return self._process_pdf(context)
            else:
                return self._process_webpage(context)

        except Exception as e:
            logger.error(f"Error processing web content: {str(e)}")
            context.add_error(
                f"Failed to process web content: {str(e)}", processor=str(self)
            )

        return context

    def _process_pdf(self, context: PipelineContext) -> PipelineContext:
        """
        Process PDF content.

        Args:
            context: Pipeline context with url

        Returns:
            Updated pipeline context with PDF content
        """
        url = context.url
        qr_path = context.get_artifact("qr_path", "")

        try:
            # Process PDF
            result = self.pdf_service.process_pdf(url, qr_path)

            if not result:
                context.add_error("Failed to process PDF", processor=str(self))
                return context

            # Add PDF result to context
            context.content = result
            context.content_type = "pdf"

            # Add PDF path to artifacts
            context.add_artifact("pdf_path", result.get("pdf_path", ""))
            context.add_artifact("title", result.get("title", url))

            logger.info(f"PDF processed: {result.get('title', url)}")

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            context.add_error(f"Failed to process PDF: {str(e)}", processor=str(self))

        return context

    def _process_webpage(self, context: PipelineContext) -> PipelineContext:
        """
        Process webpage content.

        Args:
            context: Pipeline context with url

        Returns:
            Updated pipeline context with webpage content
        """
        url = context.url

        try:
            # Scrape web content
            content = self.web_scraper.scrape(url)

            if not content:
                context.add_error(
                    f"Failed to scrape web content: {url}", processor=str(self)
                )
                return context

            # Add scraped content to context
            context.content = content
            context.content_type = "webpage"

            # Add title to artifacts
            context.add_artifact("title", content.get("title", url))

            logger.info(f"Web content processed: {content.get('title', url)}")

        except Exception as e:
            logger.error(f"Error processing webpage: {str(e)}")
            context.add_error(
                f"Failed to process webpage: {str(e)}", processor=str(self)
            )

        return context
