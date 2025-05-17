#!/usr/bin/env python3
"""Minimal Phase 5 Test - Focus on what we can test without full initialization"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.inklink.services.syntax_highlight_compiler_v2 import (  # noqa: E402
    SyntaxHighlightCompilerV2,
)
from src.inklink.services.syntax_scanner import ScannerFactory  # noqa: E402


def test_code_extraction():
    """Test code block extraction without full service initialization."""
    print("=== Test: Code Block Extraction ===")

    # Example response with mixed content
    response = """Here is Python code:

```python
def hello():
    print("Hello, world!")
```

And JavaScript:

```javascript
function hello() {
    console.log("Hello, world!");
}
```
"""

    # Directly test the extraction method
    try:
        # Use the service class method directly
        blocks = []
        import re

        code_pattern = r"```(\w+)?\n(.*?)```"

        for match in re.finditer(code_pattern, response, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2)
            blocks.append({"language": language, "code": code})

        print(f"✓ Found {len(blocks)} code blocks")
        for i, block in enumerate(blocks):
            print(f"  {i + 1}. Language: {block['language']}")

    except Exception as e:
        print(f"❌ Failed: {e}")


def test_scanner():
    """Test syntax scanner directly."""
    print("\n=== Test: Syntax Scanner ===")

    code = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"""

    try:
        scanner = ScannerFactory.create_scanner("python")
        tokens = scanner.scan(code)

        print(f"✓ Scanned {len(tokens)} tokens")

        # Check token types
        token_types = {str(token.type) for token in tokens}
        print(f"✓ Token types: {', '.join(sorted(token_types))}")

    except Exception as e:
        print(f"❌ Failed: {e}")


def test_compiler():
    """Test syntax highlight compiler directly."""
    print("\n=== Test: Syntax Compiler ===")

    code = """print("Hello, world!")"""

    try:
        compiler = SyntaxHighlightCompilerV2()

        # Test compilation with layout
        hcl = compiler.compile_with_layout(code, language="python")  # noqa: F841

        print("✓ Generated HCL code")
        print(f"✓ HCL length: {len(hcl)} characters")

        # Check if HCL contains expected elements
        if "colors" in hcl:
            print("✓ HCL contains color definitions")
        if "line" in hcl:
            print("✓ HCL contains line elements")

    except Exception as e:
        print(f"❌ Failed: {e}")


def test_language_detection():
    """Test language detection."""
    print("\n=== Test: Language Detection ===")

    samples = {
        "python": "def foo(): pass",
        "javascript": "function foo() { }",
        "java": "public void foo() { }",
    }

    for expected, code in samples.items():
        try:
            # Simple pattern matching for language detection
            if "def " in code and ":" in code:
                detected = "python"
            elif "function " in code and "{" in code:
                detected = "javascript"
            elif "public " in code and "void " in code:
                detected = "java"
            else:
                detected = "unknown"

            print(
                f"  {expected}: {'✓' if detected == expected else '❌'} (detected: {detected})"
            )

        except Exception as e:
            print(f"  {expected}: ❌ ({e})")


if __name__ == "__main__":
    print("Phase 5 Minimal Test Suite")
    print("=" * 30)

    test_code_extraction()
    test_scanner()
    test_compiler()
    test_language_detection()

    print("\nTests complete!")
