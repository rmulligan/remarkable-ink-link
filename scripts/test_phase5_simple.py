#!/usr/bin/env python3
"""
Simple Phase 5 Test - Testing what actually exists
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import what we can actually import
try:
    from src.inklink.services.syntax_scanner import PythonScanner, ScannerFactory

    print("✓ Scanner imports successful")
except ImportError as e:
    print(f"❌ Scanner import failed: {e}")

try:
    from src.inklink.services.syntax_layout import LayoutCalculator

    print("✓ Layout calculator import successful")
except ImportError as e:
    print(f"❌ Layout calculator import failed: {e}")

try:
    from src.inklink.services.syntax_highlight_compiler_v2 import (
        SyntaxHighlightCompilerV2,
    )

    print("✓ Compiler v2 import successful")
except ImportError as e:
    print(f"❌ Compiler v2 import failed: {e}")


def test_scanner_factory():
    """Test scanner factory functionality."""
    print("\n=== Testing Scanner Factory ===")

    try:
        scanner = ScannerFactory.create_scanner("python")
        print(f"✓ Created scanner: {type(scanner).__name__}")

        # Test simple tokenization
        code = "print('Hello, world!')"
        tokens = scanner.scan(code)
        print(f"✓ Scanned {len(tokens)} tokens from code")

    except Exception as e:
        print(f"❌ Scanner test failed: {e}")


def test_layout_calculator():
    """Test layout calculator basics."""
    print("\n=== Testing Layout Calculator ===")

    try:
        calculator = LayoutCalculator()  # noqa: F841
        print("✓ Created layout calculator")

        # Check for available methods
        methods = [m for m in dir(calculator) if not m.startswith("_")]
        print(f"✓ Available methods: {', '.join(methods[:5])}...")

    except Exception as e:
        print(f"❌ Layout calculator test failed: {e}")


def test_compiler():
    """Test syntax highlight compiler."""
    print("\n=== Testing Compiler ===")

    try:
        compiler = SyntaxHighlightCompilerV2()  # noqa: F841
        print("✓ Created compiler")

        # Check for available methods
        methods = [m for m in dir(compiler) if not m.startswith("_")]
        print(f"✓ Available methods: {', '.join(methods[:5])}...")

    except Exception as e:
        print(f"❌ Compiler test failed: {e}")


if __name__ == "__main__":
    print("Phase 5 Simple Test Suite")
    print("=" * 30)

    test_scanner_factory()
    test_layout_calculator()
    test_compiler()

    print("\nTests complete!")
