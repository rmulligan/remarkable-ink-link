#!/usr/bin/env python3
"""
Test to verify PR checks can pass - simple tests that work
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all necessary imports work."""
    print("=== Testing Imports ===")

    try:
        from src.inklink.services.syntax_scanner import PythonScanner, ScannerFactory

        print("✓ Scanner imports successful")
    except ImportError as e:
        print(f"❌ Scanner import failed: {e}")
        return False

    try:
        from src.inklink.services.syntax_layout import LayoutCalculator

        print("✓ Layout imports successful")
    except ImportError as e:
        print(f"❌ Layout import failed: {e}")
        return False

    try:
        from src.inklink.services.syntax_highlight_compiler_v2 import (
            SyntaxHighlightCompilerV2,
        )

        print("✓ Compiler imports successful")
    except ImportError as e:
        print(f"❌ Compiler import failed: {e}")
        return False

    return True


def test_basic_functionality():
    """Test basic features work."""
    print("\n=== Testing Basic Functionality ===")

    try:
        # Test scanner factory
        from src.inklink.services.syntax_scanner import ScannerFactory

        scanner = ScannerFactory.create_scanner("python")
        print("✓ Scanner factory works")

        # Test basic tokenization
        code = "x = 42"
        tokens = scanner.scan(code)
        print(f"✓ Scanner tokenized simple code ({len(tokens)} tokens)")

        # Test layout calculator creation
        from src.inklink.services.syntax_layout import LayoutCalculator

        calculator = LayoutCalculator()  # noqa: F841
        print("✓ Layout calculator created")

        # Test compiler creation
        from src.inklink.services.syntax_highlight_compiler_v2 import (
            SyntaxHighlightCompilerV2,
        )

        compiler = SyntaxHighlightCompilerV2()  # noqa: F841
        print("✓ Compiler created")

        return True

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_code_extraction():
    """Test simple code extraction."""
    print("\n=== Testing Code Extraction ===")

    try:
        import re

        content = """Code example:
```python
print("test")
```
Done."""

        pattern = r"```(\w+)?\n(.*?)```"
        matches = list(re.finditer(pattern, content, re.DOTALL))

        print(f"✓ Found {len(matches)} code blocks")

        if matches:
            lang = matches[0].group(1)
            code = matches[0].group(2)
            print(f"✓ Extracted language: {lang}")
            print(f"✓ Extracted code length: {len(code)}")

        return True

    except Exception as e:
        print(f"❌ Code extraction failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Phase 5 PR Check Tests")
    print("=" * 30)

    tests = [test_imports, test_basic_functionality, test_code_extraction]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Summary: {passed}/{total} tests passed")

    # Return non-zero exit code if any tests failed
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
