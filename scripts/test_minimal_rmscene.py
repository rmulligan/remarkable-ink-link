#!/usr/bin/env python3
"""Minimal test of rmscene functionality."""
import uuid
from rmscene import scene_stream
from rmscene.scene_stream import simple_text_document

print("Testing simple_text_document function...")

# Create a simple text document
text = "Hello World"
doc_id = uuid.uuid4()  # Create a proper UUID

# Use the simple_text_document helper
si, tree = simple_text_document(text, doc_id)

print(f"Created document with ID: {doc_id}")
print(f"Scene info: {si}")
print(f"Tree has {len(tree.items)} items")

# Check what's in the tree
for item_id, item in tree.items.items():
    print(f"  Item {item_id}: {type(item)}")

# Now try to save it
print("\nTrying to save...")

# Check what methods the tree has
print("Tree methods:", [m for m in dir(tree) if not m.startswith("_")])

# Look for conversion methods
if hasattr(tree, "to_blocks"):
    print("Tree has to_blocks method")
    blocks = list(tree.to_blocks())
    print(f"Got {len(blocks)} blocks")
else:
    print("Tree doesn't have to_blocks method")

# Check the scene_stream module for saving functions

print("\nFunctions in scene_stream:")
for name in dir(scene_stream):
    if "write" in name.lower() or "save" in name.lower() or "block" in name.lower():
        print(f"  {name}")
