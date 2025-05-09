"""HTML processing utilities for InkLink.

This module provides functions for processing HTML content into structured
data suitable for document generation.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


def extract_title_from_html(soup: BeautifulSoup) -> str:
    """
    Extract title from HTML using various methods.

    Tries:
    1. OpenGraph meta tag
    2. Twitter meta tag
    3. Traditional title tag
    4. First h1 tag

    Args:
        soup: BeautifulSoup object of HTML document

    Returns:
        Best available title or empty string
    """
    # Try OpenGraph title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    # Try Twitter Card title
    twitter_title = soup.find("meta", property="twitter:title")
    if twitter_title and twitter_title.get("content"):
        return twitter_title["content"].strip()

    # Try traditional title
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    # Try first h1
    h1 = soup.find("h1")
    if h1 and h1.text:
        return h1.text.strip()

    return ""


def generate_title_from_url(url: str) -> str:
    """
    Generate a readable title from a URL.

    Args:
        url: URL to extract title from

    Returns:
        Human-readable title derived from URL
    """
    try:
        # Parse URL
        parsed = urlparse(url)

        # Get domain without www.
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]

        # Get path without trailing slash
        path = parsed.path
        if path.endswith("/"):
            path = path[:-1]

        # If path is empty, return domain-based title
        if not path:
            return f"Page from {domain}"

        # Get last path segment
        segments = path.strip("/").split("/")
        last_segment = segments[-1]

        # Convert hyphens, underscores to spaces
        last_segment = re.sub(r"[-_]", " ", last_segment)

        # Title case and remove file extension
        title = " ".join(word.capitalize() for word in last_segment.split())
        title = re.sub(r"\.[a-zA-Z0-9]+$", "", title)

        return f"{title} - {domain}"

    except Exception as e:
        logger.error(f"Error generating title from URL: {e}")
        return "Document"


def find_main_content_container(soup: BeautifulSoup) -> Tag:
    """
    Find the main content container in HTML.

    Looks for content in this priority:
    1. <main>
    2. <article>
    3. <div id="content">
    4. <div class="content">
    5. <body>

    Args:
        soup: BeautifulSoup object

    Returns:
        BeautifulSoup Tag containing main content
    """
    # Look for <main> (HTML5 semantic element)
    main_element = soup.find("main")
    if main_element:
        return main_element

    # Look for <article>
    article = soup.find("article")
    if article:
        return article

    # Look for div with id="content"
    content_div = soup.find("div", id="content")
    if content_div:
        return content_div

    # Look for div with class containing "content"
    content_class = soup.find("div", class_=lambda c: c and "content" in c.lower())
    if content_class:
        return content_class

    # Fallback to <body>
    return soup.body or soup


def parse_html_container(
    container: Tag, base_url: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parse an HTML container into structured content and images.

    Args:
        container: BeautifulSoup Tag to parse
        base_url: Base URL for resolving relative links

    Returns:
        Tuple of (structured_content, images)
    """
    structured_content = []
    images = []

    if not container:
        return structured_content, images

    # Process all elements
    for element in container.children:
        if not isinstance(element, Tag):
            continue

        # Handle different element types
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            structured_content.append(
                {"type": element.name, "content": element.get_text().strip()}
            )

        elif element.name == "p":
            structured_content.append(
                {"type": "paragraph", "content": element.get_text().strip()}
            )

        elif element.name in ["ul", "ol"]:
            items = [li.get_text().strip() for li in element.find_all("li")]
            if items:
                structured_content.append(
                    {
                        "type": "list",
                        "content": f"{'Numbered' if element.name == 'ol' else 'Bullet'} List",
                        "items": items,
                    }
                )

        elif element.name == "pre":
            # Handle code blocks
            structured_content.append(
                {"type": "code", "content": element.get_text().strip()}
            )

        elif element.name == "img":
            # Process image
            src = element.get("src", "")
            alt = element.get("alt", "")

            # Make relative URLs absolute
            if src and not (src.startswith("http://") or src.startswith("https://")):
                src = f"{base_url.rstrip('/')}/{src.lstrip('/')}"

            if src:
                image_data = {
                    "url": src,
                    "caption": alt,
                }
                images.append(image_data)

                # Add image reference to content
                structured_content.append(
                    {"type": "image", "content": alt or "Image", "url": src}
                )

        elif element.name == "blockquote":
            structured_content.append(
                {"type": "quote", "content": element.get_text().strip()}
            )

        # Recursively process div, article, section, etc.
        elif element.name in ["div", "article", "section", "main", "aside"]:
            sub_content, sub_images = parse_html_container(element, base_url)
            structured_content.extend(sub_content)
            images.extend(sub_images)

    return structured_content, images


def extract_structured_content(html_content: str, url: str) -> Dict[str, Any]:
    """
    Extract structured content from HTML.

    Args:
        html_content: HTML content string
        url: Source URL

    Returns:
        Dictionary with title, structured_content, and images
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title
        title = extract_title_from_html(soup)
        if not title:
            title = generate_title_from_url(url)

        # Find main content
        main_container = find_main_content_container(soup)

        # Parse content
        structured_content, images = parse_html_container(main_container, url)

        return {
            "title": title,
            "structured_content": structured_content,
            "images": images,
        }

    except Exception as e:
        logger.error(f"Error extracting structured content: {e}")
        return {
            "title": generate_title_from_url(url),
            "structured_content": [
                {
                    "type": "paragraph",
                    "content": f"Failed to extract content from {url}: {e}",
                }
            ],
            "images": [],
        }


def validate_and_fix_content(content: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Validate and fix content structure, ensuring all required keys exist.

    Args:
        content: Structured content dictionary
        url: Fallback URL for generating title

    Returns:
        Validated and fixed content dictionary
    """
    # Initialize with defaults if empty
    if not content:
        content = {}

    # Ensure title exists
    if "title" not in content or not content["title"]:
        content["title"] = generate_title_from_url(url)

    # Ensure structured_content exists
    if "structured_content" not in content:
        content["structured_content"] = []

    # Ensure images exists
    if "images" not in content:
        content["images"] = []

    # Convert legacy list format to bullet items
    structured = []
    for item in content["structured_content"]:
        if item.get("type") == "list" and "items" in item:
            # Convert list to bullet items
            for list_item in item["items"]:
                structured.append({"type": "bullet", "content": list_item})
        else:
            structured.append(item)

    content["structured_content"] = structured

    return content
