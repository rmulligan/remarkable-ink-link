#!/usr/bin/env python3
"""
Extract strokes from reMarkable notebooks using rmapi.

This script downloads notebooks from reMarkable Cloud using rmapi and
extracts stroke data for use with the handwriting recognition model.
"""

import os
import sys
import json
import argparse
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add parent directory to path to import preprocessing utilities
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import stroke extraction function
from preprocessing import extract_strokes_from_rm_file, save_strokes_to_json

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def list_notebooks(rmapi_cmd: str) -> List[Dict[str, Any]]:
    """
    List all notebooks in reMarkable Cloud using rmapi.

    Args:
        rmapi_cmd: rmapi command (either binary path or Docker command)

    Returns:
        List of notebook metadata dictionaries
    """
    try:
        # Check if we're using Docker
        if isinstance(rmapi_cmd, str) and "docker" in rmapi_cmd:
            # Docker command for rmapi
            cmd = rmapi_cmd.split() + ["ls", "-l", "/"]
        else:
            # Regular rmapi command
            cmd = [rmapi_cmd, "ls", "-l", "/"]

        # Run command
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            logger.error(f"Failed to list notebooks: {result.stderr}")
            return []

        # Parse output (not JSON, but formatted text)
        lines = result.stdout.strip().split("\n")
        notebooks = []

        for line in lines:
            if not line.strip():
                continue

            # Parse line format: [d/f] ID NAME...
            if line.startswith("[f]"):
                # This is a file/document
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    doc_id = parts[1].strip()
                    name = parts[2].strip()
                    notebooks.append(
                        {"ID": doc_id, "VissibleName": name, "Type": "DocumentType"}
                    )

        return notebooks

    except Exception as e:
        logger.error(f"Error listing notebooks: {e}")
        return []


def download_notebook(
    rmapi_cmd: str, document_id: str, output_dir: str
) -> Optional[str]:
    """
    Download a notebook from reMarkable Cloud using rmapi.

    Args:
        rmapi_cmd: rmapi command (either binary path or Docker command)
        document_id: ID of the document to download
        output_dir: Directory to save the downloaded notebook

    Returns:
        Path to the downloaded file or None if failed
    """
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Prepare command
            zip_path = os.path.abspath(f"{temp_dir}/notebook.zip")

            # Ensure the parent directory exists
            os.makedirs(os.path.dirname(zip_path), exist_ok=True)

            # Check if we're using Docker
            if isinstance(rmapi_cmd, str) and "docker" in rmapi_cmd:
                # Docker command needs volume mounting
                docker_args = rmapi_cmd.split()

                # Add volume mount for the temporary directory
                vol_mount = f"{os.path.dirname(zip_path)}:{os.path.dirname(zip_path)}"

                # Extract docker run command and insert volume mount
                run_idx = docker_args.index("run")
                if "-v" not in docker_args[run_idx + 1 : run_idx + 3]:
                    # Add volume mount only if not already present
                    docker_args.insert(run_idx + 1, "-v")
                    docker_args.insert(run_idx + 2, vol_mount)

                # Add rmapi command
                cmd = docker_args + ["get", document_id, zip_path, "--format", "zip"]
            else:
                # Regular rmapi command
                cmd = [
                    rmapi_cmd,
                    "get",
                    document_id,
                    f"{temp_dir}/notebook.zip",
                    "--format",
                    "zip",
                ]

            # Run command
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                logger.error(
                    f"Failed to download notebook {document_id}: {result.stderr}"
                )
                return None

            # Extract zip file
            result = subprocess.run(
                ["unzip", f"{temp_dir}/notebook.zip", "-d", f"{temp_dir}/extracted"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(
                    f"Failed to extract notebook {document_id}: {result.stderr}"
                )
                return None

            # Create output directory
            os.makedirs(output_dir, exist_ok=True)

            # Find all .rm files
            rm_files = list(Path(f"{temp_dir}/extracted").glob("**/*.rm"))

            # Extract strokes from each .rm file
            for rm_file in rm_files:
                # Extract strokes
                strokes = extract_strokes_from_rm_file(str(rm_file))

                # Skip if no strokes found
                if not strokes:
                    logger.warning(f"No strokes found in {rm_file}")
                    continue

                # Save strokes to JSON
                output_file = os.path.join(output_dir, f"{rm_file.stem}_strokes.json")
                save_strokes_to_json(strokes, output_file)
                logger.info(f"Saved {len(strokes)} strokes to {output_file}")

            # Return output directory
            return output_dir

    except Exception as e:
        logger.error(f"Error downloading notebook {document_id}: {e}")
        return None


def main():
    """Main function."""
    # Parse arguments
    home_dir = os.path.expanduser("~")
    default_docker_cmd = (
        f"docker run -v {home_dir}/.config/rmapi/:/home/app/.config/rmapi/ rmapi"
    )

    parser = argparse.ArgumentParser(
        description="Extract strokes from reMarkable notebooks"
    )
    parser.add_argument(
        "--rmapi",
        type=str,
        default=default_docker_cmd,
        help="Path to rmapi executable or Docker command",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/remarkable",
        help="Directory to save extracted strokes",
    )
    parser.add_argument(
        "--document-id",
        type=str,
        help="ID of specific document to download (if omitted, list all documents)",
    )
    parser.add_argument(
        "--use-docker",
        action="store_true",
        default=True,
        help="Use Docker version of rmapi (default: True)",
    )

    args = parser.parse_args()

    # Set default Docker command if --use-docker is specified
    if args.use_docker and not args.rmapi.startswith("docker"):
        args.rmapi = default_docker_cmd
        logger.info(f"Using Docker rmapi command: {args.rmapi}")

    # If using a local binary, check if it exists
    if not args.rmapi.startswith("docker") and not os.path.exists(args.rmapi):
        logger.error(f"rmapi not found at {args.rmapi}")
        sys.exit(1)

    # If no document ID provided, list all notebooks
    if not args.document_id:
        notebooks = list_notebooks(args.rmapi)

        if not notebooks:
            logger.error("No notebooks found or failed to list notebooks")
            sys.exit(1)

        # Print notebooks
        print("\nAvailable notebooks:")
        for i, notebook in enumerate(notebooks):
            print(
                f"[{i+1}] {notebook.get('VissibleName', 'Unnamed')} - ID: {notebook.get('ID')}"
            )

        print("\nTo download a specific notebook, run:")
        print(f"python {sys.argv[0]} --document-id DOCUMENT_ID\n")

    else:
        # Download specific notebook
        output_dir = os.path.join(args.output_dir, args.document_id)
        result = download_notebook(args.rmapi, args.document_id, output_dir)

        if not result:
            logger.error(f"Failed to download notebook {args.document_id}")
            sys.exit(1)

        logger.info(f"Successfully downloaded and extracted strokes to {output_dir}")


if __name__ == "__main__":
    main()
