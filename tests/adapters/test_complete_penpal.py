#!/usr/bin/env python3
"""Complete test of Claude Penpal Service with real handwriting."""

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
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_complete_penpal")

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

def create_test_rm_file():
    """Create a test .rm file with actual stroke data."""
    # reMarkable .lines file version 6 header
    header = b"reMarkable .lines file, version=6" + b" " * 10
    
    # Number of layers (1)
    num_layers = 1
    layers_data = struct.pack('<I', num_layers)
    
    # Layer 1 - actual strokes
    num_strokes = 1
    strokes_data = struct.pack('<I', num_strokes)
    
    # Test stroke - a simple "?" shape
    stroke = {
        "pen": 4,  # Pencil
        "color": 0,  # Black
        "width": 1.875,
        "pressure": 0.5,
        "speed": 0.5,
        "opacity": 1.0,
        "num_points": 10  # Question mark shape
    }
    
    # Pack stroke header
    stroke_header = struct.pack('<IIIBBBB',
        stroke["pen"],
        stroke["color"],
        0,  # Unknown
        int(stroke["width"] * 100),  # Width in hundredths
        0,  # Unknown
        int(stroke["opacity"] * 255),  # Opacity as byte
        0   # Unknown
    )
    
    # Question mark points (simplified)
    points = [
        (500, 300, stroke["pressure"], 0, 0, stroke["speed"]),  # Top curve start
        (450, 250, stroke["pressure"], 0, 0, stroke["speed"]),
        (400, 300, stroke["pressure"], 0, 0, stroke["speed"]),
        (400, 400, stroke["pressure"], 0, 0, stroke["speed"]),
        (400, 500, stroke["pressure"], 0, 0, stroke["speed"]),
        (400, 600, stroke["pressure"], 0, 0, stroke["speed"]),  # Straight part
        (400, 650, stroke["pressure"], 0, 0, stroke["speed"]),
        (400, 700, stroke["pressure"], 0, 0, stroke["speed"]),  # Bottom
        (400, 800, stroke["pressure"], 0, 0, stroke["speed"]),  # Dot
        (400, 810, stroke["pressure"], 0, 0, stroke["speed"])
    ]
    
    num_points = len(points)
    points_data = struct.pack('<I', num_points)
    
    # Pack all points
    all_points = b''
    for x, y, pressure, tilt_x, tilt_y, speed in points:
        point_data = struct.pack('<ffffff', x, y, pressure, tilt_x, tilt_y, speed)
        all_points += point_data
    
    # Combine all data
    rm_data = header + layers_data + strokes_data + stroke_header + points_data + all_points
    
    return rm_data

def create_test_notebook_with_query():
    """Create a complete notebook with a query page."""
    # Create temp directory
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_notebook_complete")
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
            "visibleName": "Test_Penpal_Query_Notebook",
            "tags": ["HasLilly"]
        }
        
        # Create content with proper cPages structure
        content = {
            "cPages": {
                "lastOpened": {
                    "timestamp": "1:1",
                    "value": page_id
                },
                "original": {
                    "timestamp": "0:0",
                    "value": -1
                },
                "pages": [
                    {
                        "id": page_id,
                        "idx": {
                            "timestamp": "1:1",  
                            "value": "aa"
                        }
                    }
                ]
            },
            "coverPageNumber": 0,
            "customZoomCenterX": 0,
            "customZoomCenterY": 936,
            "customZoomOrientation": "portrait",
            "customZoomPageHeight": 1872,
            "customZoomPageWidth": 1404,
            "customZoomScale": 1,
            "documentMetadata": {},
            "extraMetadata": {},
            "fileType": "notebook",
            "fontName": "",
            "lineHeight": -1,
            "margins": 125,
            "orientation": "portrait",
            "originalPageCount": -1,
            "pageCount": 1,
            "pageTags": {
                page_id: ["Lilly"]  # Tag the page with Lilly
            },
            "pages": [page_id],
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
                "m33": 1
            }
        }
        
        # Write files
        metadata_path = os.path.join(temp_dir, f"{notebook_id}.metadata")
        content_path = os.path.join(temp_dir, f"{notebook_id}.content")
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        with open(content_path, 'w') as f:
            json.dump(content, f, indent=2)
            
        # Create notebook directory and .rm file
        notebook_dir = os.path.join(temp_dir, notebook_id)
        os.makedirs(notebook_dir, exist_ok=True)
        
        rm_file_path = os.path.join(notebook_dir, f"{page_id}.rm")
        with open(rm_file_path, 'wb') as f:
            f.write(create_test_rm_file())
            
        # Create .rmdoc archive
        archive_path = os.path.join(temp_dir, "Test_Penpal_Query_Notebook.rmdoc")
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_STORED) as zipf:
            # Add metadata
            zipf.write(metadata_path, f"{notebook_id}.metadata")
            # Add content  
            zipf.write(content_path, f"{notebook_id}.content")
            # Add .rm file
            zipf.write(rm_file_path, f"{notebook_id}/{page_id}.rm")
            
        logger.info(f"Created test notebook at: {archive_path}")
        return archive_path, notebook_id, page_id
        
    except Exception as e:
        logger.error(f"Error creating test notebook: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

def main():
    """Main entry point for complete test."""
    parser = argparse.ArgumentParser(description="Complete test for Claude Penpal Service")
    parser.add_argument("--rmapi-path", type=str, help="Path to rmapi executable")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
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
    
    # Create test notebook
    logger.info("Creating test notebook with query...")
    notebook_path, notebook_id, page_id = create_test_notebook_with_query()
    
    # Upload the notebook
    logger.info("Uploading test notebook...")
    success, message = rmapi_adapter.upload_file(notebook_path, "Test_Penpal_Query_Notebook")
    
    if not success:
        logger.error(f"Failed to upload notebook: {message}")
        return 1
        
    logger.info("Successfully uploaded test notebook")
    time.sleep(3)  # Give the cloud time to process
    
    # Initialize service
    logger.info("Initializing Claude Penpal Service")
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
        if notebook.get("VissibleName") == "Test_Penpal_Query_Notebook":
            target_notebook = notebook
            break
            
    if not target_notebook:
        logger.error("Test notebook not found")
        return 1
        
    logger.info(f"Found test notebook: {target_notebook.get('VissibleName')}")
    
    try:
        # Process the notebook
        logger.info("Processing notebook for queries...")
        service._check_notebook_for_tagged_pages(target_notebook)
        logger.info("✅ Successfully processed notebook")
        return 0
        
    except Exception as e:
        logger.error(f"Error processing notebook: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
if __name__ == "__main__":
    sys.exit(main())