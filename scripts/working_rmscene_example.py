#!/usr/bin/env python3
"""Working example based on test_rmscene_extraction_updated.py"""

import logging
import tempfile
import time
import uuid

# Try importing rmscene
try:
    import rmscene  # noqa: E402
    import rmscene.scene_items as si  # noqa: E402
    import rmscene.scene_tree as st  # noqa: E402
    from rmscene.scene_stream import (  # noqa: E402
        MainBlockInfo,
        SceneInfo,
        SceneLineItemBlock,
        SceneTree,
        SceneTreeBlock,
        TreeNodeBlock,
        read_tree,
        write_blocks,
    )

    RMSCENE_AVAILABLE = True
except ImportError:
    print("rmscene not installed or not properly configured")
    RMSCENE_AVAILABLE = False


def create_test_rm_file():
    """Create a test .rm file with simple strokes using the current rmscene API."""
    if not RMSCENE_AVAILABLE:
        print("rmscene not available - cannot create test .rm file")
        return None

    try:
        # We need to build the blocks manually for a reMarkable file
        blocks = []

        # 1. Create the header/main block
        main_block = MainBlockInfo()
        blocks.append(main_block)

        # 2. Create scene info
        scene_info = SceneInfo(
            file_type="reMarkable .lines file, version=6", x_max=1404.0, y_max=1872.0
        )
        blocks.append(scene_info)

        # 3. Create a root node
        root_id = rmscene.CrdtId(0, 1)
        root_node = TreeNodeBlock(node_id=root_id, parent_id=None)
        blocks.append(root_node)

        # 4. Create a line
        # Create a Line item
        line = si.Line()
        line.pen = si.Pen.BALLPOINT_1
        line.color = si.PenColor.BLACK

        # Add points
        points = []
        for i in range(10):
            point = si.Point(x=100 + i * 10, y=100, pressure=0.5)
            points.append(point)

        line.points = points

        # Create a line block
        line_id = rmscene.CrdtId(1, 1)
        line_block = SceneLineItemBlock(parent_id=root_id, item_id=line_id, line=line)
        blocks.append(line_block)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".rm") as temp_file:
            temp_path = temp_file.name

        # Write blocks to the file
        with open(temp_path, "wb") as f:
            write_blocks(f, blocks)

        print(f"Created test .rm file at {temp_path}")

        # Test reading it back
        with open(temp_path, "rb") as f:
            loaded_tree = read_tree(f)
            print(f"Successfully read back - tree has {len(loaded_tree.items)} items")

        return temp_path

    except Exception as e:
        print(f"Failed to create test .rm file: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    rm_file = create_test_rm_file()
    if rm_file:
        print(f"Success! Created {rm_file}")
    else:
        print("Failed to create .rm file")
