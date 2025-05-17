"""Tests for syntax highlight compiler refactoring."""

from inklink.services.syntax_highlight_compiler import SyntaxHighlightCompiler
from inklink.services.syntax_tokens import TokenType


def test_simple_tokenize_basic():
    """Test that the refactored tokenizer still works for basic code."""
    compiler = SyntaxHighlightCompiler()
    compiler.set_language("python")  # Initialize language settings

    # Simple Python code
    code = """x = 42
# Comment here
print("hello")"""

    tokens = compiler._simple_tokenize(code)

    # Verify we get tokens
    assert len(tokens) > 0

    # Check some expected token types
    token_types = [t.type for t in tokens]
    assert TokenType.IDENTIFIER in token_types  # x, print
    assert TokenType.NUMBER in token_types  # 42
    assert TokenType.STRING in token_types  # "hello"
    assert TokenType.COMMENT in token_types  # # Comment here


def test_tokenizers_exist():
    """Test that all the new helper methods exist."""
    compiler = SyntaxHighlightCompiler()

    # Check that the refactored methods exist
    assert hasattr(compiler, "_tokenize_line")
    assert hasattr(compiler, "_tokenize_whitespace")
    assert hasattr(compiler, "_tokenize_comment")
    assert hasattr(compiler, "_tokenize_string")
    assert hasattr(compiler, "_tokenize_number")
    assert hasattr(compiler, "_tokenize_identifier_or_keyword")
    assert hasattr(compiler, "_get_identifier_type")
    assert hasattr(compiler, "_tokenize_operator")
    assert hasattr(compiler, "_tokenize_punctuation")


def test_tokenize_operators():
    """Test operator tokenization."""
    compiler = SyntaxHighlightCompiler()
    compiler.set_language("python")  # Initialize language settings

    # Test multi-character operators
    code = "x += 10"
    tokens = compiler._simple_tokenize(code)

    # Find the += operator
    operator_tokens = [t for t in tokens if t.type == TokenType.OPERATOR]
    assert any(t.value == "+=" for t in operator_tokens)
