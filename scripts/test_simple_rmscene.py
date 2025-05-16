#!/usr/bin/env python3
"""Try to understand the rmscene API better."""

import os
import tempfile

import rmscene
from rmscene.scene_stream import (
    SceneInfo,
    TaggedBlockWriter,
    read_tree,
    simple_text_document,
    )

print("Testing simple_text_document function...")

# Create a simple text document
text = "Hello World"
doc_id = rmscene.UUID(1)

# Use the simple_text_document helper
si, tree = simple_text_document(text, doc_id)

print(f"Created document with ID: {doc_id}")
print(f"Scene info version: {si.file_type}")

# Try to save it
with tempfile.NamedTemporaryFile(delete=False, suffix=".rm") as tmp:
    tmp_path = tmp.name

# Create a writer
with open(tmp_path, "wb") as f:
    writer = TaggedBlockWriter(f)

    # First write the scene info
    si_block = SceneInfo(file_type=si.file_type, x_max=si.x_max, y_max=si.y_max)
    writer.write(si_block)

    # Write the tree blocks
    # Convert the tree to blocks
    blocks = []

    # Get all blocks from the tree
    # The tree object has methods to convert to blocks
    for block in tree.to_blocks():
        writer.write(block)

print(f"Saved to {tmp_path}")

# Try to read it back
with open(tmp_path, "rb") as f:
    loaded_tree = read_tree(f)

print("Successfully read back!")

# Clean up
os.unlink(tmp_path)
