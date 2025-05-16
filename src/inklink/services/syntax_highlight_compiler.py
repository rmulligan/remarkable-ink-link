"""Syntax highlighting compiler service for converting code to HCL format"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .syntax_scanner import ScannerFactory
from .syntax_tokens import Token, TokenType

logger = logging.getLogger(__name__)


class Language(Enum):
    """Supported programming languages"""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    TYPESCRIPT = "typescript"


class Theme(Enum):
    """Available color themes"""

    MONOKAI = "monokai"
    DARK = "dark"
    LIGHT = "light"
    GITHUB = "github"
    SOLARIZED = "solarized"


@dataclass
class ThemeColors:
    """Color theme for syntax highlighting"""

    name: str
    colors: Dict[TokenType, str]
    font: str = "monospace"
    font_size: int = 10
    line_height: float = 1.2

    @classmethod
    def default_theme(cls) -> "ThemeColors":
        """Get the default dark theme"""
        return cls(
            name="default_dark",
            colors={
                TokenType.KEYWORD: "#FFAB91",  # Orange
                TokenType.IDENTIFIER: "#E1BEE7",  # Light purple
                TokenType.STRING: "#C5E1A5",  # Light green
                TokenType.NUMBER: "#81D4FA",  # Light blue
                TokenType.COMMENT: "#9E9E9E",  # Gray
                TokenType.OPERATOR: "#FFE082",  # Yellow
                TokenType.PUNCTUATION: "#FFFFFF",  # White
                TokenType.WHITESPACE: "#FFFFFF",  # White
                TokenType.ANNOTATION: "#FFD54F",  # Amber
                TokenType.FUNCTION: "#CE93D8",  # Purple
                TokenType.CLASS: "#4FC3F7",  # Light blue
                TokenType.TYPE: "#4DD0E1",  # Cyan
                TokenType.BUILTIN: "#F48FB1",  # Pink
                TokenType.ERROR: "#EF5350",  # Red
                TokenType.UNKNOWN: "#BDBDBD",  # Light gray
            },
        )

    @classmethod
    def light_theme(cls) -> "ThemeColors":
        """Get the light theme"""
        return cls(
            name="light",
            colors={
                TokenType.KEYWORD: "#D84315",  # Deep orange
                TokenType.IDENTIFIER: "#6A1B9A",  # Purple
                TokenType.STRING: "#388E3C",  # Green
                TokenType.NUMBER: "#0277BD",  # Blue
                TokenType.COMMENT: "#757575",  # Gray
                TokenType.OPERATOR: "#F57C00",  # Orange
                TokenType.PUNCTUATION: "#212121",  # Dark gray
                TokenType.WHITESPACE: "#000000",  # Black
                TokenType.ANNOTATION: "#F9A825",  # Yellow
                TokenType.FUNCTION: "#8E24AA",  # Deep purple
                TokenType.CLASS: "#0288D1",  # Blue
                TokenType.TYPE: "#00ACC1",  # Cyan
                TokenType.BUILTIN: "#C2185B",  # Pink
                TokenType.ERROR: "#D32F2F",  # Red
                TokenType.UNKNOWN: "#616161",  # Gray
            },
        )


class LanguageDefinition:
    """Defines syntax highlighting rules for a programming language"""

    def __init__(self, name: str):
        self.name = name
        self.keywords: Set[str] = set()
        self.builtin_functions: Set[str] = set()
        self.operators: Set[str] = set()
        self.line_comment: Optional[str] = None
        self.block_comment: Optional[Tuple[str, str]] = None
        self.string_delimiters: List[str] = []
        self.identifier_pattern: str = r"[a-zA-Z_][a-zA-Z0-9_]*"
        self.number_pattern: str = r"\b\d+\.?\d*\b"

    @classmethod
    def python(cls) -> "LanguageDefinition":
        """Get Python language definition"""
        lang = cls("python")
        lang.keywords = {
            "def",
            "class",
            "import",
            "from",
            "return",
            "if",
            "else",
            "elif",
            "for",
            "while",
            "break",
            "continue",
            "pass",
            "try",
            "except",
            "finally",
            "raise",
            "with",
            "as",
            "in",
            "is",
            "not",
            "and",
            "or",
            "None",
            "True",
            "False",
            "lambda",
            "yield",
            "await",
            "async",
            "global",
            "nonlocal",
            "del",
            "assert",
        }
        lang.builtin_functions = {
            "print",
            "input",
            "len",
            "range",
            "int",
            "float",
            "str",
            "list",
            "dict",
            "set",
            "tuple",
            "open",
            "file",
            "help",
            "dir",
            "type",
            "isinstance",
            "hasattr",
            "getattr",
            "setattr",
            "delattr",
            "min",
            "max",
            "sum",
            "abs",
            "round",
            "sorted",
            "reversed",
            "enumerate",
            "zip",
            "map",
            "filter",
            "any",
            "all",
        }
        lang.operators = {
            "+",
            "-",
            "*",
            "/",
            "//",
            "%",
            "**",
            "=",
            "+=",
            "-=",
            "*=",
            "/=",
            "==",
            "!=",
            "<",
            "<=",
            ">",
            ">=",
            "<<",
            ">>",
            "&",
            "|",
            "^",
            "~",
        }
        lang.line_comment = "#"
        lang.string_delimiters = ['"', "'", '"""', "'''"]
        return lang

    @classmethod
    def javascript(cls) -> "LanguageDefinition":
        """Get JavaScript language definition"""
        lang = cls("javascript")
        lang.keywords = {
            "function",
            "class",
            "const",
            "let",
            "var",
            "return",
            "if",
            "else",
            "for",
            "while",
            "do",
            "break",
            "continue",
            "switch",
            "case",
            "default",
            "try",
            "catch",
            "finally",
            "throw",
            "new",
            "this",
            "super",
            "extends",
            "instanceof",
            "typeof",
            "void",
            "delete",
            "in",
            "of",
            "true",
            "false",
            "null",
            "undefined",
            "async",
            "await",
            "yield",
            "import",
            "export",
            "from",
            "as",
            "static",
            "get",
            "set",
        }
        lang.builtin_functions = {
            "console",
            "log",
            "Array",
            "Object",
            "String",
            "Number",
            "Boolean",
            "Date",
            "Math",
            "JSON",
            "Promise",
            "Map",
            "Set",
            "WeakMap",
            "WeakSet",
            "Symbol",
            "Error",
            "parseInt",
            "parseFloat",
            "isNaN",
            "isFinite",
            "alert",
            "prompt",
            "confirm",
            "setTimeout",
            "setInterval",
        }
        lang.operators = {
            "+",
            "-",
            "*",
            "/",
            "%",
            "=",
            "+=",
            "-=",
            "*=",
            "/=",
            "%=",
            "==",
            "===",
            "!=",
            "!==",
            "<",
            "<=",
            ">",
            ">=",
            "&&",
            "||",
            "!",
            "++",
            "--",
            "<<",
            ">>",
            ">>>",
            "&",
            "|",
            "^",
            "~",
            "?",
            ":",
        }
        lang.line_comment = "//"
        lang.block_comment = ("/*", "*/")
        lang.string_delimiters = ['"', "'", "`"]
        return lang


