#!/usr/bin/env python3
"""Simple test to verify rmscene works."""

import os
import sys
import tempfile

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from inklink.services.ink_generation_service import InkGenerationService

print("Testing rmscene functionality...")

service = InkGenerationService()

# Test creating a simple stroke
try:
    strokes = service.text_to_strokes("Hi")
    print(f"Created {len(strokes)} strokes")
    
    # Test creating a file
    with tempfile.NamedTemporaryFile(suffix='.rm', delete=False) as tmp:
        tmp_path = tmp.name
    
    success = service.create_rm_file_with_text("Hello World", tmp_path)
    if success:
        print(f"Successfully created .rm file at {tmp_path}")
        file_size = os.path.getsize(tmp_path)
        print(f"File size: {file_size} bytes")
    else:
        print("Failed to create .rm file")
    
    # Clean up
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()