#!/usr/bin/env python3
"""
Basic test for rmscene functionality.
This script tests if rmscene is working correctly.
"""

import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try importing rmscene
try:
    import rmscene

    logger.info(
        f"rmscene version: {rmscene.__version__ if hasattr(rmscene, '__version__') else 'unknown'}"
    )

    # Import specific modules
    try:
        import rmscene.scene_tree as st

        logger.info("Successfully imported rmscene.scene_tree")
    except ImportError as e:
        logger.error(f"Failed to import rmscene.scene_tree: {e}")

    try:
        import rmscene.scene_items as si

        logger.info("Successfully imported rmscene.scene_items")
    except ImportError as e:
        logger.error(f"Failed to import rmscene.scene_items: {e}")

    try:
        from rmscene.scene_stream import read_tree, write_tree

        logger.info(
            "Successfully imported read_tree and write_tree from rmscene.scene_stream"
        )
    except ImportError as e:
        logger.error(f"Failed to import from rmscene.scene_stream: {e}")

except ImportError as e:
    logger.error(f"Failed to import rmscene: {e}")
    sys.exit(1)

# Print available objects/attributes in each module
print("\nContents of rmscene:")
print(", ".join(sorted([item for item in dir(rmscene) if not item.startswith("_")])))

print("\nContents of rmscene.scene_tree:")
print(", ".join(sorted([item for item in dir(st) if not item.startswith("_")])))

print("\nContents of rmscene.scene_items:")
print(", ".join(sorted([item for item in dir(si) if not item.startswith("_")])))

# Create a simple scene tree and print its structure
try:
    print("\nCreating a simple scene tree...")
    scene_tree = st.SceneTree()

    # Create and add a group
    group = si.Group()
    group_id = scene_tree.add_item(group)
    print(f"Added group with ID: {group_id}")

    # Create and add a line
    line = si.Line()
    line.pen = si.Pen.FINELINER
    line.color = si.PenColor.BLACK

    # Create and add points
    points = [
        si.Point(x=100, y=100, pressure=0.5, t=0),
        si.Point(x=200, y=200, pressure=0.6, t=100),
        si.Point(x=300, y=100, pressure=0.5, t=200),
    ]
    line.points = points

    # Add the line to the scene tree
    line_id = scene_tree.add_item(line, parent_id=group_id)
    print(f"Added line with ID: {line_id}")

    # Print information about the scene tree
    print(f"\nScene tree has {len(scene_tree.items)} items")
    print(f"Scene tree root ID: {scene_tree.root_id}")

    # Count item types
    type_counts = {}
    for item in scene_tree.items.values():
        item_type = type(item).__name__
        type_counts[item_type] = type_counts.get(item_type, 0) + 1

    print("Item types in scene tree:")
    for type_name, count in type_counts.items():
        print(f"  {type_name}: {count}")

    # Print information about the line
    print(f"\nLine information:")
    print(f"  Pen: {line.pen}")
    print(f"  Color: {line.color}")
    print(f"  Points: {len(line.points)}")
    if line.points:
        print(
            f"  First point: x={line.points[0].x}, y={line.points[0].y}, pressure={line.points[0].pressure}, t={line.points[0].t}"
        )

    print("\nrmscene test completed successfully!")

except Exception as e:
    logger.error(f"Failed to create and manipulate scene tree: {e}")
    import traceback

    traceback.print_exc()
