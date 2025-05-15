#!/usr/bin/env python3
"""Script to resolve formatting conflicts automatically."""

import os
import re
import sys


def resolve_conflicts(file_path):
    """Resolve conflicts in a single file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Pattern to match conflict markers
    conflict_pattern = r"<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> ed7dcda.*?\n"

    # Find all conflicts
    conflicts = list(re.finditer(conflict_pattern, content, re.DOTALL))

    if not conflicts:
        return False

    print(f"Found {len(conflicts)} conflicts in {file_path}")

    # Resolve conflicts by taking the incoming (formatting) changes
    for match in reversed(conflicts):
        head_content = match.group(1)
        incoming_content = match.group(2)
        # Take the incoming content (the formatted version)
        content = content[: match.start()] + incoming_content + content[match.end() :]

    # Handle the special nested conflict pattern
    nested_pattern = r"<<<<<<< HEAD\n(.*?)<< << << < HEAD\n== == == =\n>>>>>> > [a-f0-9]+.*?\n\n=======\n(.*?)>>>>>>> ed7dcda.*?\n"
    nested_conflicts = list(re.finditer(nested_pattern, content, re.DOTALL))

    for match in reversed(nested_conflicts):
        # Take the cleaned version without conflict markers
        content = content[: match.start()] + match.group(1) + content[match.end() :]

    # Clean up any remaining conflict markers
    content = re.sub(
        r"<< << << < HEAD\n== == == =\n>>>>>> > [a-f0-9]+.*?\n", "", content
    )

    with open(file_path, "w") as f:
        f.write(content)

    return True


def main():
    """Main function to resolve conflicts in all files."""
    # Get list of files with conflicts
    result = os.popen("git status --porcelain").read()
    conflicted_files = []

    for line in result.split("\n"):
        if line.startswith("UU "):
            file_path = line[3:].strip()
            conflicted_files.append(file_path)

    if not conflicted_files:
        print("No conflicted files found")
        return

    print(f"Found {len(conflicted_files)} conflicted files")

    for file_path in conflicted_files:
        if os.path.exists(file_path):
            if resolve_conflicts(file_path):
                print(f"Resolved conflicts in {file_path}")
                os.system(f"git add {file_path}")


if __name__ == "__main__":
    main()
