#!/usr/bin/env python3
"""Test script for Phase 3: Enhanced Scanner with Regex Pattern Matching"""
import logging
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the path to import inklink
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.inklink.services.drawj2d_service import Drawj2dService  # noqa: E402
from src.inklink.services.syntax_highlight_compiler import (  # noqa: E402
    SyntaxHighlightCompiler,
)
from src.inklink.services.syntax_scanner import (  # noqa: E402
    JavaScriptScanner,
    PythonScanner,
)
from src.inklink.services.syntax_tokens import TokenType  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_python_scanner():
    """Test the enhanced Python scanner."""
    print("\n" + "=" * 50)
    print("Test 1: Python Scanner")
    print("=" * 50)

    scanner = PythonScanner()

    # Test various Python constructs
    python_code = """# This is a comment
import os
from typing import List, Dict

@dataclass
class Person:
    '''A person with a name and age'''
    name: str
    age: int = 0

    def greet(self) -> str:
        \"\"\"Return a greeting message.\"\"\"
        return f"Hello, my name is {self.name}!"

# Multi-line string
story = \"\"\"
Once upon a time,
in a land far away...
\"\"\"

# Numbers and operators
pi = 3.14159
hex_val = 0xFF
binary = 0b1010
result = (pi * 2) ** 2

# List comprehension
squares = [x**2 for x in range(10) if x % 2 == 0]

# Function with complex logic
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Try-except block
try:
    data = json.loads('{"key": "value"}')
except ValueError as e:
    print(f"Error: {e}")
"""

    tokens = scanner.scan(python_code)

    # Print token statistics
    token_counts = {}
    for token in tokens:
        token_counts[token.type] = token_counts.get(token.type, 0) + 1

    print(f"Total tokens: {len(tokens)}")
    print("\nToken distribution:")
    for token_type, count in sorted(
        token_counts.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {token_type.value}: {count}")

    # Show some specific tokens
    print("\nSample tokens:")
    for i, token in enumerate(tokens[:30]):
        if token.type != TokenType.WHITESPACE:
            print(f"{i:3}: {token.type.value:12} '{token.value}'")

    return len(tokens) > 100


def test_javascript_scanner():
    """Test the enhanced JavaScript scanner."""
    print("\n" + "=" * 50)
    print("Test 2: JavaScript Scanner")
    print("=" * 50)

    scanner = JavaScriptScanner()

    js_code = """// Modern JavaScript example
import React, { useState, useEffect } from 'react';

/* Multi-line comment
   explaining the component */
const MyComponent = ({ name, age }) => {
    const [count, setCount] = useState(0);

    useEffect(() => {
        console.log(`Component mounted for ${name}`);
        return () => console.log('Cleanup');
    }, [name]);

    // Template literal
    const message = `Hello ${name}, you are ${age} years old!`;

    // Arrow function
    const increment = () => setCount(prev => prev + 1);

    // Async function
    async function fetchData(url) {
        try {
            const response = await fetch(url);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Fetch failed:', error);
        }
    }

    // Regular expression
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$/;

    return (
        <div>
            <h1>{message}</h1>
            <button onClick={increment}>Count: {count}</button>
        </div>
    );
};

export default MyComponent;
"""

    tokens = scanner.scan(js_code)

    # Print token statistics
    token_counts = {}
    for token in tokens:
        token_counts[token.type] = token_counts.get(token.type, 0) + 1

    print(f"Total tokens: {len(tokens)}")
    print("\nToken distribution:")
    for token_type, count in sorted(
        token_counts.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {token_type.value}: {count}")

    return len(tokens) > 100


def test_multiline_strings():
    """Test multiline string handling."""
    print("\n" + "=" * 50)
    print("Test 3: Multiline String Handling")
    print("=" * 50)

    scanner = PythonScanner()

    code = """
# Triple-quoted strings
doc = \"\"\"This is a
multi-line
documentation string\"\"\"

sql = '''
    SELECT * FROM users
    WHERE age > 21
    ORDER BY name
'''

# Nested quotes
nested = \"\"\"He said, "It's working!" and smiled.\"\"\"
"""

    tokens = scanner.scan(code)

    # Find string tokens
    string_tokens = [t for t in tokens if t.type == TokenType.STRING]
    print(f"Found {len(string_tokens)} string tokens:")
    for i, token in enumerate(string_tokens):
        lines = token.value.count("\n")
        print(f"{i + 1}. Lines: {lines + 1}, Length: {len(token.value)}")
        print(f"   Preview: {repr(token.value[:50])}...")

    return len(string_tokens) >= 3


def test_enhanced_compiler():
    """Test the compiler with enhanced scanner."""
    print("\n" + "=" * 50)
    print("Test 4: Enhanced Compiler Integration")
    print("=" * 50)

    compiler = SyntaxHighlightCompiler()

    # Complex Python code with various constructs
    python_code = """
import asyncio
from dataclasses import dataclass

@dataclass
class Config:
    host: str = "localhost"
    port: int = 8080

async def main():
    # Configure server
    config = Config(port=9000)

    # Lambda function
    square = lambda x: x ** 2

    # List comprehension with multiple conditions
    results = [
        square(x) for x in range(100)
        if x % 2 == 0 and x > 10
    ]

    print(f"Server: {config.host}:{config.port}")
    print(f"Results: {results[:5]}...")

if __name__ == "__main__":
    asyncio.run(main())
"""

    # Compile to HCL
    success, hcl_content = compiler.compile_code_to_hcl(python_code, "python")

    if success:
        print("✓ Enhanced compilation successful!")
        print(f"Generated {len(hcl_content.splitlines())} lines of HCL")

        # Test with drawj2d
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hcl", delete=False) as f:
            f.write(hcl_content)
            hcl_path = f.name

        drawj2d = Drawj2dService()
        success, result = drawj2d.process_hcl(hcl_path)

        if success:
            print("✓ drawj2d processing successful!")
            print(f"Output file: {result['output_path']}")
            if "file_size" in result:
                print(f"File size: {result['file_size']} bytes")
            else:
                import os

                file_size = os.path.getsize(result["output_path"])
                print(f"File size: {file_size} bytes")
        else:
            print(f"✗ drawj2d processing failed: {result}")
    else:
        print(f"✗ Compilation failed: {hcl_content}")

    return success


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 50)
    print("Test 5: Edge Cases")
    print("=" * 50)

    scanner = PythonScanner()

    # Code with various edge cases
    edge_cases = """
# Empty strings
empty1 = ""
empty2 = ''

# Escaped quotes
escaped = "She said, \\"Hello!\\" and left."

# Unicode
unicode_str = "Hello, 世界! 🌍"

# Complex numbers
complex_num = 3.14j

# Underscores in numbers (Python 3.6+)
big_number = 1_000_000

# Raw strings
raw_path = r"C:\\Users\\Documents\\file.txt"

# F-string with expressions
name = "Alice"
f_string = f"User: {name.upper()}"

# Unclosed string (error case)
# unclosed = "This string never ends...
"""

    tokens = scanner.scan(edge_cases)

    # Look for interesting tokens
    print("Interesting tokens found:")
    for token in tokens:
        if token.type in [
            TokenType.STRING,
            TokenType.NUMBER,
            TokenType.ERROR,
            TokenType.UNKNOWN,
        ]:
            print(f"  {token.type.value}: {repr(token.value)}")

    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("Testing Enhanced Scanner - Phase 3")
    print("=" * 50)

    tests = [
        ("Python Scanner", test_python_scanner),
        ("JavaScript Scanner", test_javascript_scanner),
        ("Multiline Strings", test_multiline_strings),
        ("Enhanced Compiler", test_enhanced_compiler),
        ("Edge Cases", test_edge_cases),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} failed with error: {e}")
            import traceback

            traceback.print_exc()
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
        print("\n✓ All tests passed! Phase 3 scanner is working correctly.")
    else:
        print("\n✗ Some tests failed. Please check the logs.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
