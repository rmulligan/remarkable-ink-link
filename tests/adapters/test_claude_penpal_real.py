#!/usr/bin/env python3
"""Test Claude Penpal Service with real Claude integration."""

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
logger = logging.getLogger("test_claude_penpal_real")

# Import project modules
try:
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG
    from inklink.services.claude_penpal_service import ClaudePenpalService
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.config import CONFIG
    from inklink.services.claude_penpal_service import ClaudePenpalService


def create_handwritten_query_rm():
    """Create a .rm file with realistic handwriting data."""
    # Create a more complete .rm file with version 6 format

    # Header for version 6
    header = b"reMarkable .lines file, version=6          "

    # Write basic structure
    content = bytearray()

    # Number of layers (1)
    content.extend(struct.pack("<I", 1))

    # Layer 1: Number of strokes (let's create a simple "Hello" text)
    num_strokes = 3  # Three strokes for simple text
    content.extend(struct.pack("<I", num_strokes))

    # Create strokes that form "Hi Claude" - simplified version
    def create_stroke(points_list):
        stroke_data = bytearray()

        # Stroke header
        stroke_data.extend(struct.pack("<I", 4))  # pen type (4 = Ballpoint)
        stroke_data.extend(struct.pack("<I", 0))  # color (0 = black)
        stroke_data.extend(struct.pack("<I", 0))  # unknown
        stroke_data.extend(struct.pack("<f", 1.875))  # width
        stroke_data.extend(struct.pack("<I", 0))  # unknown

        # Number of points
        stroke_data.extend(struct.pack("<I", len(points_list)))

        # Points
        for x, y, pressure, tilt_x, tilt_y, timestamp in points_list:
            stroke_data.extend(
                struct.pack("<ffffff", x, y, pressure, tilt_x, tilt_y, timestamp)
            )

        return stroke_data

    # Stroke 1: "H" - left vertical line
    points_h1 = [
        (200.0, 300.0, 1.0, 0.0, 0.0, 0.1),
        (200.0, 350.0, 1.0, 0.0, 0.0, 0.2),
        (200.0, 400.0, 1.0, 0.0, 0.0, 0.3),
        (200.0, 450.0, 1.0, 0.0, 0.0, 0.4),
    ]
    content.extend(create_stroke(points_h1))

    # Stroke 2: "H" - horizontal line
    points_h2 = [
        (200.0, 375.0, 1.0, 0.0, 0.0, 0.5),
        (225.0, 375.0, 1.0, 0.0, 0.0, 0.6),
        (250.0, 375.0, 1.0, 0.0, 0.0, 0.7),
    ]
    content.extend(create_stroke(points_h2))

    # Stroke 3: "H" - right vertical line
    points_h3 = [
        (250.0, 300.0, 1.0, 0.0, 0.0, 0.8),
        (250.0, 350.0, 1.0, 0.0, 0.0, 0.9),
        (250.0, 400.0, 1.0, 0.0, 0.0, 1.0),
        (250.0, 450.0, 1.0, 0.0, 0.0, 1.1),
    ]
    content.extend(create_stroke(points_h3))

    # Combine header and content
    rm_data = header + content

    return rm_data


def create_test_notebook_with_query():
    """Create a notebook with a handwritten query for Claude."""
    # Create temp directory
    temp_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "test_claude_real"
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
            "visibleName": "Claude_Real_Test",
            "tags": ["HasLilly"],
        }

        # Create content with proper structure
        content = {
            "cPages": {
                "lastOpened": {"timestamp": "1:1", "value": page_id},
                "original": {"timestamp": "0:0", "value": -1},
                "pages": [{"id": page_id, "idx": {"timestamp": "1:1", "value": "aa"}}],
            },
            "coverPageNumber": 0,
            "documentMetadata": {},
            "extraMetadata": {
                "LastTool": "Ballpoint",
                "LastBallpointColor": "Black",
                "LastBallpointSize": "2",
            },
            "fileType": "notebook",
            "fontName": "",
            "lineHeight": -1,
            "margins": 125,
            "orientation": "portrait",
            "originalPageCount": -1,
            "pageCount": 1,
            "pages": [
                {
                    "id": page_id,
                    "idx": 0,
                    "template": "Blank",
                    "lastModified": now_ms,
                    "lineHeight": -1,
                    "orientation": "portrait",
                    "pageHeight": 1872,
                    "pageWidth": 1404,
                    "tags": ["Lilly"],
                    "visibleName": "Query for Claude",
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
            f.write(create_handwritten_query_rm())

        # Create .rmdoc archive
        archive_path = os.path.join(temp_dir, "Claude_Real_Test.rmdoc")
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_STORED) as zipf:
            # Add metadata
            zipf.write(metadata_path, f"{notebook_id}.metadata")
            # Add content
            zipf.write(content_path, f"{notebook_id}.content")
            # Add .rm file
            zipf.write(rm_file_path, f"{notebook_id}/{page_id}.rm")

        logger.info(f"Created test notebook at: {archive_path}")
        return archive_path, notebook_id, page_id

    except Exception as e:
        logger.error(f"Error creating notebook: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Claude Penpal Service with real Claude"
    )
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--mock", action="store_true", help="Use mock instead of real Claude"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Configure rmapi path
    rmapi_path = args.rmapi_path or CONFIG.get("RMAPI_PATH", "./local-rmapi")
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
    logger.info("Creating test notebook with handwritten query...")
    notebook_path, notebook_id, page_id = create_test_notebook_with_query()

    # Upload the notebook
    logger.info("Uploading notebook...")
    success, message = rmapi_adapter.upload_file(notebook_path, "Claude_Real_Test")

    if not success:
        logger.error(f"Failed to upload notebook: {message}")
        return 1

    logger.info("Successfully uploaded notebook")
    time.sleep(3)  # Give the cloud time to process

    # Initialize service
    if args.mock:
        logger.info("Initializing mock Claude Penpal Service")

        class MockClaudePenpalService(ClaudePenpalService):
            def _process_with_claude(self, notebook_id, prompt, new_conversation=False):
                logger.info(f"Mock processing: {prompt[:100]}...")
                return f"Mock response to: {prompt}"

        service = MockClaudePenpalService(
            rmapi_path=rmapi_path,
            query_tag="Lilly",
            pre_filter_tag="HasLilly",
        )
    else:
        logger.info("Initializing real Claude Penpal Service")
        service = ClaudePenpalService(
            rmapi_path=rmapi_path,
            query_tag="Lilly",
            pre_filter_tag="HasLilly",
        )

    # Find and process the notebook
    success, notebooks = rmapi_adapter.list_files()
    if not success:
        logger.error("Failed to list notebooks")
        return 1

    target_notebook = None
    for notebook in notebooks:
        if notebook.get("VissibleName") == "Claude_Real_Test":
            target_notebook = notebook
            break

    if not target_notebook:
        logger.error("Test notebook not found")
        return 1

    logger.info(f"Found notebook: {target_notebook.get('VissibleName')}")

    try:
        # Process the notebook
        logger.info("Processing notebook for queries...")
        service._check_notebook_for_tagged_pages(target_notebook)

        # Wait a bit for processing
        time.sleep(5)

        # Check for updates
        logger.info("Checking for response...")
        success, updated_notebooks = rmapi_adapter.list_files()
        if success:
            for nb in updated_notebooks:
                if nb.get("VissibleName") == "Claude_Real_Test":
                    logger.info(f"Notebook last modified: {nb.get('ModifiedClient')}")
                    break

        logger.info("✅ Successfully processed notebook with Claude Penpal Service")
        return 0

    except Exception as e:
        logger.error(f"Error processing notebook: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
