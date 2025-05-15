"""External service adapters for InkLink.

This package provides adapters for external services and tools.
"""

from inklink.adapters.handwriting_adapter import HandwritingAdapter
from inklink.adapters.handwriting_web_adapter import HandwritingWebAdapter
from inklink.adapters.http_adapter import HTTPAdapter
from inklink.adapters.remarkable_adapter import RemarkableAdapter

__all__ = [
    "RemarkableAdapter",
    "HandwritingAdapter",
    "HandwritingWebAdapter",
    "HTTPAdapter",
]
