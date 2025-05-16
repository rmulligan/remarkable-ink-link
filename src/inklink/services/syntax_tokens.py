"""Token definitions for syntax highlighting."""

from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass


class TokenType(Enum):
    """Token types for syntax highlighting"""

    KEYWORD = "keyword"
    IDENTIFIER = "identifier"
    STRING = "string"
    NUMBER = "number"
    COMMENT = "comment"
    OPERATOR = "operator"
    PUNCTUATION = "punctuation"
    WHITESPACE = "whitespace"
    ANNOTATION = "annotation"
    FUNCTION = "function"
    CLASS = "class"
    TYPE = "type"
    BUILTIN = "builtin"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class Token:
    """Represents a syntax token"""

    type: TokenType
    value: str
    start: int
    end: int
    line: int
    column: int
    metadata: Optional[Dict[str, Any]] = None
