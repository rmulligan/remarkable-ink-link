#!/usr/bin/env python3
"""Fix unused imports detected by pyflakes."""

import re
import subprocess
import sys


def get_unused_imports():
    """Get all unused imports from pyflakes."""
    result = subprocess.run(
        ["poetry", "run", "pyflakes", "src/"],
        capture_output=True,
        text=True,
        cwd="/home/ryan/dev/remarkable-ink-link",
    )
    lines = result.stdout.strip().split("\n")
    unused_imports = []

    for line in lines:
        match = re.match(r"(.+):(\d+):(\d+): '(.+)' imported but unused", line)
        if match:
            filename, line_num, col_num, import_name = match.groups()
            unused_imports.append(
                {
                    "filename": filename,
                    "line_num": int(line_num),
                    "col_num": int(col_num),
                    "import_name": import_name,
                }
            )

    return unused_imports


def fix_import(filename, line_num, import_name):
    """Remove an unused import from a file."""
    with open(filename, "r") as f:
        lines = f.readlines()

    # Handle edge case where line_num is out of bounds
    if line_num > len(lines) or line_num < 1:
        print(f"Line {line_num} out of bounds for {filename}")
        return False

    line_index = line_num - 1
    line = lines[line_index]

    # Check if this is a simple import line
    if line.strip() == f"import {import_name}":
        # Remove the entire line
        lines.pop(line_index)
    else:
        # Handle complex imports like "from typing import A, B, C"
        # First, try to handle it as a direct match
        pattern = rf"\b{re.escape(import_name)}\b"
        new_line = re.sub(pattern, "", line)

        # Clean up extra commas and spaces
        new_line = re.sub(r",\s*,", ",", new_line)  # Replace ",," with ","
        new_line = re.sub(r",\s*$", "", new_line)  # Remove trailing comma
        new_line = re.sub(r"(\s+)import\s*,", r"\1import", new_line)  # Fix "import ,"
        new_line = re.sub(r"import\s*$", "", new_line)  # Remove empty import

        # If the line becomes empty or just has "from X import", remove it
        if new_line.strip() in ["", "from", "import"] or re.match(
            r"^\s*from\s+\S+\s+import\s*$", new_line
        ):
            lines.pop(line_index)
        else:
            lines[line_index] = new_line

    with open(filename, "w") as f:
        f.writelines(lines)

    return True


def main():
    """Main function to fix all unused imports."""
    unused_imports = get_unused_imports()
    print(f"Found {len(unused_imports)} unused imports")

    # Group by filename to process each file only once
    files_to_fix = {}
    for item in unused_imports:
        filename = item["filename"]
        if filename not in files_to_fix:
            files_to_fix[filename] = []
        files_to_fix[filename].append(item)

    # Process each file
    for filename, imports in files_to_fix.items():
        print(f"Processing {filename} ({len(imports)} unused imports)")
        # Sort by line number in reverse order to avoid line number shifts
        imports.sort(key=lambda x: x["line_num"], reverse=True)

        for imp in imports:
            if fix_import(filename, imp["line_num"], imp["import_name"]):
                print(f"  Fixed: {imp['import_name']} on line {imp['line_num']}")
            else:
                print(
                    f"  Failed to fix: {imp['import_name']} on line {imp['line_num']}"
                )

    print("Done!")


if __name__ == "__main__":
    main()
