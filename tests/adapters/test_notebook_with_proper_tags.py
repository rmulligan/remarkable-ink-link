"""Create a notebook with proper page tagging structure."""

import argparse
import json
import logging
import os
import struct
import sys
import time
import uuid
import zipfile

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_notebook_with_proper_tags")

# Import project modules
try:
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG


def create_test_rm_file():
    """Create a proper test .rm file with actual stroke data."""
    # reMarkable .lines file version 5 header
    header = b"reMarkable .lines file, version=5          "

    # Number of layers (1)
    num_layers = struct.pack("<I", 1)

    # Layer 1 - actual strokes
    num_strokes = struct.pack("<I", 1)

    # Test stroke - a simple line
    pen = struct.pack("<I", 4)  # Pencil
    color = struct.pack("<I", 0)  # Black
    unknown1 = struct.pack("<I", 0)
    width = struct.pack("<f", 1.875)
    unknown2 = struct.pack("<I", 0)

    # Number of points
    num_points = struct.pack("<I", 3)

    point1 = struct.pack("<fffff", 100.0, 100.0, 1.0, 0.0, 0.0)
    point2 = struct.pack("<fffff", 200.0, 200.0, 1.0, 0.0, 0.0)
    point3 = struct.pack("<fffff", 300.0, 300.0, 1.0, 0.0, 0.0)

    # Combine all data
    rm_data = (
        header
        + num_layers
        + num_strokes
        + pen
        + color
        + unknown1
        + width
        + unknown2
        + num_points
        + point1
        + point2
        + point3
    )

    return rm_data


def create_tagged_notebook():
    """Create a complete notebook with properly tagged pages."""
    # Create temp directory
    temp_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "test_tagged_notebook"
    )
    if os.path.exists(temp_dir):
        import shutil

        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    try:
        # Generate IDs
        notebook_id = str(uuid.uuid4())
        page_id = str(uuid.uuid4())
        now_ms = str(int(time.time() * 1000))

        # Create metadata
        metadata = {
            "deleted": False,
            "lastModified": now_ms,
            "lastOpened": now_ms,
            "lastOpenedPage": 0,
            "metadatamodified": False,
            "modified": False,
            "parent": "",
            "pinned": False,
            "synced": True,
            "type": "DocumentType",
            "version": 1,
            "visibleName": "Tagged_Test_Notebook",
            "tags": ["HasLilly"],  # Notebook-level tag
        }

        # Create content with page-level tags
        content = {
            "cPages": {
                "lastOpened": {"timestamp": "1:1", "value": page_id},
                "original": {"timestamp": "0:0", "value": -1},
                "pages": [{"id": page_id, "idx": {"timestamp": "1:1", "value": "aa"}}],
            },
            "coverPageNumber": 0,
            "documentMetadata": {},
            "extraMetadata": {},
            "fileType": "notebook",
            "fontName": "",
            "lineHeight": -1,
            "margins": 125,
            "orientation": "portrait",
            "originalPageCount": -1,
            "pageCount": 1,
            "pageTags": [  # Page tags as a list
                {
                    "name": page_id,
                    "pageIdx": 0,
                    "type": "1",
                    "value": ["Lilly"],  # Page-level tag
                }
            ],
            "pages": [  # Pages as a detailed list
                {
                    "id": page_id,
                    "idx": 0,
                    "template": "Blank",
                    "lastModified": now_ms,
                    "lineHeight": -1,
                    "orientation": "portrait",
                    "pageHeight": 1872,
                    "pageWidth": 1404,
                    "tags": ["Lilly"],  # Also include tags directly in page
                    "visibleName": "Query Page",
                }
            ],
            "sizeInBytes": 1000,
            "tags": [],
            "textAlignment": "left",
            "textScale": 1,
            "transform": {
                "m11": 1,
                "m12": 0,
                "m13": 0,
                "m21": 0,
                "m22": 1,
                "m23": 0,
                "m31": 0,
                "m32": 0,
                "m33": 1,
            },
        }

        # Write files
        metadata_path = os.path.join(temp_dir, f"{notebook_id}.metadata")
        content_path = os.path.join(temp_dir, f"{notebook_id}.content")

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        with open(content_path, "w") as f:
            json.dump(content, f, indent=2)

        # Create notebook directory and .rm file
        notebook_dir = os.path.join(temp_dir, notebook_id)
        os.makedirs(notebook_dir, exist_ok=True)

        rm_file_path = os.path.join(notebook_dir, f"{page_id}.rm")
        with open(rm_file_path, "wb") as f:
            f.write(create_test_rm_file())

        # Create .rmdoc archive
        archive_path = os.path.join(temp_dir, "Tagged_Test_Notebook.rmdoc")
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as zipf:
            # Add metadata
            zipf.write(metadata_path, f"{notebook_id}.metadata")
            # Add content
            zipf.write(content_path, f"{notebook_id}.content")
            # Add .rm file
            zipf.write(rm_file_path, f"{notebook_id}/{page_id}.rm")

        logger.info(f"Created tagged notebook at: {archive_path}")
        return archive_path, notebook_id, page_id

    except Exception as e:
        logger.error(f"Error creating notebook: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create notebook with proper tags")
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Configure rmapi path
    rmapi_path = args.rmapi_path or CONFIG.get("RMAPI_PATH")
    if not os.path.exists(rmapi_path):
        logger.error(f"RMAPI executable not found at {rmapi_path}")
        return 1

    logger.info(f"Using rmapi path: {rmapi_path}")

    # Initialize rmapi adapter
    rmapi_adapter = RmapiAdapter(rmapi_path)

    # Verify connection
    if not rmapi_adapter.ping():
        logger.error("Failed to connect to reMarkable Cloud")
        return 1

    logger.info("Successfully connected to reMarkable Cloud")

    # Create notebook
    logger.info("Creating notebook with proper tags...")
    notebook_path, notebook_id, page_id = create_tagged_notebook()

    # Upload the notebook
    logger.info("Uploading notebook...")
    success, message = rmapi_adapter.upload_file(notebook_path, "Tagged_Test_Notebook")

    if not success:
        logger.error(f"Failed to upload notebook: {message}")
        return 1

    logger.info("Successfully uploaded notebook")
    logger.info(f"Notebook ID: {notebook_id}")
    logger.info(f"Page ID: {page_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
