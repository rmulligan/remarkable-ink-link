#!/usr/bin/env python3
"""Debug rmscene import issue."""

import os
import sys

from inklink.services import ink_generation_service

print("Python version:", sys.version)

print("\nTrying to import rmscene...")
try:
    import rmscene

    print("✓ rmscene imported successfully")
except ImportError as e:
    print(f"✗ Failed to import rmscene: {e}")

print("\nTrying to import rmscene components...")
try:
    import rmscene.scene_items as si

    print("✓ rmscene.scene_items imported successfully")
except ImportError as e:
    print(f"✗ Failed to import rmscene.scene_items: {e}")

try:
    import rmscene.scene_tree as st

    print("✓ rmscene.scene_tree imported successfully")
except ImportError as e:
    print(f"✗ Failed to import rmscene.scene_tree: {e}")

try:
    from rmscene.scene_stream import read, write

    print("✓ rmscene.scene_stream functions imported successfully")
except ImportError as e:
    print(f"✗ Failed to import from rmscene.scene_stream: {e}")

# Check the global flag
print("\nChecking service module...")

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


print(f"RMSCENE_AVAILABLE in module: {ink_generation_service.RMSCENE_AVAILABLE}")
