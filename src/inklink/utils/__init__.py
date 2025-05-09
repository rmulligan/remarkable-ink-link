"""Utility functions for the InkLink application."""

import os
import logging
import time
import platform
import re
import subprocess
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any, Callable, TypeVar, Tuple, Optional

from inklink.config import CONFIG
from inklink.utils.common import (
    retry_operation,
    format_error,
    is_safe_url,
    ensure_rcu_available,
    convert_markdown_to_rm,
    convert_html_to_rm,
)
from inklink.utils.url_utils import (
    extract_url,
    sanitize_url,
    get_hostname,
)
from inklink.utils.hcl_render import (
    create_hcl_from_content,
    escape_hcl,
    render_hcl_resource,
)
from inklink.utils.html_processor import (
    extract_title_from_html,
    find_main_content_container,
    parse_html_container,
    extract_structured_content,
    generate_title_from_url,
    validate_and_fix_content,
)

logger = logging.getLogger(__name__)

# Type variable for generic function
T = TypeVar("T")
