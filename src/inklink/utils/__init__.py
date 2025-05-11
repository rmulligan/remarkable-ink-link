"""Utility functions for InkLink.

This package provides utility functions for the InkLink project.
"""

from inklink.utils.common import (
    retry_operation,
    format_error,
    ensure_rcu_available,
    convert_markdown_to_rm,
    convert_html_to_rm,
    is_safe_url,
)

from inklink.utils.hcl_render import (
    create_hcl_from_content,
    escape_hcl,
)

from inklink.utils.url_utils import (
    extract_url,
)

from inklink.utils.html_processor import (
    extract_structured_content,
    validate_and_fix_content,
    extract_title_from_html,
    find_main_content_container,
    parse_html_container,
    generate_title_from_url,
)

__all__ = [
    "retry_operation",
    "format_error",
    "ensure_rcu_available",
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
