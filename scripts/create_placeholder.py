#!/usr/bin/env python3
"""Create placeholder notebook files with sample content and tags."""

import os
import json
import sys
import uuid


def create_placeholder_notebook(notebook_name, output_dir, add_lilly_tag=True):
    """Create a placeholder notebook with some sample content."""
    # Create the notebook directory
    os.makedirs(output_dir, exist_ok=True)

    # Create a content file
    content_file = os.path.join(output_dir, f"{notebook_name}.content")

    # Create a unique ID for the notebook
    notebook_id = str(uuid.uuid4())

    # Create page IDs
    page1_id = str(uuid.uuid4())
    page2_id = str(uuid.uuid4())

    # Create content data
    content_data = {
        "ID": notebook_id,
        "Version": 2,
        "VissibleName": notebook_name,
        "Type": "DocumentType",
        "pages": [
            {
                "id": page1_id,
                "visibleName": "Page 1",
                "tags": ["Lilly"] if add_lilly_tag else [],
            },
            {"id": page2_id, "visibleName": "Page 2", "tags": ["Context"]},
        ],
        "tags": [],
    }

    # Write content file
    with open(content_file, "w") as f:
        json.dump(content_data, f, indent=2)

    # Create placeholder page files
    pages_dir = os.path.join(output_dir, notebook_id)
    os.makedirs(pages_dir, exist_ok=True)

    # Create .rm files for pages
    for page_id in [page1_id, page2_id]:
        page_file = os.path.join(pages_dir, f"{page_id}.rm")
        with open(page_file, "w") as f:
            f.write(f"Placeholder content for page {page_id}")

    print(f"Created placeholder notebook '{notebook_name}' in {output_dir}")
    print(f"Added Lilly tag to Page 1: {add_lilly_tag}")

    return content_file


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python create_placeholder.py <notebook_name> <output_dir> [add_lilly_tag=True|False]"
        )
        sys.exit(1)

    notebook_name = sys.argv[1]
    output_dir = sys.argv[2]
    add_lilly_tag = True

    if len(sys.argv) > 3:
        add_lilly_tag = sys.argv[3].lower() in ["true", "yes", "1"]

    create_placeholder_notebook(notebook_name, output_dir, add_lilly_tag)
