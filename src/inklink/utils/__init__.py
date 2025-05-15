"""Utility functions for InkLink.

This package provides utility functions for the InkLink project.
"""

from inklink.utils.common import (
    convert_html_to_rm,
    convert_markdown_to_rm,
    ensure_rcu_available,
    format_error,
    is_safe_url,
    retry_operation,
)
from inklink.utils.hcl_render import create_hcl_from_content, escape_hcl
from inklink.utils.html_processor import (
    extract_structured_content,
    extract_title_from_html,
    find_main_content_container,
    generate_title_from_url,
    parse_html_container,
    validate_and_fix_content,
)
from inklink.utils.url_utils import extract_url

__all__ = [
    "retry_operation",
    "format_error",
    "ensure_drawj2d_available",
    "create_hcl_from_markdown",
    "convert_markdown_to_rm",
    "convert_html_to_rm",
    "create_hcl_from_content",
    "escape_hcl",
    "is_safe_url",
    "extract_url",
    "extract_structured_content",
    "validate_and_fix_content",
    "extract_title_from_html",
    "find_main_content_container",
    "parse_html_container",
    "generate_title_from_url",
]
