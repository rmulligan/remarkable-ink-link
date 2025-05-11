"""Web scraping service that tries multiple methods."""

import logging
from typing import Dict, Any, Optional, Tuple

from inklink.services.interfaces import IWebScraperService
from inklink.adapters.http_adapter import HTTPAdapter

try:
    from readability import Document
except ImportError:
    Document = None

# Import utility functions for HTML parsing and error handling
from inklink.utils import (
    format_error,
    extract_structured_content,
    validate_and_fix_content,
)

logger = logging.getLogger(__name__)


class WebScraperService(IWebScraperService):
    """Web scraping service to extract structured content from URLs."""

    def __init__(self, http_adapter: Optional[HTTPAdapter] = None):
        """
        Initialize web scraper service.

        Args:
            http_adapter: Optional HTTP adapter for making requests
        """
        # Create a new HTTP adapter if one wasn't provided
        self.adapter = http_adapter or HTTPAdapter(timeout=15, retries=3)

        # Configure standard browser headers for the adapter
        self.adapter.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def scrape(self, url: str) -> Dict[str, Any]:
        """
        Fetch URL and extract title and structured content.

        This method attempts to extract structured content in the following order:
        1. Try Mozilla Readability for reader-mode extraction if available
        2. Fall back to direct BeautifulSoup processing of raw HTML
        3. Return a standardized content structure with title and content

        Args:
            url: The URL to scrape

        Returns:
            Dict with title, structured_content, and images
        """
        logger.info(f"Scraping URL: {url}")

        # Fetch the URL content
        logger.debug("Fetching URL content")
        try:
            success, html_content = self._fetch_url(url)

            if not success:
                error_msg = f"Failed to fetch URL: {html_content}"
                logger.error(error_msg)
                return self._build_error_response(
                    url, f"Could not fetch content: {html_content}"
                )

            logger.debug("URL content fetched successfully")

        except Exception as e:
            error_msg = format_error("network", f"Failed to fetch URL {url}", e)
            logger.error(error_msg)
            return self._build_error_response(url, f"Could not fetch content: {str(e)}")

        # Try different extraction methods
        if Document:
            try:
                logger.debug("Using Mozilla Readability for extraction")
                # Use Mozilla Readability to get clean article content
                doc = Document(html_content)
                content_html = doc.summary()
                logger.debug("Mozilla Readability extraction completed")

                # Extract structured content from the cleaned HTML
                content = extract_structured_content(content_html, url)

                # If Readability found a title, use it
                doc_title = doc.short_title()
                if doc_title and doc_title.strip():
                    content["title"] = doc_title.strip()

                # Validate and fix content
                return validate_and_fix_content(content, url)
            except Exception as e:
                logger.warning(
                    f"Readability extraction failed: {e}, falling back to direct parsing"
                )
                # Fall through to direct parsing

        # Direct parsing of raw HTML
        try:
            content = extract_structured_content(html_content, url)
            return validate_and_fix_content(content, url)
        except Exception as e:
            error_msg = format_error("parsing", f"Failed to parse HTML from {url}", e)
            logger.error(error_msg)
            return self._build_error_response(
                url, f"Could not extract content: {str(e)}"
            )

    def _fetch_url(self, url: str) -> Tuple[bool, str]:
        """
        Fetch URL and return its HTML content using the HTTP adapter.

        Args:
            url: The URL to fetch

        Returns:
            Tuple of (success, content_or_error)
        """
        # Use the HTTP adapter to get the content
        # The adapter handles retries, timeouts, and error handling
        success, response = self.adapter.get(url)

        return success, response

    def _build_error_response(self, url: str, error_message: str) -> Dict[str, Any]:
        """
        Build a standardized error response.

        Args:
            url: The URL that was being scraped
            error_message: The error message

        Returns:
            Structured content dictionary with error information
        """
        return {
            "title": url,
            "structured_content": [
                {
                    "type": "paragraph",
                    "content": f"{error_message}",
                }
            ],
            "images": [],
        }