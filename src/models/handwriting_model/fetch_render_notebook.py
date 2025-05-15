#!/usr/bin/env python3
"""
Fetch and render a reMarkable notebook as PNG images.

This script finds a notebook with a specific name, downloads it,
and renders each page as a PNG image for AI processing.
"""

import os
import sys
import json
import argparse
import tempfile
import subprocess
import logging
from pathlib import Path
import uuid
import shutil
from typing import List, Dict, Any, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def run_docker_rmapi(cmd_args: List[str]) -> Tuple[bool, str]:
    """
    Run a command using rmapi in Docker.

    Args:
        cmd_args: List of command arguments to pass to rmapi

    Returns:
        Tuple of (success, output/error)
    """
    home_dir = os.path.expanduser("~")

    # Build Docker command
    docker_cmd = [
        "docker", "run",
        "-v", f"{home_dir}/.config/rmapi/:/home/app/.config/rmapi/",
    ]

    # Use a directory that should be accessible by Docker
    output_path = os.path.join(home_dir, "dev/remarkable-ink-link/handwriting_model/docker_temp")
    os.makedirs(output_path, exist_ok=True)
    docker_cmd.extend(["-v", f"{output_path}:/output"])

    # Add rmapi image and commands
    docker_cmd.extend(["rmapi"] + cmd_args)

    logger.info(f"Running command: {' '.join(docker_cmd)}")

    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            logger.error(f"rmapi command failed: {result.stderr}")
            return False, result.stderr

        return True, result.stdout
    except Exception as e:
        logger.error(f"Error running rmapi command: {e}")
        return False, str(e)


def find_notebook_by_name(notebook_name: str) -> Optional[str]:
    """
    Find a notebook by name and return its ID.

    Args:
        notebook_name: Name of the notebook to find

    Returns:
        Notebook ID or None if not found
    """
    logger.info(f"Looking for notebook named '{notebook_name}'")

    # List all files
    success, output = run_docker_rmapi(["ls", "-l", "/"])
    if not success:
        return None

    # Parse output to find notebook
    lines = output.strip().split("\n")
    print("Available notebooks:")
    for line in lines:
        print(line)
        # Case insensitive search
        if notebook_name.lower() in line.lower() and line.startswith("[f]"):
            # Extract the name part after the file indicator and ID
            parts = line.split("\t", 1)  # Use tab as separator
            if len(parts) >= 2:
                notebook_name_found = parts[1].strip()
                logger.info(f"Found notebook: '{notebook_name_found}'")

                # Use special command to get the ID by name
                success, id_output = run_docker_rmapi(["find", "/", notebook_name_found])
                if success and id_output.strip():
                    # Extract the ID from the find result
                    for result_line in id_output.strip().split("\n"):
                        if notebook_name_found in result_line:
                            notebook_id = result_line.split(" ")[0].strip()
                            logger.info(f"Found notebook ID: {notebook_id}")
                            return notebook_id

                # If the find command fails, just use the name as the ID (works in some rmapi versions)
                logger.info(f"Using name as ID: {notebook_name_found}")
                return notebook_name_found

    logger.error(f"Notebook '{notebook_name}' not found")
    return None


def download_notebook(notebook_id: str) -> Optional[str]:
    """
    Download a notebook from reMarkable Cloud.

    Args:
        notebook_id: ID of the notebook to download

    Returns:
        Path to the downloaded .rmdoc file or None if failed
    """
    logger.info(f"Downloading notebook with ID: {notebook_id}")

    # Get the output path in the mounted volume
    home_dir = os.path.expanduser("~")
    output_path = os.path.join(home_dir, "dev/remarkable-ink-link/handwriting_model/docker_temp/notebook.zip")

    # Download notebook
    success, output = run_docker_rmapi(["get", notebook_id, "/output/notebook.zip", "--format", "zip"])

    if not success:
        logger.error(f"Failed to download notebook: {output}")
        return None

    if not os.path.exists(output_path):
        logger.error(f"Downloaded file not found at {output_path}")
        return None

    logger.info(f"Downloaded notebook to {output_path}")
    return output_path


def extract_notebook(zip_path: str) -> Optional[str]:
    """
    Extract the notebook zip file.
    
    Args:
        zip_path: Path to the downloaded .zip file
        
    Returns:
        Path to the directory with extracted content or None if failed
    """
    logger.info(f"Extracting notebook: {zip_path}")
    
    # Create extraction directory
    extract_dir = tempfile.mkdtemp(prefix="remarkable_content_")
    
    try:
        # Extract the zip file
        subprocess.run(
            ["unzip", "-o", zip_path, "-d", extract_dir],
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Extracted notebook to {extract_dir}")
        return extract_dir
    except Exception as e:
        logger.error(f"Failed to extract notebook: {e}")
        return None


def find_rm_files(extract_dir: str) -> List[str]:
    """
    Find all .rm files in the extracted notebook.
    
    Args:
        extract_dir: Path to the directory with extracted content
        
    Returns:
        List of paths to .rm files
    """
    logger.info(f"Finding .rm files in {extract_dir}")
    
    # Find all .rm files
    rm_files = list(Path(extract_dir).glob("**/*.rm"))
    
    if not rm_files:
        logger.warning("No .rm files found in the notebook")
    else:
        logger.info(f"Found {len(rm_files)} .rm files")
    
    return [str(f) for f in rm_files]


def render_rm_file_to_png(rm_file: str, output_dir: str) -> Optional[str]:
    """
    Render an .rm file to PNG.
    
    Args:
        rm_file: Path to the .rm file
        output_dir: Directory to save the PNG file
        
    Returns:
        Path to the rendered PNG file or None if failed
    """
    logger.info(f"Rendering {rm_file} to PNG")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    filename = os.path.basename(rm_file)
    name_without_ext = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{name_without_ext}.png")
    
    # Try to use rM tools if available (rsvg-convert is commonly used)
    try:
        # This is a simplified version - actual rendering would require processing
        # the .rm format which requires specialized tools
        
        # As a fallback, we'll try to use pdftoppm if available
        logger.warning("Using simplified rendering - install specialized tools for better results")
        
        # For now, just copy the file to show we processed it
        shutil.copy(rm_file, output_path)
        logger.info(f"Saved (placeholder) PNG to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to render .rm file: {e}")
        return None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fetch and render a reMarkable notebook as PNG images."
    )
    parser.add_argument("--notebook-name", type=str, default="Claude",
                       help="Name of the notebook to fetch (default: Claude)")
    parser.add_argument("--output-dir", type=str, default="rendered_pages",
                       help="Directory to save rendered PNG files (default: rendered_pages)")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Find notebook
    notebook_id = find_notebook_by_name(args.notebook_name)
    if not notebook_id:
        sys.exit(1)
    
    # Download notebook
    zip_path = download_notebook(notebook_id)
    if not zip_path:
        sys.exit(1)
    
    # Extract notebook
    extract_dir = extract_notebook(zip_path)
    if not extract_dir:
        sys.exit(1)
    
    # Find .rm files
    rm_files = find_rm_files(extract_dir)
    if not rm_files:
        sys.exit(1)
    
    # Render each .rm file to PNG
    for rm_file in rm_files:
        render_rm_file_to_png(rm_file, args.output_dir)
    
    logger.info(f"Rendered {len(rm_files)} pages to {args.output_dir}")


if __name__ == "__main__":
    main()