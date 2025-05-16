#!/usr/bin/env python3
"""Test script for Phase 2: Syntax Highlight Compiler"""

import logging
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the path to import inklink
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.inklink.services.drawj2d_service import Drawj2dService  # noqa: E402
from src.inklink.services.syntax_highlight_compiler import (  # noqa: E402
    SyntaxHighlightCompiler,
    Theme,
    TokenType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)  # noqa: E402


def test_tokenization():
    """Test the tokenization functionality"""
    print("\n" + "=" * 50)
    print("Test 1: Python tokenization")
    print("=" * 50)

    compiler = SyntaxHighlightCompiler()

    python_code = '''def greet(name):
    """Say hello to someone"""
    message = f"Hello, {name}!"
    print(message)
    return message

# Test the function
result = greet("World")
print(f"Result: {result}")
'''

    tokens = compiler.tokenize(python_code, language="python")

    # Print token summary
    token_types = {}
    for token in tokens:
        token_types[token.type] = token_types.get(token.type, 0) + 1
        if token.type != TokenType.WHITESPACE:
            print(f"{token.type.value}: '{token.value}'")

    print("\nToken summary:")
    for token_type, count in token_types.items():
        print(f"  {token_type.value}: {count}")

    return len(tokens) > 0


def test_theme_support():
    """Test theme support"""
    print("\n" + "=" * 50)
    print("Test 2: Theme support")
    print("=" * 50)

    compiler = SyntaxHighlightCompiler()

    # Test default theme
    default_theme = compiler.current_theme
    print(f"Default theme: {default_theme.name}")
    print(f"Keyword color: {default_theme.colors[TokenType.KEYWORD]}")

    # Test switching themes
    success = compiler.set_theme("light")
    print(f"Switched to light theme: {success}")
    print(f"Keyword color: {compiler.current_theme.colors[TokenType.KEYWORD]}")

    # Test custom theme
    custom_theme = Theme(
        name="custom",
        colors={
            TokenType.KEYWORD: "#FF0000",
            TokenType.STRING: "#00FF00",
            TokenType.NUMBER: "#0000FF",
            TokenType.COMMENT: "#808080",
            TokenType.IDENTIFIER: "#FFFFFF",
            TokenType.OPERATOR: "#FFFF00",
            TokenType.PUNCTUATION: "#FFFFFF",
            TokenType.WHITESPACE: "#FFFFFF",
            TokenType.BUILTIN: "#FF00FF",
            TokenType.FUNCTION: "#00FFFF",
            TokenType.CLASS: "#FFA500",
            TokenType.TYPE: "#800080",
            TokenType.ANNOTATION: "#FFD700",
            TokenType.ERROR: "#FF0000",
            TokenType.UNKNOWN: "#C0C0C0",
        },
    )
    compiler.add_theme(custom_theme)
    success = compiler.set_theme("custom")
    print(f"Added and set custom theme: {success}")

    return success


def test_hcl_generation():
    """Test HCL generation"""
    print("\n" + "=" * 50)
    print("Test 3: HCL generation")
    print("=" * 50)

    compiler = SyntaxHighlightCompiler()
    compiler.set_theme("default_dark")

    python_code = '''def fibonacci(n):
    """Calculate the nth Fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Test the function
for i in range(10):
    print(f"fibonacci({i}) = {fibonacci(i)}")
'''

    success, hcl_content = compiler.compile_code_to_hcl(python_code, "python")

    if success:
        print("✓ HCL generation successful!")
        print(f"Generated {len(hcl_content.splitlines())} lines of HCL")
        print("\nFirst 10 lines of HCL:")
        for i, line in enumerate(hcl_content.splitlines()[:10]):
            print(f"{i + 1:2}: {line}")

        # Save HCL for testing with drawj2d
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hcl", delete=False) as f:
            f.write(hcl_content)
            hcl_path = f.name

        print(f"\nSaved HCL to: {hcl_path}")

        # Test with drawj2d
        drawj2d = Drawj2dService()
        success, result = drawj2d.process_hcl(hcl_path)

        if success:
            print("✓ drawj2d processing successful!")
            print(f"Output file: {result['output_path']}")
            if "file_size" in result:
                print(f"File size: {result['file_size']} bytes")
            else:
                # Get file size directly
                import os

                file_size = os.path.getsize(result["output_path"])
                print(f"File size: {file_size} bytes")
        else:
            print(f"✗ drawj2d processing failed: {result}")
    else:
        print(f"✗ HCL generation failed: {hcl_content}")

    return success


def test_javascript_support():
    """Test JavaScript language support"""
    print("\n" + "=" * 50)
    print("Test 4: JavaScript support")
    print("=" * 50)

    compiler = SyntaxHighlightCompiler()

    js_code = """// Calculate factorial
function factorial(n) {
    if (n === 0 || n === 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

// Test the function
const numbers = [0, 1, 2, 3, 4, 5];
numbers.forEach(num => {
    console.log(`${num}! = ${factorial(num)}`);
});
"""

    success, hcl_content = compiler.compile_code_to_hcl(js_code, "javascript", "light")

    if success:
        print("✓ JavaScript compilation successful!")
        print(f"Generated {len(hcl_content.splitlines())} lines of HCL")
    else:
        print(f"✗ JavaScript compilation failed: {hcl_content}")

    return success


def main():
    """Run all tests"""
    print("=" * 50)
    print("Testing Syntax Highlight Compiler - Phase 2")
    print("=" * 50)

    tests = [
        ("Tokenization", test_tokenization),
        ("Theme Support", test_theme_support),
        ("HCL Generation", test_hcl_generation),
        ("JavaScript Support", test_javascript_support),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} failed with error: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")

    total_passed = sum(1 for _, result in results if result)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n✓ All tests passed! Phase 2 is complete.")
    else:
        print("\n✗ Some tests failed. Please check the logs.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
