"""Web scraping service that tries multiple methods."""

import logging
from typing import Dict, Any, Tuple, List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

try:
    from readability import Document
except ImportError:
    Document = None

# Import utility functions for error handling
from inklink.utils import retry_operation, format_error, parse_html_container

logger = logging.getLogger(__name__)


class WebScraperService:
    """Simple web scraping service using requests and BeautifulSoup."""

    def __init__(self):
        """Initialize scraper."""
        pass

    def scrape(self, url: str) -> Dict[str, Any]:
        """Fetch URL and extract title and structured content."""
        logger.info(f"Scraping URL: {url}")
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
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
        soup = BeautifulSoup(resp.text, "html.parser")
        # Initial title extraction
        title = None
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            title = og["content"].strip()
        if not title and soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not title:
            title = url
            
        # Attempt reader mode extraction with Mozilla Readability if available
        # Fallback to simple BeautifulSoup parsing
        if Document:
            try:
                doc = Document(resp.text)
                doc_title = doc.short_title()
                if doc_title and doc_title.strip():
                    title = doc_title.strip()
                content_html = doc.summary()
                container = BeautifulSoup(content_html, 'html.parser')
            except Exception as e:
                logger.warning(f"Readability extraction failed: {e}")
                container = soup.body or soup
        else:
            container = soup.body or soup

        structured = []
        images = []
        if container:
            for tag in container.find_all(['h1','h2','h3','h4','h5','h6','p','ul','ol','pre','img']):
                name = tag.name.lower()
                if name == 'img':
                    src = tag.get('src') or ''
                    if src:
                        img_url = urljoin(url, src)
                        alt = tag.get('alt', '').strip()
                        images.append({"url": img_url, "caption": alt})
                        structured.append({"type": "image", "url": img_url, "caption": alt})
                elif name in ['h1','h2','h3','h4','h5','h6']:
                    structured.append({"type": name, "content": tag.get_text(strip=True)})
                elif name == 'p':
                    text = tag.get_text(strip=True)
                    if text:
                        structured.append({"type": "paragraph", "content": text})
                elif name in ['ul','ol']:
                    items = [li.get_text(strip=True) for li in tag.find_all('li') if li.get_text(strip=True)]
                    if items:
                        structured.append({"type": "list", "items": items})
                elif name == 'pre':
                    code = tag.get_text()
                    if code:
                        structured.append({"type": "code", "content": code})
        # Fallback to raw text if nothing extracted
        if not structured:
            text = soup.get_text(separator=' ', strip=True)
            structured.append({"type": "paragraph", "content": text})

        return {"title": title, "structured_content": structured, "images": images}
    
    def _extract_title_directly(self, url: str) -> str:
        """Extract title directly from URL using requests and BeautifulSoup.

        Args:
            url: The URL to extract title from

        Returns:
            Extracted title or empty string if failed
        """
        try:
            # Define the fetch operation as a separate function for retry
            def fetch_url(url_to_fetch):
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                return requests.get(url_to_fetch, headers=headers, timeout=10)

            # Use retry operation for fetching the URL
            try:
                response = retry_operation(
                    fetch_url, url, operation_name="URL title extraction"
                )
                soup = BeautifulSoup(response.text, "html.parser")
            except Exception as e:
                logger.warning(
                    format_error(
                        "network", "Failed to fetch page for title extraction", e
                    )
                )
                return ""

            # Try to get title from various elements
            title = None

            # Try standard title tag
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            # Try OpenGraph title which is often better
            if not title or len(title) < 3:
                og_title = soup.find("meta", property="og:title")
                if og_title and og_title.get("content"):
                    title = og_title["content"].strip()

            # Try Twitter title
            if not title or len(title) < 3:
                twitter_title = soup.find("meta", property="twitter:title")
                if twitter_title and twitter_title.get("content"):
                    title = twitter_title["content"].strip()

            # Try h1 if no title found
            if not title or len(title) < 3:
                h1 = soup.find("h1")
                if h1:
                    title = h1.get_text(strip=True)

            # If the title is too long, truncate it
            if title and len(title) > 100:
                title = title[:97] + "..."

            # Clean the title
            if title:
                title = title.replace("\n", " ").replace("\r", "").strip()

            return title or self._generate_title_from_url(url)

        except Exception as e:
            logger.warning(f"Error extracting title directly: {e}")
            return self._generate_title_from_url(url)

    def _generate_title_from_url(self, url: str) -> str:
        """Generate a title from URL if no title can be extracted.

        Args:
            url: The URL to generate title from

        Returns:
            Generated title
        """
        try:
            parsed_url = urlparse(url)

            # Use domain as base
            domain = parsed_url.netloc.replace("www.", "")

            # Try to use path segments
            path = parsed_url.path
            if path and path not in ("/", ""):
                # Remove trailing slash
                if path.endswith("/"):
                    path = path[:-1]

                # Get last path segment
                segments = path.split("/")
                page = segments[-1] if segments else ""

                if page:
                    # Convert slug to title
                    page = page.replace("-", " ").replace("_", " ")
                    page = " ".join(word.capitalize() for word in page.split())

                    # Remove file extension if present
                    if "." in page:
                        page = page.split(".")[0]

                    return f"{page} - {domain}"

            # Fallback to just the domain
            return f"Page from {domain}"

        except Exception as e:
            logger.warning(f"Error generating title from URL: {e}")
            return "Web Page"

    def _validate_and_fix_content(self, content: Dict, url: str) -> Dict:
        """Validate and fix content structure.

        Args:
            content: The content to validate and fix
            url: The source URL

        Returns:
            Fixed content
        """
        # Ensure title exists and is not empty
        if not content.get("title") or len(content.get("title", "").strip()) < 2:
            content["title"] = self._generate_title_from_url(url)

        # Ensure content is not empty
        if (
            not content.get("structured_content")
            or len(content.get("structured_content", [])) == 0
        ):
            content["structured_content"] = [
                {
                    "type": "paragraph",
                    "content": f"This is a page from {url}. Content could not be properly extracted.",
                }
            ]

        # Convert legacy formats
        structured_content = content.get("structured_content", [])
        for i, item in enumerate(structured_content):
            # Handle list items format conversion
            if item.get("type") == "list" and "items" in item:
                list_items = item.pop("items", [])
                for j, list_item in enumerate(list_items):
                    structured_content.insert(
                        i + j + 1, {"type": "bullet", "content": list_item}
                    )

        # Ensure images list exists
        if "images" not in content:
            content["images"] = []

        return content
