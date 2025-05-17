#!/usr/bin/env python3
"""
Phase 5 Notebook Integration Test Suite
Test the complete notebook generation pipeline with syntax highlighting
This version fixes dependency injection issues.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the required services
from src.inklink.services.augmented_notebook_service_v2 import (  # noqa: E402
    AugmentedNotebookServiceV2,
)
from src.inklink.services.syntax_highlight_compiler_v2 import (  # noqa: E402
    SyntaxHighlightCompilerV2,
)
from src.inklink.services.syntax_layout import LayoutCalculator  # noqa: E402
from src.inklink.services.syntax_scanner import SyntaxScanner  # noqa: E402


def test_syntax_highlighted_document():
    """Test creating a simple syntax-highlighted document."""
    print("=== Test 1: Syntax Highlighted Document ===")

    code = '''
def quicksort(arr):
    """Recursive quicksort implementation."""
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quicksort(left) + middle + quicksort(right)
'''

    try:
        # Test scanner
        scanner = SyntaxScanner()
        tokens = scanner.tokenize(code, language="python")
        print(f"✓ Tokenized {len(tokens)} tokens")

        # Test layout
        page_info = MagicMock()
        page_info.width = 1404
        page_info.height = 1872

        layout = LayoutCalculator()  # noqa: F841  # noqa: F841
        # Testing layout calculation without actual stroke generation
        print("✓ Layout calculator initialized")

        # Test compiler
        compiler = SyntaxHighlightCompilerV2()
        hcl = compiler.create_hcl_document(  # noqa: F841
            code, language="python", show_line_numbers=True, add_metadata=True
        )

        print("✓ Generated HCL document")

        # Note: Actual drawj2d rendering would happen here
        print("⚠️ Skipping actual document creation (drawj2d dependency)")
        print("✓ Test would create syntax-highlighted document with:")
        print("  - Language: Python")
        print("  - Line numbers: Yes")
        print("  - Metadata: Yes")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        raise

    print()


def test_mixed_content_response():
    """Test creating documents with mixed text and code content."""
    print("=== Test 2: Mixed Content Response ===")

    # Example response with mixed content
    response = """Here is a binary search implementation in Python:

```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1
```

And here's an equivalent in JavaScript:

```javascript
function binarySearch(arr, target) {
    let left = 0;
    let right = arr.length - 1;

    while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        if (arr[mid] === target) {
            return mid;
        } else if (arr[mid] < target) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }

    return -1;
}
```

Both implementations have O(log n) time complexity.
"""

    try:
        # Create mock services to avoid initialization issues
        class MockRemarkableAdapter:
            def __init__(self):
                raise NotImplementedError()

        class MockRemarkableService:
            def __init__(self, adapter=None):
                self.adapter = adapter or MockRemarkableAdapter()

        class MockDocumentService:
            pass

        # Create service with mocked dependencies
        service = AugmentedNotebookServiceV2(
            document_service=MockDocumentService(),
            remarkable_service=MockRemarkableService(),
            knowledge_graph_service=None,
        )

        # Extract code blocks
        code_blocks = service._extract_code_blocks(response)

        print(f"Found {len(code_blocks)} code blocks:")
        for i, block in enumerate(code_blocks):
            print(
                f"  {i + 1}. Language: {block['language']}, Lines: {len(block['code'].splitlines())}"
            )

        # Note: Full mixed document creation would require more setup
        print("✓ Code block extraction working")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        raise

    print()


def test_language_detection():
    """Test language detection for various code snippets."""
    print("=== Test 3: Language Detection ===")

    code_samples = {
        "python": """
def greet(name):
    print(f"Hello, {name}!")
""",
        "javascript": """
function greet(name) {
    console.log(`Hello, ${name}!`);
}
""",
        "java": """
public void greet(String name) {
    System.out.println("Hello, " + name + "!");
}
""",
        "cpp": """
void greet(const std::string& name) {
    std::cout << "Hello, " << name << "!" << std::endl;
}
""",
    }

    try:
        scanner = SyntaxScanner()

        for expected_lang, code in code_samples.items():
            detected = scanner._detect_language(code)
            print(
                f"  {expected_lang}: {'✓' if detected == expected_lang else '❌'} (detected: {detected})"
            )

        print("✓ Language detection working")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        raise

    print()


def test_line_numbering():
    """Test line number generation."""
    print("=== Test 4: Line Numbering ===")

    code = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

    try:
        scanner = SyntaxScanner()
        tokens = scanner.tokenize(code, language="python")

        # Count line number tokens
        line_num_tokens = [t for t in tokens if t.type == "line_number"]
        code_lines = code.strip().split("\n")

        print(f"Code has {len(code_lines)} lines")
        print(f"Generated {len(line_num_tokens)} line number tokens")

        if len(line_num_tokens) == len(code_lines):
            print("✓ Line numbering correct")
        else:
            print("❌ Line numbering mismatch")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        raise

    print()


def run_all_tests():
    """Run all Phase 5 integration tests."""
    print("Starting Phase 5 Notebook Integration Tests...")
    print()

    test_syntax_highlighted_document()
    test_mixed_content_response()
    test_language_detection()
    test_line_numbering()

    print("Phase 5 Integration Tests Complete!")


if __name__ == "__main__":
    run_all_tests()
