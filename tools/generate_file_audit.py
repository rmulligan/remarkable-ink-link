#!/usr/bin/env python3
"""
Script to generate a file audit CSV from git status output.
This helps with organizing untracked files in the repository.
"""

import csv
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# File categories and suggested actions
FILE_TYPES = {
    ".py": "py",
    ".md": "md",
    ".sh": "sh",
    ".js": "js",
    ".html": "html",
    ".json": "json",
    ".yml": "yml",
    ".yaml": "yaml",
    ".rmdoc": "rmdoc",
    ".txt": "txt",
    ".lock": "lock",
    ".toml": "toml",
}


def get_file_type(path: str) -> str:
    """Determine file type based on extension."""
    ext = os.path.splitext(path)[1].lower()
    return FILE_TYPES.get(ext, "other")


def suggest_action_and_location(path: str, file_type: str) -> Tuple[str, str]:
    """Suggest action and location based on file path and type."""
    basename = os.path.basename(path)
    dirname = os.path.dirname(path)

    # Default values
    action = "keep-commit"
    suggested_location = dirname if dirname else "."

    # Python files
    if file_type == "py":
        if basename.startswith("test_"):
            if not dirname.startswith("tests"):
                suggested_location = "tests"
                action = "move"
        elif basename.startswith("create_") or basename.startswith("run_"):
            suggested_location = "scripts"
            action = "move"

    # Documentation files
    elif file_type == "md":
        if "SUMMARY" in basename or "README" in basename:
            suggested_location = "docs"
            action = "move"

    # Shell scripts
    elif file_type == "sh":
        suggested_location = "scripts"
        action = "move"

    # Temporary and data files
    elif any(x in basename for x in ["temp", "test", "debug"]):
        action = "ignore"

    # Notebook files
    elif file_type == "rmdoc":
        suggested_location = "notebooks"
        action = "move"

    return action, suggested_location


def parse_git_status(status_file: str) -> List[Dict]:
    """Parse git status output to extract untracked files."""
    results = []

    with open(status_file, "r") as f:
        content = f.read()

    # Extract untracked files section
    untracked_match = re.search(
        r"Untracked files:.*?\n(.*?)(?:\n\n|\Z)", content, re.DOTALL
    )

    if not untracked_match:
        print("No untracked files found or unexpected git status format")
        return results

    # Process each untracked file
    untracked_section = untracked_match.group(1)
    file_lines = re.findall(r"^\s+(.+)$", untracked_section, re.MULTILINE)

    for file_path in file_lines:
        # Clean up the path (git status might add quotes or indicators)
        clean_path = file_path.strip().strip("'\"")
        if clean_path.endswith("/"):
            # For directories, we'll add a placeholder noting it's a directory
            clean_path = clean_path[:-1]
            file_type = "directory"
        else:
            file_type = get_file_type(clean_path)

        action, suggested_location = suggest_action_and_location(clean_path, file_type)

        results.append(
            {
                "path": clean_path,
                "type": file_type,
                "suggested_action": action,
                "current_location": os.path.dirname(clean_path) or ".",
                "suggested_location": suggested_location,
            }
        )

    return results


def write_audit_csv(data: List[Dict], output_file: str) -> None:
    """Write the audit data to a CSV file."""
    fieldnames = [
        "path",
        "type",
        "suggested_action",
        "current_location",
        "suggested_location",
    ]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"Audit file written to {output_file}")


def main():
    """Main function to generate the file audit CSV."""
    script_dir = Path(__file__).parent

    input_file = script_dir / "file_audit.txt"
    output_file = script_dir / "file_audit.csv"

    if not input_file.exists():
        print(f"Error: Input file {input_file} not found")
        sys.exit(1)

    audit_data = parse_git_status(str(input_file))
    if audit_data:
        write_audit_csv(audit_data, str(output_file))
        print(f"Generated audit file with {len(audit_data)} entries")
    else:
        print("No files to process")


if __name__ == "__main__":
    main()
