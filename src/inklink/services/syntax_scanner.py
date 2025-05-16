"""Enhanced scanner for syntax highlighting with regex pattern matching."""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Tuple

from .syntax_tokens import Token, TokenType

logger = logging.getLogger(__name__)


@dataclass
class ScannerRule:
    """Defines a scanning rule for tokenization."""

    pattern: Pattern
    token_type: TokenType
    priority: int = 0
    multiline: bool = False
    end_pattern: Optional[str] = None
    capture_group: Optional[int] = None


@dataclass
class ScannerState:
    """Maintains the scanner's current state during tokenization."""

    position: int = 0
    line: int = 1
    column: int = 1
    in_multiline: Optional[TokenType] = None
    multiline_delimiter: Optional[str] = None
    multiline_end_pattern: Optional[str] = None


class LanguageScanner:
    """Scanner for a specific programming language."""

    def __init__(self, name: str):
        self.name = name
        self.rules: List[ScannerRule] = []
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for the language. Override in subclasses."""
        pass

    def add_rule(
        self,
        pattern: str,
        token_type: TokenType,
        priority: int = 0,
        multiline: bool = False,
        end_pattern: Optional[str] = None,
        capture_group: Optional[int] = None,
    ):
        """Add a scanning rule."""
        rule = ScannerRule(
            pattern=re.compile(pattern),
            token_type=token_type,
            priority=priority,
            multiline=multiline,
            end_pattern=end_pattern,
            capture_group=capture_group,
        )
        self.rules.append(rule)
        # Sort by priority (higher priority first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def scan(self, code: str) -> List[Token]:
        """Scan the code and return tokens."""
        tokens = []
        state = ScannerState()

        while state.position < len(code):
            # Handle multiline continuation
            if state.in_multiline:
                token = self._handle_multiline(code, state)
                if token:
                    tokens.append(token)
                continue

            # Try each rule
            matched = False
            for rule in self.rules:
                match = rule.pattern.match(code, state.position)
                if match:
                    # Handle multiline start specially
                    if rule.multiline:
                        state.in_multiline = rule.token_type
                        state.multiline_delimiter = match.group(0)
                        state.multiline_end_pattern = rule.end_pattern or match.group(0)
                        # Create a token for the opening delimiter
                        token = self._create_token_at_position(
                            state.position,
                            match.end(),
                            match.group(0),
                            rule.token_type,
                            state,
                        )
                        tokens.append(token)
                        state.position = match.end()
                        state.column += len(match.group(0))
                        matched = True
                        break

                    token = self._create_token(match, rule, state)
                    tokens.append(token)

                    # Update position
                    old_pos = state.position
                    state.position = match.end()

                    # Update line and column
                    matched_text = code[old_pos : state.position]
                    newlines = matched_text.count("\n")
                    if newlines > 0:
                        state.line += newlines
                        state.column = len(matched_text.split("\n")[-1]) + 1
                    else:
                        state.column += len(matched_text)

                    matched = True
                    break

            if not matched:
                # Handle newlines specially
                if state.position < len(code) and code[state.position] == "\n":
                    state.position += 1
                    state.line += 1
                    state.column = 1
                else:
                    # No rule matched - treat as unknown/error
                    tokens.append(
                        Token(
                            type=TokenType.UNKNOWN,
                            value=code[state.position],
                            start=state.position,
                            end=state.position + 1,
                            line=state.line,
                            column=state.column,
                        )
                    )
                    state.position += 1
                    state.column += 1

        return tokens

    def _handle_multiline(self, code: str, state: ScannerState) -> Optional[Token]:
        """Handle multiline tokens like block comments or multiline strings."""
        start_pos = state.position
        start_line = state.line
        start_column = state.column

        # Find the end pattern
        end_pattern = state.multiline_end_pattern
        end_pos = -1

        if end_pattern:
            end_pos = code.find(end_pattern, state.position)
            if end_pos != -1:
                # Found end delimiter
                value = code[state.position : end_pos]
                state.position = end_pos + len(end_pattern)

                # Create token for the content
                content_token = Token(
                    type=state.in_multiline,
                    value=value,
                    start=start_pos,
                    end=end_pos,
                    line=start_line,
                    column=start_column,
                )

                # Update line/column
                newlines = value.count("\n")
                if newlines > 0:
                    state.line += newlines
                    last_line = value.split("\n")[-1]
                    state.column = len(last_line) + 1
                else:
                    state.column += len(value)

                # Create token for closing delimiter (not used currently)
                # closing_token = Token(
                #     type=state.in_multiline,
                #     value=end_pattern,
                #     start=end_pos,
                #     end=state.position,
                #     line=state.line,
                #     column=state.column,
                # )

                state.column += len(end_pattern)
                state.in_multiline = None
                state.multiline_delimiter = None
                state.multiline_end_pattern = None

                return content_token  # Return content, closing will be next

        # No end found - consume rest of line or file
        line_end = code.find("\n", state.position)
        if line_end == -1:
            line_end = len(code)

        value = code[state.position : line_end]
        token = Token(
            type=state.in_multiline,
            value=value,
            start=state.position,
            end=line_end,
            line=state.line,
            column=state.column,
        )

        state.position = line_end
        state.column += len(value)

        return token

    def _create_token(
        self, match: re.Match, rule: ScannerRule, state: ScannerState
    ) -> Token:
        """Create a token from a regex match."""
        if rule.capture_group is not None:
            value = match.group(rule.capture_group)
            start = match.start(rule.capture_group)
            end = match.end(rule.capture_group)
        else:
            value = match.group(0)
            start = match.start()
            end = match.end()

        return Token(
            type=rule.token_type,
            value=value,
            start=start,
            end=end,
            line=state.line,
            column=state.column,
        )

    def _create_token_at_position(
        self,
        start: int,
        end: int,
        value: str,
        token_type: TokenType,
        state: ScannerState,
    ) -> Token:
        """Create a token at a specific position."""
        return Token(
            type=token_type,
            value=value,
            start=start,
            end=end,
            line=state.line,
            column=state.column,
        )


class PythonScanner(LanguageScanner):
    """Scanner for Python code."""

    def __init__(self):
        super().__init__("python")

    def _compile_patterns(self):
        """Compile Python-specific patterns."""
        # Comments (highest priority)
        self.add_rule(r"#[^\n]*", TokenType.COMMENT, priority=100)

        # Triple-quoted strings (multiline)
        self.add_rule(r'"""', TokenType.STRING, priority=90, multiline=True)
        self.add_rule(r"'''", TokenType.STRING, priority=90, multiline=True)

        # F-strings
        self.add_rule(r'f"[^"]*"', TokenType.STRING, priority=85)
        self.add_rule(r"f'[^']*'", TokenType.STRING, priority=85)

        # Raw strings
        self.add_rule(r'r"[^"]*"', TokenType.STRING, priority=82)
        self.add_rule(r"r'[^']*'", TokenType.STRING, priority=82)

        # Regular strings
        self.add_rule(r'"[^"\n]*"', TokenType.STRING, priority=80)
        self.add_rule(r"'[^'\n]*'", TokenType.STRING, priority=80)

        # Numbers (including complex)
        self.add_rule(
            r"\b\d+\.\d*[jJ]?\b", TokenType.NUMBER, priority=75
        )  # Float/complex
        self.add_rule(r"\b\d+[jJ]\b", TokenType.NUMBER, priority=74)  # Complex
        self.add_rule(r"\b\d+\b", TokenType.NUMBER, priority=73)  # Int
        self.add_rule(r"\b0[xX][0-9a-fA-F]+\b", TokenType.NUMBER, priority=72)  # Hex
        self.add_rule(r"\b0[oO][0-7]+\b", TokenType.NUMBER, priority=71)  # Octal
        self.add_rule(r"\b0[bB][01]+\b", TokenType.NUMBER, priority=70)  # Binary

        # Keywords (must come before identifiers)
        keywords = {
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
        keyword_pattern = r"\b(" + "|".join(keywords) + r")\b"
        self.add_rule(keyword_pattern, TokenType.KEYWORD, priority=60)

        # Built-in functions
        builtins = {
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
        builtin_pattern = r"\b(" + "|".join(builtins) + r")\b"
        self.add_rule(builtin_pattern, TokenType.BUILTIN, priority=55)

        # Decorators
        self.add_rule(r"@\w+", TokenType.ANNOTATION, priority=50)

        # Identifiers
        self.add_rule(r"\b[a-zA-Z_]\w*\b", TokenType.IDENTIFIER, priority=40)

        # Operators (order matters!)
        self.add_rule(r"//=", TokenType.OPERATOR, priority=38)
        self.add_rule(r"\*\*=", TokenType.OPERATOR, priority=37)
        self.add_rule(
            r"\+=|-=|\*=|/=|%=|&=|\|=|\^=|>>=|<<=", TokenType.OPERATOR, priority=36
        )
        self.add_rule(r"//", TokenType.OPERATOR, priority=35)
        self.add_rule(r"\*\*", TokenType.OPERATOR, priority=34)
        self.add_rule(r"==|!=|<=|>=|>>|<<", TokenType.OPERATOR, priority=33)
        self.add_rule(r"[-+*/%<>=&|^~]", TokenType.OPERATOR, priority=30)

        # Punctuation
        self.add_rule(r"[()[\]{},.:;]", TokenType.PUNCTUATION, priority=20)

        # Whitespace
        self.add_rule(r"[ \t]+", TokenType.WHITESPACE, priority=10)


class JavaScriptScanner(LanguageScanner):
    """Scanner for JavaScript code."""

    def __init__(self):
        super().__init__("javascript")

    def _compile_patterns(self):
        """Compile JavaScript-specific patterns."""
        # Comments
        self.add_rule(r"//[^\n]*", TokenType.COMMENT, priority=100)  # Line comments
        self.add_rule(
            r"/\*", TokenType.COMMENT, priority=95, multiline=True, end_pattern="*/"
        )

        # Template literals (multiline)
        self.add_rule(
            r"`", TokenType.STRING, priority=90, multiline=True, end_pattern="`"
        )

        # Regular expressions (must come before division operator)
        self.add_rule(r"/[^/\n]+/[gimuysd]*", TokenType.STRING, priority=85)

        # Strings
        self.add_rule(r'"[^"\n]*"', TokenType.STRING, priority=80)
        self.add_rule(r"'[^'\n]*'", TokenType.STRING, priority=80)

        # Numbers
        self.add_rule(
            r"\b\d+\.\d*([eE][+-]?\d+)?\b", TokenType.NUMBER, priority=72
        )  # Float
        self.add_rule(r"\b\d+([eE][+-]?\d+)?\b", TokenType.NUMBER, priority=71)  # Int
        self.add_rule(r"\b0[xX][0-9a-fA-F]+\b", TokenType.NUMBER, priority=70)  # Hex
        self.add_rule(r"\b0[oO][0-7]+\b", TokenType.NUMBER, priority=70)  # Octal
        self.add_rule(r"\b0[bB][01]+\b", TokenType.NUMBER, priority=70)  # Binary

        # Keywords
        keywords = {
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
        keyword_pattern = r"\b(" + "|".join(keywords) + r")\b"
        self.add_rule(keyword_pattern, TokenType.KEYWORD, priority=60)

        # Built-in objects and functions
        builtins = {
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
        builtin_pattern = r"\b(" + "|".join(builtins) + r")\b"
        self.add_rule(builtin_pattern, TokenType.BUILTIN, priority=55)

        # Identifiers
        self.add_rule(r"\b[a-zA-Z_$][\w$]*\b", TokenType.IDENTIFIER, priority=40)

        # Operators
        self.add_rule(r"=>", TokenType.OPERATOR, priority=39)  # Arrow function
        self.add_rule(r"\+\+|--", TokenType.OPERATOR, priority=38)
        self.add_rule(r"===|!==", TokenType.OPERATOR, priority=37)
        self.add_rule(
            r"\+=|-=|\*=|/=|%=|<<=|>>=|>>>=|&=|\|=|\^=", TokenType.OPERATOR, priority=36
        )
        self.add_rule(r"&&|\|\|", TokenType.OPERATOR, priority=35)
        self.add_rule(r"<<|>>>|>>", TokenType.OPERATOR, priority=34)
        self.add_rule(r"==|!=|<=|>=", TokenType.OPERATOR, priority=33)
        self.add_rule(r"[-+*/%<>=&|^~!?:]", TokenType.OPERATOR, priority=30)

        # Punctuation
        self.add_rule(r"[()[\]{},.:;]", TokenType.PUNCTUATION, priority=20)

        # Whitespace
        self.add_rule(r"[ \t]+", TokenType.WHITESPACE, priority=10)


class ScannerFactory:
    """Factory for creating language-specific scanners."""

    _scanners: Dict[str, type] = {
        "python": PythonScanner,
        "javascript": JavaScriptScanner,
        "js": JavaScriptScanner,  # Alias
    }

    @classmethod
    def create_scanner(cls, language: str) -> Optional[LanguageScanner]:
        """Create a scanner for the specified language."""
        scanner_class = cls._scanners.get(language.lower())
        if scanner_class:
            return scanner_class()
        return None

    @classmethod
    def register_scanner(cls, language: str, scanner_class: type):
        """Register a new scanner class for a language."""
        cls._scanners[language.lower()] = scanner_class
