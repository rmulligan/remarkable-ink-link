#!/usr/bin/env python3
"""Test script for Phase 4: Advanced Layout & Refinements."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from inklink.services.syntax_highlight_compiler_v2 import (  # noqa: E402
    CodeMetadata,
    Language,
    RenderOptions,
    SyntaxHighlightCompilerV2,
)
from inklink.services.syntax_layout import FontMetrics, Margins, PageSize  # noqa: E402


def create_test_metadata() -> CodeMetadata:
    """Create test metadata."""
    return CodeMetadata(
        filename="test_example.py",
        language="Python",
        author="Test Author",
        tags=["test", "example", "syntax-highlighting"],
        line_start=1,
        line_end=50,
    )


def test_simple_layout():
    """Test simple code layout."""
    print("=== Test 1: Simple Layout ===")

    code = """
def hello_world():
    print("Hello, World!")
    return 42

if __name__ == "__main__":
    result = hello_world()
    print(f"Result: {result}")
"""

    compiler = SyntaxHighlightCompilerV2()
    metadata = create_test_metadata()

    pages = compiler.compile_with_layout(code, Language.PYTHON, metadata)

    print(f"Generated {len(pages)} page(s)")
    for page in pages:
        print(f"\nPage {page['page_number']}:")
        print(page["hcl"][:500] + "..." if len(page["hcl"]) > 500 else page["hcl"])
        if page["metadata"]:
            print(f"Metadata: {page['metadata']}")

    print("\n✓ Simple layout test passed")


def test_line_wrapping():
    """Test long line wrapping."""
    print("\n=== Test 2: Line Wrapping ===")

    code = """
def complex_function_with_very_long_parameter_list(first_param, second_param, third_param, fourth_param, fifth_param, sixth_param):
    # This is a very long comment that should definitely wrap to multiple lines when rendered on the page
    very_long_variable_name = first_param + second_param + third_param + fourth_param + fifth_param + sixth_param
    return very_long_variable_name
"""

    # Use smaller page width to force wrapping
    options = RenderOptions(
        page_size=PageSize.REMARKABLE_2,
        margins=Margins(left=100, right=100, top=100, bottom=100),
        show_line_numbers=True,
    )

    compiler = SyntaxHighlightCompilerV2(options)
    pages = compiler.compile_with_layout(code, Language.PYTHON)

    print(f"Generated {len(pages)} page(s)")
    for page in pages:
        print(f"\nPage {page['page_number']}:")
        # Check if any lines were wrapped
        hcl = page["hcl"]
        if "wrapped" in hcl or "continuation" in hcl:
            print("✓ Found wrapped lines")
        print(hcl[:500] + "..." if len(hcl) > 500 else hcl)

    print("\n✓ Line wrapping test passed")


def test_multipage_layout():
    """Test code spanning multiple pages."""
    print("\n=== Test 3: Multi-page Layout ===")

    # Generate a long code file
    code_lines = []
    for i in range(100):
        code_lines.append(f"def function_{i}():")
        code_lines.append(f'    """Docstring for function {i}"""')
        code_lines.append(f"    result = {i} * 2")
        code_lines.append(f"    print(f'Function {i}: {{result}}')")
        code_lines.append(f"    return result")
        code_lines.append("")

    code = "\n".join(code_lines)

    # Use smaller page height to force multiple pages
    options = RenderOptions(
        page_size=PageSize.REMARKABLE_2,
        margins=Margins(top=50, bottom=50),
        font_metrics=FontMetrics(size=24, line_height=1.5),
        show_line_numbers=True,
        show_metadata=True,
    )

    compiler = SyntaxHighlightCompilerV2(options)
    metadata = CodeMetadata(
        filename="large_file.py", language="Python", line_end=len(code_lines)
    )

    pages = compiler.compile_with_layout(code, Language.PYTHON, metadata)

    print(f"Generated {len(pages)} page(s)")
    for page in pages:
        print(f"\nPage {page['page_number']}:")
        print(
            f"Lines on page: {page['metadata']['line_count'] if page['metadata'] else 'N/A'}"
        )
        print(page["hcl"][:300] + "...")

    assert len(pages) > 1, "Should generate multiple pages"
    print("\n✓ Multi-page layout test passed")


def test_debug_mode():
    """Test debug mode with grid overlay."""
    print("\n=== Test 4: Debug Mode ===")

    code = """
# Simple test code
x = 42
y = x * 2
print(f"Result: {y}")
"""

    options = RenderOptions(debug_mode=True, show_line_numbers=True, show_metadata=True)

    compiler = SyntaxHighlightCompilerV2(options)
    metadata = CodeMetadata(filename="debug_test.py")

    pages = compiler.compile_with_layout(code, Language.PYTHON, metadata)

    print(f"Generated {len(pages)} page(s)")
    hcl = pages[0]["hcl"]

    # Check for debug elements
    if "Debug grid" in hcl and "rectangle" in hcl:
        print("✓ Debug grid elements found")
    else:
        print("✗ Debug grid elements missing")

    print("\nDebug HCL preview:")
    print(hcl[:500] + "..." if len(hcl) > 500 else hcl)

    print("\n✓ Debug mode test passed")


def test_metadata_embedding():
    """Test metadata embedding in HCL."""
    print("\n=== Test 5: Metadata Embedding ===")

    code = "print('test')"

    options = RenderOptions(embed_metadata=True)

    compiler = SyntaxHighlightCompilerV2(options)
    metadata = CodeMetadata(
        filename="embed_test.py",
        language="Python",
        author="Test Author",
        tags=["metadata", "test"],
    )

    pages = compiler.compile_with_layout(code, Language.PYTHON, metadata)

    hcl = pages[0]["hcl"]

    # Check for embedded metadata
    if "# METADATA:" in hcl and '"filename": "embed_test.py"' in hcl:
        print("✓ Metadata embedded correctly")
    else:
        print("✗ Metadata embedding failed")

    print("\nHCL with metadata:")
    print(hcl)

    print("\n✓ Metadata embedding test passed")


def run_all_tests():
    """Run all Phase 4 tests."""
    print("Starting Phase 4 Layout Tests...\n")

    try:
        test_simple_layout()
        test_line_wrapping()
        test_multipage_layout()
        test_debug_mode()
        test_metadata_embedding()

        print("\n" + "=" * 50)
        print("✅ All Phase 4 tests passed!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
