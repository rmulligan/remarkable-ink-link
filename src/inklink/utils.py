"""Utility functions for Pi Share Receiver."""

import time
import logging
from typing import Any, Callable, TypeVar, Optional, Tuple, List, Dict
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

# Import configuration with proper relative import
try:
    from .config import CONFIG

    MAX_RETRIES = CONFIG.get("MAX_RETRIES", 3)
    RETRY_DELAY = CONFIG.get("RETRY_DELAY", 2)
except ImportError:
    # Fallback to defaults if import fails
    MAX_RETRIES = 3
    RETRY_DELAY = 2

# Set up logger
logger = logging.getLogger(__name__)

# Generic type for function return
T = TypeVar("T")


def retry_operation(
    operation: Callable[..., T],
    *args,
    max_retries: Optional[int] = None,
    retry_delay: Optional[int] = None,
    operation_name: str = "Operation",
    **kwargs,
) -> T:
    """Retry an operation with exponential backoff.

    Args:
        operation: Function to retry
        args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts (default: from config)
        retry_delay: Base delay between retries in seconds (default: from config)
        operation_name: Name of the operation for logging
        kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the operation if successful

    Raises:
        Exception: If the operation fails after all retries
    """
    retries = 0
    last_error = None

    # Use provided values or defaults from config
    max_retries = max_retries if max_retries is not None else MAX_RETRIES
    retry_delay = retry_delay if retry_delay is not None else RETRY_DELAY

    while retries <= max_retries:
        try:
            if retries > 0:
                logger.info(
                    f"{operation_name}: Retry attempt {retries}/{max_retries}..."
                )
            return operation(*args, **kwargs)
        except Exception as e:
            last_error = e
            retries += 1
            if retries <= max_retries:
                sleep_time = retry_delay * (2 ** (retries - 1))  # Exponential backoff
                logger.warning(
                    f"{operation_name} failed: {str(e)}. Retrying in {sleep_time} seconds..."
                )
                time.sleep(sleep_time)
            else:
                logger.error(
                    f"{operation_name} failed after {max_retries} retries: {str(e)}"
                )
                raise last_error


def format_error(error_type: str, message: str, details: Any = None) -> str:
    """Format error messages consistently.

    Args:
        error_type: Type of error (e.g., "network", "conversion")
        message: Error message
        details: Additional error details (optional)

    Returns:
        Formatted error message
    """
    error_msg = f"{error_type.upper()} ERROR: {message}"

    if details:
        if isinstance(details, Exception):
            error_msg += f" ({type(details).__name__}: {str(details)})"
        else:
            error_msg += f" ({details})"

    return error_msg


# Enhanced HTML parsing utilities


def extract_title_from_html(
    soup: BeautifulSoup, url: Optional[str] = None, max_length: int = 100
) -> str:
    """Extract title from HTML BeautifulSoup object.
    
    Tries multiple sources in priority order:
    1. OpenGraph meta title
    2. Twitter card meta title 
    3. Standard title tag
    4. First h1 element
    5. If nothing found, generate from URL or use fallback
    
    Args:
        soup: BeautifulSoup object containing HTML
        url: Optional URL for fallback title generation
        max_length: Maximum allowed title length
        
    Returns:
        Extracted title string
    """
    title = None
    
    # Try OpenGraph title (usually best quality)
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    
    # Try Twitter title
    if not title or len(title) < 3:
        twitter_title = soup.find("meta", property="twitter:title")
        if twitter_title and twitter_title.get("content"):
            title = twitter_title["content"].strip()
    
    # Try standard title tag
    if not title or len(title) < 3:
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
    
    # Try h1 if no title found
    if not title or len(title) < 3:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    
    # Clean and limit length
    if title:
        # Clean the title
        title = title.replace("\n", " ").replace("\r", "").strip()
        
        # Truncate if too long
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
    
    # Generate from URL if still empty and URL provided
    if (not title or len(title) < 2) and url:
        title = generate_title_from_url(url)
    
    return title or "Untitled Document"


def generate_title_from_url(url: str) -> str:
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


def find_main_content_container(soup: BeautifulSoup) -> Tag:
    """Find the main content container in an HTML document.
    
    Attempts to identify the primary content area by looking for semantic
    elements in order of likelihood to contain main content.
    
    Args:
        soup: BeautifulSoup object of the HTML document
        
    Returns:
        BeautifulSoup Tag containing the main content
    """
    # Try common content containers in order of specificity
    container_selectors = [
        "main", 
        "article",
        "#content",
        ".content",
        "#main",
        ".main", 
        "section",
        ".post-content",
        ".entry-content",
    ]
    
    for selector in container_selectors:
        if selector.startswith("#") or selector.startswith("."):
            container = soup.select_one(selector)
        else:
            container = soup.find(selector)
            
        if container and len(container.get_text(strip=True)) > 100:
            return container
    
    # Fallback to body or entire document
    return soup.body or soup


