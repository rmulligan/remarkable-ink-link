"""Service for generating editable ink strokes from text.

This service creates native reMarkable ink strokes that are editable on the device,
replacing the old approach of using drawj2d to create static text.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from inklink.services.character_strokes import CharacterStrokes

logger = logging.getLogger(__name__)

try:
    import rmscene
    import rmscene.scene_items as si
    import rmscene.scene_tree as st
    from rmscene.scene_stream import TaggedBlockWriter, read_tree

    RMSCENE_AVAILABLE = True
except ImportError:
    logger.warning("rmscene not installed - cannot generate editable ink")
    RMSCENE_AVAILABLE = False


class InkGenerationService:
    """Service for generating editable ink strokes from text."""

    # Font metrics for simple character rendering
    CHAR_WIDTH = 20
    CHAR_HEIGHT = 30
    LINE_SPACING = 40
    MARGIN_LEFT = 100
    MARGIN_TOP = 100

    def __init__(self):
        """Initialize the ink generation service."""
        self.pen_type = si.Pen.BALLPOINT_1
        self.color = si.PenColor.BLACK
        self.character_strokes = CharacterStrokes()

    def text_to_strokes(self, text: str, x: int = None, y: int = None) -> List[si.Line]:
        """
        Convert text to a list of stroke Lines.

        Args:
            text: Text to convert
            x: Starting x position (default: MARGIN_LEFT)
            y: Starting y position (default: MARGIN_TOP)

        Returns:
            List of Line objects representing the text as strokes
        """
        if not RMSCENE_AVAILABLE:
            raise ImportError("rmscene is required for ink generation")

        lines = []
        current_x = x or self.MARGIN_LEFT
        current_y = y or self.MARGIN_TOP

        for char in text:
            if char == "\n":
                current_x = x or self.MARGIN_LEFT
                current_y += self.LINE_SPACING
                continue

            if char == " ":
                current_x += self.CHAR_WIDTH
                continue

            # Create strokes for the character
            char_strokes = self._create_character_strokes(char, current_x, current_y)
            lines.extend(char_strokes)

            current_x += self.CHAR_WIDTH

        return lines

    def _create_character_strokes(self, char: str, x: int, y: int) -> List[si.Line]:
        """
        Create strokes for a single character using the comprehensive character mapping.

        Args:
            char: Character to render
            x: X position
            y: Y position

        Returns:
            List of Line objects for the character
        """
        lines = []

        # Get stroke patterns from the character mapping
        strokes = self.character_strokes.get_strokes(char, x, y)

        # Convert each stroke pattern to a Line object
        for stroke_points in strokes:
            if stroke_points:  # Only create line if there are points
                line = self._create_line(stroke_points, 0.5)
                lines.append(line)

        return lines

    def _create_line(
        self, points: List[Tuple[float, float]], pressure: float = 0.5
    ) -> si.Line:
        """
        Create a Line object from points.

        Args:
            points: List of (x, y) tuples
            pressure: Pen pressure (0.0 to 1.0)

        Returns:
            Line object
        """
        # Create Point objects
        line_points = []
        for i, (x, y) in enumerate(points):
            # Calculate direction between consecutive points
            direction = 0
            if i < len(points) - 1:
                dx = points[i + 1][0] - x
                dy = points[i + 1][1] - y
                if dx != 0 or dy != 0:
                    direction = math.atan2(dy, dx)

            # Point constructor: x, y, speed, direction, width, pressure
            point = si.Point(
                x=x,
                y=y,
                speed=0,  # Speed unknown for generated strokes
                direction=direction,
                width=1.0,  # Standard width
                pressure=pressure,
            )
            line_points.append(point)

        # Create Line with all required parameters
        line = si.Line(
            color=self.color,
            tool=self.pen_type,
            points=line_points,
            thickness_scale=1.0,  # Standard thickness
            starting_length=0.0,  # Start at 0
        )
        return line

    def create_rm_file_with_text(self, text: str, output_path: str) -> bool:
        """
        Create a .rm file with editable text strokes.

        Args:
            text: Text to write
            output_path: Path to save the .rm file

        Returns:
            True if successful, False otherwise
        """
        if not RMSCENE_AVAILABLE:
            logger.error("rmscene not available - cannot create .rm file")
            return False

        try:
            from rmscene.scene_stream import (
                MainBlockInfo,
                SceneInfo,
                SceneLineItemBlock,
                TreeNodeBlock,
                write_blocks,
            )

            # Create blocks list for the reMarkable file
            blocks = []

            # 1. Create the main block
            main_block = MainBlockInfo()
            blocks.append(main_block)

            # 2. Create scene info
            scene_info = SceneInfo(
                file_type="reMarkable .lines file, version=6",
                x_max=1404.0,
                y_max=1872.0,
            )
            blocks.append(scene_info)

            # 3. Create a root node
            root_id = rmscene.CrdtId(0, 1)
            root_node = TreeNodeBlock(node_id=root_id, parent_id=None)
            blocks.append(root_node)

            # 4. Convert text to strokes and create line blocks
            strokes = self.text_to_strokes(text)

            for i, stroke in enumerate(strokes):
                line_id = rmscene.CrdtId(i + 1, 1)
                line_block = SceneLineItemBlock(
                    parent_id=root_id, item_id=line_id, line=stroke
                )
                blocks.append(line_block)

            # Write blocks to the file
            with open(output_path, "wb") as f:
                write_blocks(f, blocks)

            logger.info(f"Created .rm file with editable ink at {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create .rm file: {e}")
            return False

    def append_text_to_rm_file(
        self, rm_file_path: str, text: str, y_offset: int = None
    ) -> bool:
        """
        Append text as editable strokes to an existing .rm file.

        Args:
            rm_file_path: Path to existing .rm file
            text: Text to append
            y_offset: Y position to start writing (defaults to after existing content)

        Returns:
            True if successful, False otherwise
        """
        if not RMSCENE_AVAILABLE:
            logger.error("rmscene not available - cannot append to .rm file")
            return False

        try:
            from rmscene.scene_stream import (
                MainBlockInfo,
                SceneInfo,
                SceneLineItemBlock,
                TreeNodeBlock,
                write_blocks,
            )

            # Read existing file
            with open(rm_file_path, "rb") as f:
                blocks = list(read_tree(f))

            # Find the highest y-coordinate in existing strokes
            max_y = 0
            for block in blocks:
                if hasattr(block, "line") and hasattr(block.line, "points"):
                    for point in block.line.points:
                        if point.y > max_y:
                            max_y = point.y

            # Calculate y offset
            if y_offset is None:
                y_offset = max_y + self.LINE_SPACING

            # Convert text to strokes at the new position
            new_strokes = self.text_to_strokes(text, y=y_offset)

            # Find the root node and get the highest existing line ID
            root_id = None
            max_line_id = 0
            for block in blocks:
                if isinstance(block, TreeNodeBlock) and block.parent_id is None:
                    root_id = block.node_id
                elif isinstance(block, SceneLineItemBlock):
                    if block.item_id.value > max_line_id:
                        max_line_id = block.item_id.value

            if root_id is None:
                raise ValueError("Could not find root node in existing file")

            # Add new line blocks
            for i, stroke in enumerate(new_strokes):
                line_id = rmscene.CrdtId(max_line_id + i + 1, 1)
                line_block = SceneLineItemBlock(
                    parent_id=root_id, item_id=line_id, line=stroke
                )
                blocks.append(line_block)

            # Write updated blocks to the file
            with open(rm_file_path, "wb") as f:
                write_blocks(f, blocks)

            logger.info(f"Appended text to .rm file at {rm_file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to append to .rm file: {e}")
            return False
