#!/usr/bin/env python3
"""Test the real rmscene API with a simple example."""

import tempfile
import uuid

import rmscene
import rmscene.scene_items as si
import rmscene.scene_tree as st
from rmscene.scene_stream import (
    SceneLineItemBlock,
    SceneTree,
    SceneTreeBlock,
    TreeNodeBlock,
    read_tree,
    write_blocks,
)

# Create a simple scene tree
tree = SceneTree()

# Create a root group
root_group = si.Group()
# We need to create a CrdtId for the root

root_id = rmscene.CrdtId(0, uuid.uuid4())

# Add the root group to the tree
tree.add_node(root_id, None)  # Parent is None for root
tree.items[root_id] = root_group

# Create a simple line
line = si.Line()
line.pen = si.Pen.BALLPOINT_1
line.color = si.PenColor.BLACK

# Add some points
points = []
for i in range(5):
    point = si.Point(
        x=100 + i * 20,
        y=100,
        pressure=0.5,
        # t parameter doesn't exist in the constructor
    )
    points.append(point)

line.points = points

# Create a CrdtId for the line
line_id = rmscene.CrdtId(1, uuid.uuid4())

# Add the line to the tree
tree.add_item(line, parent_id=root_id)

print("Created scene tree with one line")

# Now let's try to save it
with tempfile.NamedTemporaryFile(delete=False, suffix=".rm") as tmp:
    tmp_path = tmp.name

# Convert tree to blocks
blocks = []

# Add SceneTreeBlock

# Create tree structure blocks
for node_id, node in tree.tree.items():
    tree_block = TreeNodeBlock(parent_id=node.parent, node_id=node_id)
    blocks.append(tree_block)

# Add scene items blocks

for item_id, item in tree.items.items():
    if isinstance(item, si.Line):
        # Create block for the line
        item_block = SceneLineItemBlock(
            parent_id=tree.get_parent(item_id),
            item_id=item_id,
            pen=item.pen,
            color=item.color,
            points=item.points,
        )
        blocks.append(item_block)

# Write the blocks
with open(tmp_path, "wb") as f:
    write_blocks(f, blocks)

print(f"Saved to {tmp_path}")

# Try to read it back
with open(tmp_path, "rb") as f:
    loaded_tree = read_tree(f)

print("Successfully read back!")
