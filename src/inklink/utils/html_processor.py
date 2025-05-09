"""HTML processing utilities for InkLink.

This module provides utilities for extracting structured content from HTML.
"""

import logging
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


def extract_structured_content(html_content: str, url: str) -> Dict[str, Any]:
    """
    Extract structured content from HTML.
    
    Args:
        html_content: HTML content to extract from
        url: Source URL for resolving relative links
        
    Returns:
        Dictionary with title, structured_content, and images
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract title (try meta tags first, then title tag)
        title = extract_title(soup) or url
        
        # Extract content
        structured_content = []
        images = []
        
        # Process body content
        body = soup.body or soup
        for element in body.find_all(recursive=True):
            # Skip hidden elements
            if element.get("hidden") or element.get("style") == "display:none":
                continue
                
            # Process based on element type
            if element.name == "h1":
                structured_content.append({"type": "h1", "content": element.get_text().strip()})
            elif element.name == "h2":
                structured_content.append({"type": "h2", "content": element.get_text().strip()})
            elif element.name == "h3":
                structured_content.append({"type": "h3", "content": element.get_text().strip()})
            elif element.name == "p" and element.get_text().strip():
                structured_content.append({"type": "paragraph", "content": element.get_text().strip()})
            elif element.name == "ul" or element.name == "ol":
                items = [li.get_text().strip() for li in element.find_all("li") if li.get_text().strip()]
                if items:
                    structured_content.append({"type": "list", "items": items})
            elif element.name == "pre" or element.name == "code":
                structured_content.append({"type": "code", "content": element.get_text().strip()})
            elif element.name == "blockquote":
                structured_content.append({"type": "quote", "content": element.get_text().strip()})
            elif element.name == "img" and element.get("src"):
                image_url = urljoin(url, element.get("src"))
                alt_text = element.get("alt", "")
                images.append({"url": image_url, "alt": alt_text})
                structured_content.append({"type": "image", "url": image_url, "alt": alt_text})
                
        # Handle empty content
        if not structured_content:
            main_text = body.get_text().strip()
            if main_text:
                # Split text into paragraphs
                paragraphs = [p.strip() for p in re.split(r'\n\s*\n', main_text) if p.strip()]
                for p in paragraphs:
                    structured_content.append({"type": "paragraph", "content": p})
            else:
                structured_content.append({"type": "paragraph", "content": "No content extracted"})
                
        return {
            "title": title,
            "structured_content": structured_content,
            "images": images,
        }
        
    except Exception as e:
        logger.error(f"Error extracting structured content: {e}")
        return {
            "title": url,
            "structured_content": [{"type": "paragraph", "content": f"Error extracting content: {e}"}],
            "images": [],
        }


def extract_title(soup: BeautifulSoup) -> str:
    """
    Extract title from HTML using various methods.
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        Title string, or empty string if no title found
    """
    # Try OpenGraph title (both property and meta with name)
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if not og_title:
        og_title = soup.find("meta", attrs={"name": "og:title"})
    
    if og_title and og_title.get("content"):
        return og_title["content"].strip()
        
    # Try Twitter title
    twitter_title = soup.find("meta", attrs={"property": "twitter:title"})
    if not twitter_title:
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
    
    if twitter_title and twitter_title.get("content"):
        return twitter_title["content"].strip()
        
    # Try main heading
    h1 = soup.find("h1")
    if h1 and h1.get_text().strip():
        return h1.get_text().strip()
        
    # Try title tag
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text().strip():
        return title_tag.get_text().strip()
        
    return ""


def validate_and_fix_content(content: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Validate and fix structured content.
    
    Args:
        content: Structured content to validate
        url: Source URL
        
    Returns:
        Validated and fixed content
    """
    # Ensure title exists
    if not content.get("title"):
        content["title"] = url
        
    # Ensure structured_content exists and is a list
    if not content.get("structured_content") or not isinstance(content["structured_content"], list):
        content["structured_content"] = [{"type": "paragraph", "content": "No content extracted"}]
        
    # Ensure images exists and is a list
    if not content.get("images") or not isinstance(content["images"], list):
        content["images"] = []
        
    # Validate each content item
    for i, item in enumerate(content["structured_content"]):
        # Ensure each item has a type
        if not item.get("type"):
            item["type"] = "paragraph"
            
        # Ensure text content exists
        if item["type"] in ["paragraph", "h1", "h2", "h3", "code", "quote"]:
            if not item.get("content") or not isinstance(item["content"], str):
                item["content"] = ""
                
        # Ensure list items exist
        if item["type"] == "list":
            if not item.get("items") or not isinstance(item["items"], list):
                item["items"] = []
                
        # Ensure image URLs exist
        if item["type"] == "image":
            if not item.get("url"):
                content["structured_content"][i] = {"type": "paragraph", "content": "Invalid image"}
                
    return content