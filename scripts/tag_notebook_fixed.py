#!/usr/bin/env python3
"""
Tag an existing reMarkable notebook with HasLilly and Lilly tags.
Corrected version with proper upload command.
"""

import os
import json
import logging
import tempfile
import zipfile
import sys
import subprocess
import shutil

from inklink.adapters.rmapi_adapter import RmapiAdapter
from inklink.config import CONFIG

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def run_rmapi_command(command, path=None):
    """Run rmapi command directly to work around upload issues."""
    rmapi_path = os.path.abspath("/home/ryan/dev/remarkable-ink-link/local-rmapi")
    if not os.path.exists(rmapi_path):
        rmapi_path = CONFIG.get("RMAPI_PATH", "./local-rmapi")
    
    base_cmd = [rmapi_path]
    if path:
        base_cmd.extend(["put", path])
    else:
        base_cmd.extend(command.split())
    
    try:
        logger.info(f"Running command: {' '.join(base_cmd)}")
        result = subprocess.run(
            base_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Log the output
        if result.stdout:
            logger.info(f"Command output: {result.stdout.strip()}")
        if result.stderr:
            logger.warning(f"Command error: {result.stderr.strip()}")
            
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        logger.error(f"Error running rmapi command: {e}")
        return False, "", str(e)

def tag_notebook(notebook_name):
    """
    Tag a notebook with HasLilly at document level and add Lilly tag to a page.
    
    Args:
        notebook_name: Name of the notebook to tag
    """
    # Initialize the RmapiAdapter
    rmapi_path = CONFIG.get("RMAPI_PATH", "./local-rmapi")
    adapter = RmapiAdapter(rmapi_path)
    
    # Verify the notebook exists
    success, notebooks = adapter.list_files()
    if not success:
        logger.error("Failed to list notebooks")
        return False
    
    target_notebook = None
    for notebook in notebooks:
        if notebook.get("VissibleName") == notebook_name and notebook.get("Type") == "DocumentType":
            target_notebook = notebook
            break
    
    if not target_notebook:
        logger.error(f"Notebook not found: {notebook_name}")
        return False
    
    notebook_id = target_notebook.get("ID")
    logger.info(f"Found notebook: {notebook_name} (ID: {notebook_id})")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download the notebook
        download_path = os.path.join(temp_dir, f"{notebook_name}.rmdoc")
        success, message = adapter.download_file(notebook_id, download_path, "zip")
        
        if not success:
            logger.error(f"Failed to download notebook: {message}")
            return False
        
        logger.info(f"Downloaded notebook to {download_path}")
        
        # Extract the notebook
        extraction_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extraction_dir, exist_ok=True)
        
        with zipfile.ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(extraction_dir)
        
        # Find content file
        content_file_path = None
        for root, _, files in os.walk(extraction_dir):
            for file in files:
                if file.endswith('.content'):
                    content_file_path = os.path.join(root, file)
                    break
        
        if not content_file_path:
            logger.error("No content file found in notebook")
            # Create a new content file
            content_id = os.path.basename(download_path).split('.')[0]
            if not content_id:
                import uuid
                content_id = str(uuid.uuid4())
            
            content_file_path = os.path.join(extraction_dir, f"{content_id}.content")
            metadata_file_path = os.path.join(extraction_dir, f"{content_id}.metadata")
            
            # Create basic content structure
            content = {"pages": []}
            metadata = {
                "visibleName": notebook_name,
                "type": "DocumentType", 
                "parent": "",
                "lastModified": str(int(os.path.getmtime(download_path) * 1000)),
                "lastOpened": str(int(os.path.getmtime(download_path) * 1000)),
                "lastOpenedPage": 0,
                "version": 1,
                "pinned": False,
                "synced": True,
                "modified": False,
                "deleted": False,
                "metadatamodified": False
            }
            
            # Write initial files
            with open(content_file_path, 'w') as f:
                json.dump(content, f, indent=2)
            
            with open(metadata_file_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        else:
            # Load content
            with open(content_file_path, 'r') as f:
                content = json.load(f)
                
            # Find and load metadata file
            metadata_file_path = os.path.join(
                os.path.dirname(content_file_path), 
                f"{os.path.splitext(os.path.basename(content_file_path))[0]}.metadata"
            )
            
            if os.path.exists(metadata_file_path):
                with open(metadata_file_path, 'r') as f:
                    metadata = json.load(f)
            else:
                # Create metadata if it doesn't exist
                metadata = {
                    "visibleName": notebook_name,
                    "type": "DocumentType",
                    "parent": "",
                    "lastModified": str(int(os.path.getmtime(content_file_path) * 1000)),
                    "lastOpened": str(int(os.path.getmtime(content_file_path) * 1000)),
                    "lastOpenedPage": 0,
                    "version": 1,
                    "pinned": False,
                    "synced": True,
                    "modified": False,
                    "deleted": False,
                    "metadatamodified": False
                }
        
        # Add HasLilly tag to notebook (in metadata)
        if "tags" not in metadata:
            metadata["tags"] = []
        
        if "HasLilly" not in metadata["tags"]:
            metadata["tags"].append("HasLilly")
            logger.info("Added HasLilly tag to notebook")
        
        # Get or create pages
        pages = content.get("pages", [])
        if not pages:
            logger.info("No pages found in notebook, creating a new page")
            # Create a new page ID
            import uuid
            page_id = str(uuid.uuid4())
            
            # Current timestamp in milliseconds
            import time
            now_ms = int(time.time() * 1000)
            
            # Create a page with the Lilly tag
            first_page = {
                "id": page_id,
                "visibleName": "Test Query Page",
                "lastModified": now_ms,
                "tags": ["Lilly"]
            }
            pages.append(first_page)
            content["pages"] = pages
            
            # Ensure pageTags exists
            if "pageTags" not in content or content["pageTags"] is None:
                content["pageTags"] = {}
            
            # Create page file
            page_dir = os.path.dirname(content_file_path)
            page_file_path = os.path.join(page_dir, f"{page_id}.rm")
            
            # Write simple test content
            with open(page_file_path, 'w') as f:
                f.write("Test content for the Lilly query page #Lilly")
                
            logger.info(f"Created new page with ID: {page_id}")
            
            # Update metadata timestamp
            metadata["lastModified"] = str(now_ms)
            metadata["version"] = metadata.get("version", 0) + 1
        else:
            # Add Lilly tag to first page
            first_page = pages[0]
            if "tags" not in first_page:
                first_page["tags"] = []
            
            if "Lilly" not in first_page["tags"]:
                first_page["tags"].append("Lilly")
                logger.info(f"Added Lilly tag to page: {first_page.get('visibleName', first_page.get('id'))}")
        
        # Save modified content
        with open(content_file_path, 'w') as f:
            json.dump(content, f, indent=2)
            
        # Save modified metadata
        with open(metadata_file_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create modified zip
        modified_path = os.path.join(temp_dir, f"{notebook_name}_modified.rmdoc")
        with zipfile.ZipFile(modified_path, 'w') as zipf:
            for root, _, files in os.walk(extraction_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, extraction_dir)
                    zipf.write(file_path, arcname)
        
        # First refresh rmapi to sync with remote state
        run_rmapi_command("refresh")
        
        # Upload with direct rmapi command (without file extension in target name)
        success, stdout, stderr = run_rmapi_command(None, modified_path)
        
        if not success:
            logger.error(f"Failed to upload using direct rmapi command: {stderr}")
            
            # Alternative: try to rename the uploaded file if it was created
            document_id = None
            for line in stdout.split('\n'):
                if "ID:" in line:
                    document_id = line.split("ID:")[1].strip()
                    break
                    
            if document_id:
                logger.info(f"Uploaded file with ID: {document_id}, trying to rename it")
                success, _, stderr = run_rmapi_command(f"mv {document_id} {notebook_name}")
                if success:
                    logger.info(f"Successfully renamed uploaded file to: {notebook_name}")
                    logger.info("You can now run the Claude Penpal service to process this notebook.")
                    return True
                else:
                    logger.error(f"Failed to rename uploaded file: {stderr}")
                    return False
            
            return False
        else:
            logger.info(f"Successfully tagged notebook: {notebook_name}")
            logger.info("You can now run the Claude Penpal service to process this notebook.")
            return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tag_notebook_fixed.py <notebook_name>")
        sys.exit(1)
    
    notebook_name = sys.argv[1]
    if tag_notebook(notebook_name):
        print(f"Successfully tagged notebook '{notebook_name}' with HasLilly and Lilly tags.")
    else:
        print(f"Failed to tag notebook '{notebook_name}'")
        sys.exit(1)