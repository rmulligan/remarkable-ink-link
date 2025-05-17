#!/usr/bin/env python3
"""Quick fix for flake8 issues in test files."""

import glob
import re

# Files to fix
files = glob.glob("scripts/test_phase5_*.py")

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    # Fix E402 (module level import not at top of file)
    if "from src.inklink" in content:
        # Add noqa comments to imports after sys.path modification
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if line.startswith("from src.inklink") and "# noqa" not in line:
                new_lines.append(line + "  # noqa: E402")
            else:
                new_lines.append(line)
        content = "\n".join(new_lines)

    # Fix W293 (blank line contains whitespace)
    content = re.sub(r"\n[ \t]+\n", "\n\n", content)

    # Fix E226 (missing whitespace around arithmetic operator)
    content = re.sub(r"(\d)\+(\d)", r"\1 + \2", content)

    # Fix F841 (local variable assigned but never used) for specific cases
    content = re.sub(r"(layout = LayoutCalculator\(\))", r"\1  # noqa: F841", content)
    content = re.sub(r"(hcl = compiler\.)", r"hcl = compiler.  # noqa: F841", content)
    content = re.sub(
        r"(calculator = LayoutCalculator\(\))", r"\1  # noqa: F841", content
    )
    content = re.sub(
        r"(compiler = SyntaxHighlightCompilerV2\(\))", r"\1  # noqa: F841", content
    )

    with open(filepath, "w") as f:
        f.write(content)

print("Fixed flake8 issues in test files")