def parse_html_container(
    container: BeautifulSoup, base_url: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Parse a BeautifulSoup container to structured content and images.
    
    Extracts headings, paragraphs, lists, code blocks and images from
    an HTML container, converting them to a structured format suitable
    for document generation.
    
    Args:
        container: BeautifulSoup container to parse
        base_url: Optional base URL for resolving relative links
        
    Returns:
        Tuple of (structured_content, images)
        structured_content: List of dicts with type and content
        images: List of dicts with url and caption
    """
    structured: List[Dict[str, Any]] = []
    images: List[Dict[str, str]] = []
    
    # Skip if container is None
    if not container:
        return structured, images
    
    for tag in container.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "pre", "img"]
    ):
        name = tag.name.lower()
        if name == "img":
            src = tag.get("src", "") or ""
            if src:
                img_url = urljoin(base_url, src) if base_url else src
                alt = tag.get("alt", "").strip()
                
                # Avoid duplicates in images list
                if not any(img["url"] == img_url for img in images):
                    images.append({"url": img_url, "caption": alt})
                    
                structured.append({"type": "image", "url": img_url, "caption": alt})
        elif name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            text = tag.get_text(strip=True)
            if text:  # Only add non-empty headings
                structured.append({"type": name, "content": text})
        elif name == "p":
            text = tag.get_text(strip=True)
            if text:  # Only add non-empty paragraphs
                structured.append({"type": "paragraph", "content": text})
        elif name in ["ul", "ol"]:
            items = [
                li.get_text(strip=True)
                for li in tag.find_all("li")
                if li.get_text(strip=True)
            ]
            if items:  # Only add non-empty lists
                structured.append({"type": "list", "items": items})
        elif name == "pre":
            code = tag.get_text()
            if code:  # Only add non-empty code blocks
                structured.append({"type": "code", "content": code})
    
    # Fallback to plain text if nothing extracted
    if not structured:
        text = container.get_text(separator=" ", strip=True)
        if text:
            structured.append({"type": "paragraph", "content": text})
            
    return structured, images


def extract_structured_content(
    html_content: str, base_url: Optional[str] = None
) -> Dict[str, Any]:
    """Extract structured content from HTML.
    
    Comprehensive function that performs:
    1. HTML parsing with BeautifulSoup
    2. Title extraction
    3. Main content identification
    4. Structured content extraction
    5. Image collection
    
    Args:
        html_content: HTML string to parse
        base_url: Optional base URL for resolving relative links
        
    Returns:
        Dict with keys:
        - title: Extracted document title
        - structured_content: List of structured content blocks
        - images: List of image information
    """
    try:
        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract title
        title = extract_title_from_html(soup, base_url)
        
        # Find main content container
        container = find_main_content_container(soup)
        
        # Parse container for structured content
        structured_content, images = parse_html_container(container, base_url)
        
        return {
            "title": title,
            "structured_content": structured_content,
            "images": images
        }
    except Exception as e:
        logger.error(f"Error extracting structured content: {e}")
        fallback_title = base_url or "Unknown Document"
        return {
            "title": fallback_title,
            "structured_content": [
                {
                    "type": "paragraph",
                    "content": f"Error extracting content: {str(e)}",
                }
            ],
            "images": [],
        }


def validate_and_fix_content(content: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Validate and fix content structure.
    
    Ensures content has proper structure and values:
    1. Ensures title exists
    2. Ensures structured_content is not empty
    3. Ensures images list exists
    4. Converts legacy formats to current format
    
    Args:
        content: The content to validate and fix
        url: The source URL for fallback values
        
    Returns:
        Fixed content dictionary
    """
    # Ensure we have a proper content dict to start with
    if not isinstance(content, dict):
        content = {}
    
    # Ensure title exists and is not empty
    if not content.get("title") or len(content.get("title", "").strip()) < 2:
        content["title"] = generate_title_from_url(url)

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
    i = 0
    while i < len(structured_content):
        item = structured_content[i]
        # Handle list items format conversion
        if item.get("type") == "list" and "items" in item:
            list_items = item.pop("items", [])
            # Remove the original list item
            structured_content.pop(i)
            # Insert individual bullet items
            for list_item in reversed(list_items):
                structured_content.insert(
                    i, {"type": "bullet", "content": list_item}
                )
        else:
            i += 1

    # Ensure images list exists
    if "images" not in content:
        content["images"] = []

    return content