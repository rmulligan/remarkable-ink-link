#!/usr/bin/env python3
"""
Script to organize test files into appropriate test directories based on their content.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Define categories and their patterns
CATEGORIES = {
    "adapters": [r"adapter", r"rmapi", r"handwriting", r"claude_vision", r"limitless"],
    "api": [r"api", r"route", r"endpoint", r"http", r"web"],
    "integration": [r"integration", r"live", r"e2e", r"end.to.end"],
    "extraction": [r"extract", r"rmdoc", r"notebook", r"rmscene"],
    "services": [r"service", r"converter", r"document", r"ai_service"],
    "mocks": [r"mock", r"stub", r"fake"],
}


def determine_category(file_path: str) -> str:
    """Determine the category of a test file based on its content."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Extract imports to help determine category
    imports = re.findall(r"import\s+([^\n]+)", content)
    imports.extend(re.findall(r"from\s+([^\s]+)\s+import", content))

    # Check file content against category patterns
    for category, patterns in CATEGORIES.items():
        for pattern in patterns:
            # Check in imports and content
            if any(
                re.search(pattern, imp, re.IGNORECASE) for imp in imports
            ) or re.search(pattern, content, re.IGNORECASE):
                return category

    # Default to mocks category if unclear
    return "mocks"


def find_test_files(directory: str) -> List[str]:
    """Find all test_*.py files in the given directory."""
    return [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.startswith("test_")
        and f.endswith(".py")
        and os.path.isfile(os.path.join(directory, f))
    ]


def create_init_files(test_dirs: List[str]) -> None:
    """Create __init__.py files in test directories if they don't exist."""
    for test_dir in test_dirs:
        init_file = os.path.join(test_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# Test directory initialization\n")
            print(f"Created {init_file}")


def organize_test_files(root_dir: str) -> Dict[str, List[str]]:
    """
    Organize test files from the root directory into appropriate test subdirectories.
    Returns a dictionary mapping categories to lists of moved files.
    """
    test_files = find_test_files(root_dir)
    if not test_files:
        print("No test files found in the root directory.")
        return {}

    results = {category: [] for category in CATEGORIES}
    base_test_dir = os.path.join(root_dir, "tests")

    # Create test directories if they don't exist
    test_dirs = [
        os.path.join(base_test_dir, category) for category in CATEGORIES
    ]
    for test_dir in test_dirs:
        os.makedirs(test_dir, exist_ok=True)

    # Create __init__.py files
    create_init_files([base_test_dir] + test_dirs)

    # Process each test file
    for test_file in test_files:
        category = determine_category(test_file)
        dest_dir = os.path.join(base_test_dir, category)

        filename = os.path.basename(test_file)
        dest_path = os.path.join(dest_dir, filename)

        # Handle potential conflicts
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(os.path.join(dest_dir, f"{base}_{i}{ext}")):
                i += 1
            dest_path = os.path.join(dest_dir, f"{base}_{i}{ext}")

        # Move the file
        shutil.move(test_file, dest_path)
        results[category].append((test_file, dest_path))
        print(f"Moved {test_file} -> {dest_path}")

    return results


def main():
    """Main function to organize test files."""
    script_dir = Path(__file__).parent.parent
    root_dir = str(script_dir)

    print(f"Organizing test files in {root_dir}...")
    results = organize_test_files(root_dir)

    # Print summary
    total = sum(len(files) for files in results.values())
    print(f"\nSummary: Organized {total} test files")
    for category, files in results.items():
        if files:
            print(f"  - {category}: {len(files)} files")


if __name__ == "__main__":
    main()
