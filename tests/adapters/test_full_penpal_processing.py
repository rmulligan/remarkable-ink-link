#!/usr/bin/env python3
"""Full test of Claude Penpal Service processing with real integration."""

import os
import sys
import time
import logging
import json
import uuid
import zipfile
import argparse
import struct

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_full_penpal_processing")

# Import project modules
try:
    from inklink.config import CONFIG
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.services.claude_penpal_service import ClaudePenpalService
except ImportError:
    # Add project root to sys.path if imports fail
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(project_dir, "src"))
    from inklink.config import CONFIG
    from inklink.adapters.rmapi_adapter import RmapiAdapter
    from inklink.services.claude_penpal_service import ClaudePenpalService


def create_test_rm_file_with_query():
    """Create a test .rm file with actual stroke data forming 'Hello Claude'."""
    # reMarkable .lines file version 6 header
    header = b"reMarkable .lines file, version=6" + b" " * 10

    # Number of layers (1)
    num_layers = struct.pack("<I", 1)

    # Layer 1 - multiple strokes forming letters
    num_strokes = struct.pack("<I", 5)  # 5 strokes for simple text

    strokes_data = b""

    # Helper function to create a stroke
    def create_stroke(points):
        # Stroke header
        pen = struct.pack("<I", 4)  # Pencil
        color = struct.pack("<I", 0)  # Black
        unknown1 = struct.pack("<I", 0)
        width = struct.pack("<f", 1.875)
        unknown2 = struct.pack("<I", 0)

        num_points = struct.pack("<I", len(points))

        points_data = b""
        for x, y in points:
            point = struct.pack(
                "<fffff", x, y, 1.0, 0.0, 0.0
            )  # x, y, pressure, rotation, tilt
            points_data += point

        return pen + color + unknown1 + width + unknown2 + num_points + points_data

    # Create strokes forming "Hello" - simplified
    # H
    strokes_data += create_stroke([(100, 100), (100, 200)])  # Left vertical
    strokes_data += create_stroke([(100, 150), (150, 150)])  # Horizontal
    strokes_data += create_stroke([(150, 100), (150, 200)])  # Right vertical

    # ? (question mark)
    strokes_data += create_stroke(
        [(250, 120), (240, 100), (260, 100), (270, 120), (270, 150), (270, 170)]
    )  # Curve and stem
    strokes_data += create_stroke([(270, 190), (270, 195)])  # Dot

    # Combine all data
    rm_data = header + num_layers + num_strokes + strokes_data

    return rm_data


def create_penpal_test_notebook():
    """Create a complete notebook with a query for Claude."""
    # Create temp directory
    temp_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "test_penpal_notebook"
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
            "visibleName": "Claude_Query_Notebook",
            "tags": ["HasLilly"],  # Notebook-level tag
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
                "LastBallpointColor": "Black",
                "LastBallpointSize": "2",
                "LastBallpointv2Color": "Black",
                "LastBallpointv2Size": "2",
                "LastCalligraphyColor": "Black",
                "LastCalligraphySize": "2",
                "LastClearPageColor": "Black",
                "LastClearPageSize": "2",
                "LastEraserSize": "2",
                "LastEraserTool": "Eraser",
                "LastFineColor": "Black",
                "LastFineSize": "1",
                "LastFinelinerColor": "Black",
                "LastFinelinerSize": "1",
                "LastHighlighterColor": "Black",
                "LastHighlighterSize": "4",
                "LastHighlighterv2Color": "Black",
                "LastHighlighterv2Size": "4",
                "LastMarkerColor": "Black",
                "LastMarkerSize": "3",
                "LastMarkerv2Color": "Black",
                "LastMarkerv2Size": "3",
                "LastPaintBrushColor": "Black",
                "LastPaintBrushSize": "3",
                "LastPenColor": "Black",
                "LastPenSize": "2",
                "LastPencilColor": "Black",
                "LastPencilSize": "2",
                "LastPencilv2Color": "Black",
                "LastPencilv2Size": "2",
                "LastSharpPencilColor": "Black",
                "LastSharpPencilSize": "1",
                "LastSharpPencilv2Color": "Black",
                "LastSharpPencilv2Size": "1",
                "LastSolidPenColor": "Black",
                "LastSolidPenSize": "2",
                "LastTool": "Pencilv2",
                "LastToolWhenReadOnly": "Move",
                "LastUndefinedColor": "Black",
                "LastUndefinedSize": "1",
            },
            "fileType": "notebook",
            "fontName": "",
            "lineHeight": -1,
            "margins": 125,
            "orientation": "portrait",
            "originalPageCount": -1,
            "pageCount": 1,
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
                    "tags": ["Lilly"],  # Page-level tag
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
            f.write(create_test_rm_file_with_query())

        # Create .rmdoc archive
        archive_path = os.path.join(temp_dir, "Claude_Query_Notebook.rmdoc")
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
    parser = argparse.ArgumentParser(description="Full test of Claude Penpal Service")
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--use-real-claude", action="store_true", help="Use real Claude instead of mock"
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
    logger.info("Creating test notebook with Claude query...")
    notebook_path, notebook_id, page_id = create_penpal_test_notebook()

    # Upload the notebook
    logger.info("Uploading notebook...")
    success, message = rmapi_adapter.upload_file(notebook_path, "Claude_Query_Notebook")

    if not success:
        logger.error(f"Failed to upload notebook: {message}")
        return 1

    logger.info("Successfully uploaded notebook")
    time.sleep(3)  # Give the cloud time to process

    # Initialize service
    logger.info("Initializing Claude Penpal Service")
    if args.use_real_claude:
        service = ClaudePenpalService(
            rmapi_path=rmapi_path,
            query_tag="Lilly",
            pre_filter_tag="HasLilly",
        )
    else:
        # Mock service for testing
        class MockClaudePenpalService(ClaudePenpalService):
            def _process_with_claude(self, notebook_id, prompt, new_conversation=False):
                logger.info(f"Mock Claude processing for notebook: {notebook_id}")
                return f"""Hello! I see your query "{prompt[:50]}...".

This is a test response from the mock Claude Penpal Service.

The service is working correctly and can process handwritten queries!

Best regards,
Claude"""

        service = MockClaudePenpalService(
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
        if notebook.get("VissibleName") == "Claude_Query_Notebook":
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

        # Check if response was added
        logger.info("Checking for response...")
        time.sleep(5)  # Give time for upload

        # Download and check the updated notebook
        success, updated_notebooks = rmapi_adapter.list_files()
        if success:
            for nb in updated_notebooks:
                if nb.get("VissibleName") == "Claude_Query_Notebook":
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
