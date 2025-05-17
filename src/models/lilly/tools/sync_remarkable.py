#!/usr/bin/env python3
"""
Sync reMarkable notebooks to Lilly's workspace.
"""

import argparse
import os
import shutil
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

# Configure paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LILLY_DIR = os.path.dirname(SCRIPT_DIR)
WORKSPACE_DIR = os.path.join(LILLY_DIR, "workspace")
SYNC_DIR = os.path.join(WORKSPACE_DIR, "remarkable_sync")

# Ensure sync directory exists
os.makedirs(SYNC_DIR, exist_ok=True)


def run_rmapi_command(command: List[str]) -> str:
    """Run an rmapi command and return the output."""
    try:
        cmd = ["rmapi"] + command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running rmapi command: {e}")
        print(f"Error output: {e.stderr}")
        return ""


def list_notebooks() -> List[Dict[str, Any]]:
    """List all notebooks in the reMarkable cloud."""
    output = run_rmapi_command(["ls", "-d"])

    # Parse the output to extract notebook information
    notebooks = []

    if not output:
        return notebooks

    lines = output.strip().split("\n")
    for line in lines:
        if "[d]" in line:  # Directory/notebook
            parts = line.strip().split()
            if len(parts) >= 2:
                # Extract the ID and name
                id_part = parts[0].strip()
                name = " ".join(parts[1:]).strip()

                if id_part.startswith("[d]"):
                    id_part = id_part[3:].strip()

                notebooks.append({"id": id_part, "name": name, "type": "directory"})
        elif "[f]" in line:  # File
            parts = line.strip().split()
            if len(parts) >= 2:
                # Extract the ID and name
                id_part = parts[0].strip()
                name = " ".join(parts[1:]).strip()

                if id_part.startswith("[f]"):
                    id_part = id_part[3:].strip()

                notebooks.append({"id": id_part, "name": name, "type": "file"})

    return notebooks


def download_notebook(notebook_id: str, output_dir: str) -> str:
    """Download a notebook from reMarkable cloud."""
    # Create a directory for this notebook
    notebook_dir = os.path.join(output_dir, notebook_id)
    os.makedirs(notebook_dir, exist_ok=True)

    # Download the notebook
    output = run_rmapi_command(["get", notebook_id])

    if not output:
        print(f"Failed to download notebook {notebook_id}")
        return ""

    # Find the downloaded file (likely a .zip or .pdf)
    for file in os.listdir("."):
        if file.endswith(".zip") or file.endswith(".pdf") or file.endswith(".epub"):
            # Move the file to the notebook directory
            shutil.move(file, os.path.join(notebook_dir, file))
            return os.path.join(notebook_dir, file)

    print(f"No downloaded file found for notebook {notebook_id}")
    return ""


def extract_notebook(notebook_path: str) -> str:
    """Extract a reMarkable notebook and render pages."""
    if not notebook_path.endswith(".zip"):
        print(f"Not a zip file: {notebook_path}")
        return ""

    # Directory to extract to
    extract_dir = os.path.splitext(notebook_path)[0] + "_extracted"
    os.makedirs(extract_dir, exist_ok=True)

    # Extract the zip file
    try:
        subprocess.run(
            ["unzip", "-o", notebook_path, "-d", extract_dir],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error extracting notebook: {e}")
        return ""

    return extract_dir


def render_notebook_pages(extract_dir: str) -> List[str]:
    """Render notebook pages to PNG images."""
    rendered_pages = []

    # Find all .rm files in the extracted directory
    rm_files = []
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(".rm"):
                rm_files.append(os.path.join(root, file))

    # Create a directory for rendered pages
    render_dir = os.path.join(os.path.dirname(extract_dir), "rendered_pages")
    os.makedirs(render_dir, exist_ok=True)

    # Try to use rmscene for rendering if available
    for rm_file in rm_files:
        output_png = os.path.join(render_dir, os.path.basename(rm_file) + ".png")

        try:
            # First try rmscene if available
            subprocess.run(
                ["rmscene", "render", rm_file, output_png],
                check=True,
                capture_output=True,
            )
            rendered_pages.append(output_png)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fall back to drawj2d if available
            try:
                subprocess.run(
                    ["drawj2d", rm_file, output_png], check=True, capture_output=True
                )
                rendered_pages.append(output_png)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"Failed to render {rm_file} - no compatible renderer found")

    return rendered_pages


def process_rendered_pages(rendered_pages: List[str]) -> None:
    """Process rendered pages with Lilly's handwriting processing tool."""
    for page in rendered_pages:
        print(f"Processing page: {page}")
        try:
            # Run the handwriting processing tool
            script_path = os.path.join(SCRIPT_DIR, "process_handwriting.py")
            subprocess.run(
                [script_path, page, "--content-type", "mixed", "--kg"], check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Error processing page {page}: {e}")


def main():
    """Main function to sync reMarkable notebooks."""
    parser = argparse.ArgumentParser(
        description="Sync reMarkable notebooks to Lilly's workspace"
    )
    parser.add_argument("--notebook", help="ID of a specific notebook to sync")
    parser.add_argument("--list", action="store_true", help="List available notebooks")
    parser.add_argument(
        "--process", action="store_true", help="Process notebooks after syncing"
    )
    args = parser.parse_args()

    # List notebooks if requested
    if args.list:
        notebooks = list_notebooks()
        print("Available reMarkable notebooks:")
        for i, notebook in enumerate(notebooks):
            print(
                f"{i + 1}. [{notebook['type']}] {notebook['name']} ({notebook['id']})"
            )
        return

    # Sync a specific notebook if requested
    if args.notebook:
        print(f"Syncing notebook {args.notebook}...")
        notebook_path = download_notebook(args.notebook, SYNC_DIR)

        if notebook_path and notebook_path.endswith(".zip"):
            print(f"Extracting notebook {notebook_path}...")
            extract_dir = extract_notebook(notebook_path)

            if extract_dir:
                print("Rendering notebook pages...")
                rendered_pages = render_notebook_pages(extract_dir)

                if args.process and rendered_pages:
                    print(f"Processing {len(rendered_pages)} rendered pages...")
                    process_rendered_pages(rendered_pages)

        print("Notebook sync complete.")
        return

    # Sync all notebooks
    notebooks = list_notebooks()
    print(f"Found {len(notebooks)} reMarkable notebooks.")

    for i, notebook in enumerate(notebooks):
        if notebook["type"] == "directory":
            continue  # Skip directories for now

        print(f"Syncing notebook {i + 1}/{len(notebooks)}: {notebook['name']}...")
        notebook_path = download_notebook(notebook["id"], SYNC_DIR)

        if notebook_path and notebook_path.endswith(".zip"):
            print(f"Extracting notebook {notebook_path}...")
            extract_dir = extract_notebook(notebook_path)

            if extract_dir:
                print("Rendering notebook pages...")
                rendered_pages = render_notebook_pages(extract_dir)

                if args.process and rendered_pages:
                    print(f"Processing {len(rendered_pages)} rendered pages...")
                    process_rendered_pages(rendered_pages)

    print("reMarkable sync complete.")


if __name__ == "__main__":
    main()
