#!/usr/bin/env python3
"""Script to check if a notebook has specific tags."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile


def main():
    """Main function to check notebook tags."""
    if len(sys.argv) < 2:
        print("Usage: python check_tags.py <notebook_name> [tag]")
        sys.exit(1)

    notebook_name = sys.argv[1]
    tag_to_check = sys.argv[2] if len(sys.argv) > 2 else "Lilly"

    print(f"Checking if notebook '{notebook_name}' has tag '{tag_to_check}'...")

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Try to download the notebook
        cmd = f'./local-rmapi get "{notebook_name}" "{temp_dir}"'
        print(f"Running command: {cmd}")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            print(f"Command output: {result.stdout}")
            print(f"Command error: {result.stderr}")

            if result.returncode != 0:
                print(f"Failed to download notebook: {result.stderr}")
                return

            # List contents of the temp directory
            print(f"Files in temp directory: {os.listdir(temp_dir)}")

            # Look for .content files
            content_files = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".content"):
                        content_files.append(os.path.join(root, file))

            if not content_files:
                print("No content files found in the notebook.")
                # Check for .rmdoc files
                rmdoc_files = []
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith(".rmdoc"):
                            rmdoc_files.append(os.path.join(root, file))

                if rmdoc_files:
                    print(f"Found .rmdoc file: {rmdoc_files[0]}")
                    # Try to extract it
                    rmdoc_path = rmdoc_files[0]
                    rmdoc_extract_dir = os.path.join(temp_dir, "extracted")
                    os.makedirs(rmdoc_extract_dir, exist_ok=True)

                    if zipfile.is_zipfile(rmdoc_path):
                        print(f"Extracting {rmdoc_path}...")
                        with zipfile.ZipFile(rmdoc_path, "r") as zip_ref:
                            zip_ref.extractall(rmdoc_extract_dir)

                        # Look for content files again
                        for root, _, files in os.walk(rmdoc_extract_dir):
                            for file in files:
                                if file.endswith(".content"):
                                    content_files.append(os.path.join(root, file))
                    else:
                        print(f"File is not a valid zip file: {rmdoc_path}")
                        with open(rmdoc_path, "rb") as f:
                            header = f.read(20)
                        print(f"File header: {header}")

            if not content_files:
                print("No content files found after extraction attempts.")
                return

            # Process each content file
            for content_file in content_files:
                print(f"Processing content file: {content_file}")

                try:
                    with open(content_file, "r") as f:
                        content_data = json.load(f)

                    # Check document-level tags
                    doc_tags = content_data.get("tags", [])
                    print(f"Document-level tags: {doc_tags}")

                    if tag_to_check in doc_tags:
                        print(f"✅ Found tag '{tag_to_check}' at document level")

                    # Check page-level tags
                    if "pages" in content_data:
                        for i, page in enumerate(content_data["pages"]):
                            page_tags = page.get("tags", [])
                            page_name = page.get("visibleName", f"Page {i}")

                            print(f"Page '{page_name}' tags: {page_tags}")

                            if tag_to_check in page_tags:
                                print(
                                    f"✅ Found tag '{tag_to_check}' in page '{page_name}'"
                                )

                            # Also check for hashtags in text content
                            # Note: This would require accessing the actual page content

                except Exception as e:
                    print(f"Error processing content file: {e}")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
