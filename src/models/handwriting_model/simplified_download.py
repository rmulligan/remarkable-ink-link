#!/usr/bin/env python3
"""
Simple script to download a reMarkable notebook using rmapi Docker image.
"""

import os
import subprocess
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    # Parameters
    notebook_name = "Claude"
    home_dir = os.path.expanduser("~")
    output_dir = os.path.join(
        home_dir, "dev/remarkable-ink-link/handwriting_model/downloads"
    )
    os.makedirs(output_dir, exist_ok=True)

    # 1. List all notebooks
    logger.info(f"Listing all notebooks")
    list_cmd = [
        "docker",
        "run",
        "-v",
        f"{home_dir}/.config/rmapi/:/home/app/.config/rmapi/",
        "rmapi",
        "ls",
        "/",
    ]

    try:
        result = subprocess.run(list_cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error(f"Failed to list notebooks: {result.stderr}")
            return

        notebooks = result.stdout.strip().split("\n")
        logger.info("Available notebooks:")
        for notebook in notebooks:
            logger.info(f"  {notebook}")

        # 2. Find the matching notebook
        matching_notebook = None
        for notebook in notebooks:
            if notebook_name.lower() in notebook.lower():
                matching_notebook = notebook.strip()
                logger.info(f"Found matching notebook: {matching_notebook}")
                break

        if not matching_notebook:
            logger.error(f"Notebook '{notebook_name}' not found")
            return

        # 3. Download the notebook
        # Extract just the name part after the tab
        notebook_parts = matching_notebook.split("\t")
        clean_name = (
            notebook_parts[1].strip() if len(notebook_parts) > 1 else notebook_name
        )

        logger.info(f"Downloading notebook: {clean_name}")
        download_cmd = [
            "docker",
            "run",
            "-v",
            f"{home_dir}/.config/rmapi/:/home/app/.config/rmapi/",
            "-v",
            f"{output_dir}:/output",
            "rmapi",
            "get",
            clean_name,
            "/output/notebook.zip",
        ]

        download_result = subprocess.run(
            download_cmd, capture_output=True, text=True, check=False
        )
        if download_result.returncode != 0:
            logger.error(f"Failed to download notebook: {download_result.stderr}")
            return

        output_path = os.path.join(output_dir, "notebook.zip")
        if os.path.exists(output_path):
            logger.info(f"Successfully downloaded notebook to {output_path}")

            # 4. Extract the notebook
            extract_cmd = [
                "unzip",
                "-o",
                output_path,
                "-d",
                os.path.join(output_dir, "extracted"),
            ]
            extract_result = subprocess.run(
                extract_cmd, capture_output=True, text=True, check=False
            )

            if extract_result.returncode != 0:
                logger.error(f"Failed to extract notebook: {extract_result.stderr}")
                return

            logger.info(
                f"Extracted notebook to {os.path.join(output_dir, 'extracted')}"
            )
        else:
            logger.error(f"Downloaded file not found at {output_path}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
