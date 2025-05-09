"""External service adapters for InkLink.

This package provides adapters for external services and tools.
"""

from inklink.adapters.remarkable_adapter import RemarkableAdapter
from inklink.adapters.handwriting_adapter import HandwritingAdapter
from inklink.adapters.http_adapter import HTTPAdapter

__all__ = [
    'RemarkableAdapter',
    'HandwritingAdapter',
    'HTTPAdapter',
]