class SyntaxHighlightCompiler:
    """Compiles source code to HCL with syntax highlighting"""

    def __init__(self):
        self.languages: Dict[str, LanguageDefinition] = {
            "python": LanguageDefinition.python(),
            "javascript": LanguageDefinition.javascript(),
            "js": LanguageDefinition.javascript(),  # Alias
        }
        self.themes: Dict[str, ThemeColors] = {
            "default": ThemeColors.default_theme(),
            "default_dark": ThemeColors.default_theme(),
            "light": ThemeColors.light_theme(),
            "monokai": ThemeColors.default_theme(),  # Use default for now
        }
        self.current_theme = self.themes["default"]
        self.current_language: Optional[LanguageDefinition] = None

    def set_theme(self, theme_name: str) -> bool:
        """Set the active theme"""
        if theme_name in self.themes:
            self.current_theme = self.themes[theme_name]
            logger.info(f"Set theme to: {theme_name}")
            return True
        logger.error(f"Theme not found: {theme_name}")
        return False

    def add_theme(self, theme: ThemeColors) -> None:
        """Add a custom theme"""
        self.themes[theme.name] = theme
        logger.info(f"Added theme: {theme.name}")

    def set_language(self, language_name: str) -> bool:
        """Set the active language for highlighting"""
        if language_name in self.languages:
            self.current_language = self.languages[language_name]
            logger.info(f"Set language to: {language_name}")
            return True
        logger.error(f"Language not found: {language_name}")
        return False

    def tokenize(self, code: str, language: Optional[str] = None) -> List[Token]:
        """Tokenize source code into syntax tokens"""
        if language:
            self.set_language(language)

        if not self.current_language:
            logger.error("No language set for tokenization")
            return []

        # Use the enhanced scanner if available
        scanner = ScannerFactory.create_scanner(self.current_language.name)
        if scanner:
            logger.info(f"Using enhanced scanner for {self.current_language.name}")
            return scanner.scan(code)

        # Fallback to simple tokenizer
        logger.info(f"Using simple tokenizer for {self.current_language.name}")
        return self._simple_tokenize(code)

    def _simple_tokenize(self, code: str) -> List[Token]:
        """Simple tokenizer fallback for languages without a scanner"""
        tokens = []
        position = 0

        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            i = 0

            while i < len(line):
                # Skip whitespace
                if line[i].isspace():
                    start = i
                    while i < len(line) and line[i].isspace():
                        i += 1
                    tokens.append(
                        Token(
                            type=TokenType.WHITESPACE,
                            value=line[start:i],
                            start=position + start,
                            end=position + i,
                            line=line_num,
                            column=start + 1,
                        )
                    )
                    continue

                # Check for comments
                if self.current_language.line_comment:
                    if line[i:].startswith(self.current_language.line_comment):
                        tokens.append(
                            Token(
                                type=TokenType.COMMENT,
                                value=line[i:],
                                start=position + i,
                                end=position + len(line),
                                line=line_num,
                                column=i + 1,
                            )
                        )
                        break

                # Check for strings (simple version)
                if line[i] in ['"', "'"]:
                    quote = line[i]
                    start = i
                    i += 1
                    while i < len(line) and line[i] != quote:
                        if line[i] == "\\":
                            i += 2
                        else:
                            i += 1
                    if i < len(line):
                        i += 1
                    tokens.append(
                        Token(
                            type=TokenType.STRING,
                            value=line[start:i],
                            start=position + start,
                            end=position + i,
                            line=line_num,
                            column=start + 1,
                        )
                    )
                    continue

                # Check for numbers
                if line[i].isdigit():
                    start = i
                    while i < len(line) and (line[i].isdigit() or line[i] == "."):
                        i += 1
                    tokens.append(
                        Token(
                            type=TokenType.NUMBER,
                            value=line[start:i],
                            start=position + start,
                            end=position + i,
                            line=line_num,
                            column=start + 1,
                        )
                    )
                    continue

                # Check for identifiers and keywords
                if line[i].isalpha() or line[i] == "_":
                    start = i
                    while i < len(line) and (line[i].isalnum() or line[i] == "_"):
                        i += 1
                    word = line[start:i]

                    token_type = TokenType.IDENTIFIER
                    if word in self.current_language.keywords:
                        token_type = TokenType.KEYWORD
                    elif word in self.current_language.builtin_functions:
                        token_type = TokenType.BUILTIN

                    tokens.append(
                        Token(
                            type=token_type,
                            value=word,
                            start=position + start,
                            end=position + i,
                            line=line_num,
                            column=start + 1,
                        )
                    )
                    continue

                # Check for operators and punctuation
                if i < len(line):
                    # Multi-character operators
                    for op_len in [3, 2, 1]:
                        if i + op_len <= len(line):
                            op = line[i : i + op_len]
                            if op in self.current_language.operators:
                                tokens.append(
                                    Token(
                                        type=TokenType.OPERATOR,
                                        value=op,
                                        start=position + i,
                                        end=position + i + op_len,
                                        line=line_num,
                                        column=i + 1,
                                    )
                                )
                                i += op_len
                                break
                    else:
                        # Single character (punctuation or unknown)
                        tokens.append(
                            Token(
                                type=TokenType.PUNCTUATION,
                                value=line[i],
                                start=position + i,
                                end=position + i + 1,
                                line=line_num,
                                column=i + 1,
                            )
                        )
                        i += 1

            position += len(line) + 1  # +1 for newline

        return tokens

    def generate_hcl_from_tokens(
        self, tokens: List[Token], width: float = 8.5, height: float = 11.0
    ) -> str:
        """Generate HCL script from tokens with syntax highlighting"""
        if not self.current_theme:
            logger.error("No theme set for HCL generation")
            return ""

        hcl_lines = []

        # Header with correct HCL syntax
        hcl_lines.append(f"# Syntax highlighting theme: {self.current_theme.name}")
        hcl_lines.append(f"# Generated by InkLink Syntax Highlight Compiler")
        hcl_lines.append("")

        # Font settings - use proper drawj2d font name
        font_name = (
            "LinesMono"
            if self.current_theme.font == "monospace"
            else self.current_theme.font
        )
        font_size = self.current_theme.font_size / 4.0  # Convert to drawj2d scale
        hcl_lines.append(f"font {font_name} {font_size}")
        hcl_lines.append("")

        # Generate HCL for each line
        current_line = 1
        x_pos = 10  # Left margin in HCL units
        y_pos = 10  # Top margin in HCL units
        line_height = font_size * 4  # Line height in HCL units

        for token in tokens:
            if token.line > current_line:
                # New line
                current_line = token.line
                x_pos = 10
                y_pos += line_height

            # Skip whitespace tokens - just advance position
            if token.type == TokenType.WHITESPACE:
                x_pos += len(token.value) * font_size * 2
                continue

            # Get color for token - convert hex to drawj2d color names
            hex_color = self.current_theme.colors.get(token.type, "#000000")
            # For now, map to basic drawj2d colors
            color_map = {
                "#FFAB91": "orange",  # Keywords
                "#E1BEE7": "purple",  # Identifiers
                "#C5E1A5": "green",  # Strings
                "#81D4FA": "blue",  # Numbers
                "#9E9E9E": "gray",  # Comments
                "#FFE082": "yellow",  # Operators
                "#FFFFFF": "black",  # Punctuation (inverted for visibility)
                "#FFD54F": "orange",  # Annotations
                "#CE93D8": "purple",  # Functions
                "#4FC3F7": "blue",  # Classes
                "#F48FB1": "pink",  # Builtins
                "#EF5350": "red",  # Errors
            }
            pen_color = "black"  # Default
            for hex_val, color_name in color_map.items():
                if hex_color.upper() == hex_val.upper():
                    pen_color = color_name
                    break

            # Move to position and set pen color
            hcl_lines.append(f"m {x_pos} {y_pos}")
            hcl_lines.append(f"pen {pen_color}")

            # Generate HCL text command with proper escaping for curly braces
            escaped_value = token.value
            if "{" in escaped_value or "}" in escaped_value:
                # For text with curly braces, use curly brace syntax
                escaped_value = escaped_value.replace("{", "{{")
                escaped_value = escaped_value.replace("}", "}}")
                hcl_lines.append(f"text {{{escaped_value}}}")
            else:
                # For text without curly braces, use the simpler syntax
                hcl_lines.append(f"text {{{token.value}}}")

            # Update x position based on text length
            x_pos += len(token.value) * font_size * 2

        return "\n".join(hcl_lines)

    def compile_code_to_hcl(
        self, code: str, language: str, theme: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Main method to compile source code to HCL with syntax highlighting"""
        try:
            # Set language and theme
            if not self.set_language(language):
                return False, f"Unsupported language: {language}"

            if theme and not self.set_theme(theme):
                return False, f"Unknown theme: {theme}"

            # Tokenize the code
            tokens = self.tokenize(code)
            if not tokens:
                return False, "Failed to tokenize code"

            # Generate HCL
            hcl_content = self.generate_hcl_from_tokens(tokens)

            logger.info(f"Successfully compiled {len(tokens)} tokens to HCL")
            return True, hcl_content

        except Exception as e:
            logger.error(f"Error compiling code to HCL: {e}")
            return False, str(e)
