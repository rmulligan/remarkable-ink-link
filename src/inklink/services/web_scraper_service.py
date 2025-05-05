"""Web scraping service that tries multiple methods."""

import logging
from typing import Dict, Any
import requests
from bs4 import BeautifulSoup

try:
    from readability import Document
except ImportError:
    Document = None

# Import utility functions for HTML parsing and error handling
from inklink.utils import (
    retry_operation,
    format_error,
    extract_structured_content,
    validate_and_fix_content
)

logger = logging.getLogger(__name__)


class WebScraperService:
    """Web scraping service to extract structured content from URLs."""

    def __init__(self):
        """Initialize scraper."""
        pass

    def scrape(self, url: str) -> Dict[str, Any]:
        """Fetch URL and extract title and structured content.
        
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
        try:
            html_content = self._fetch_url(url)
        except Exception as e:
            error_msg = format_error("network", f"Failed to fetch URL {url}", e)
            logger.error(error_msg)
            return {
                "title": url,
                "structured_content": [
                    {
                        "type": "paragraph",
                        "content": f"Could not fetch content from {url}: {e}",
                    }
                ],
                "images": [],
            }
        
        # Try different extraction methods
        if Document:
            try:
                # Use Mozilla Readability to get clean article content
                doc = Document(html_content)
                content_html = doc.summary()
                
                # Extract structured content from the cleaned HTML
                content = extract_structured_content(content_html, url)
                
                # If Readability found a title, use it
                doc_title = doc.short_title()
                if doc_title and doc_title.strip():
                    content["title"] = doc_title.strip()
                
                # Validate and fix content
                return validate_and_fix_content(content, url)
            except Exception as e:
                logger.warning(f"Readability extraction failed: {e}, falling back to direct parsing")
                # Fall through to direct parsing
        
        # Direct parsing of raw HTML
        try:
            content = extract_structured_content(html_content, url)
            return validate_and_fix_content(content, url)
        except Exception as e:
            error_msg = format_error("parsing", f"Failed to parse HTML from {url}", e)
            logger.error(error_msg)
            return {
                "title": url,
                "structured_content": [
                    {
                        "type": "paragraph",
                        "content": f"Could not extract content from {url}: {e}",
                    }
                ],
                "images": [],
            }

    def _fetch_url(self, url: str) -> str:
        """Fetch URL and return its HTML content.
        
        Uses retry logic for resilience against temporary network failures.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as a string
            
        Raises:
            Exception: If fetching fails after retries
        """
        def fetch_with_headers(url_to_fetch):
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            response = requests.get(url_to_fetch, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        
        return retry_operation(
            fetch_with_headers, 
            url, 
            operation_name="URL fetching",
            max_retries=3
        )