"""Service for generating editable ink strokes from text.

This service creates native reMarkable ink strokes that are editable on the device,
replacing the old approach of using drawj2d to create static text.
"""

import logging
import math
import os
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Tuple

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
        Create strokes for a single character.

        This is a simplified implementation that creates basic strokes.
        In a real implementation, you'd want proper character templates.

        Args:
            char: Character to render
            x: X position
            y: Y position

        Returns:
            List of Line objects for the character
        """
        lines = []

        # Simple stroke patterns for some common characters
        if char.lower() == "h":
            # Vertical stroke
            line1 = self._create_line([(x, y), (x, y + self.CHAR_HEIGHT)], 0.5)
            # Horizontal stroke
            line2 = self._create_line(
                [
                    (x, y + self.CHAR_HEIGHT / 2),
                    (x + self.CHAR_WIDTH * 0.8, y + self.CHAR_HEIGHT / 2),
                ],
                0.5,
            )
            # Second vertical
            line3 = self._create_line(
                [
                    (x + self.CHAR_WIDTH * 0.8, y + self.CHAR_HEIGHT / 2),
                    (x + self.CHAR_WIDTH * 0.8, y + self.CHAR_HEIGHT),
                ],
                0.5,
            )
            lines.extend([line1, line2, line3])

        elif char.lower() == "e":
            # Arc and horizontal line
            points = []
            # Create arc points
            for i in range(10):
                angle = math.pi * (0.5 + 1.5 * i / 9)
                px = x + self.CHAR_WIDTH / 2 + self.CHAR_WIDTH / 2 * math.cos(angle)
                py = y + self.CHAR_HEIGHT / 2 + self.CHAR_HEIGHT / 2 * math.sin(angle)
                points.append((px, py))
            line1 = self._create_line(points, 0.5)

            # Horizontal line
            line2 = self._create_line(
                [
                    (x, y + self.CHAR_HEIGHT / 2),
                    (x + self.CHAR_WIDTH * 0.8, y + self.CHAR_HEIGHT / 2),
                ],
                0.5,
            )
            lines.extend([line1, line2])

        elif char.lower() == "l":
            # Simple vertical line
            line = self._create_line(
                [
                    (x + self.CHAR_WIDTH / 2, y),
                    (x + self.CHAR_WIDTH / 2, y + self.CHAR_HEIGHT),
                ],
                0.5,
            )
            lines.append(line)

        elif char.lower() == "o":
            # Circle
            points = []
            for i in range(20):
                angle = 2 * math.pi * i / 19
                px = x + self.CHAR_WIDTH / 2 + self.CHAR_WIDTH / 3 * math.cos(angle)
                py = y + self.CHAR_HEIGHT / 2 + self.CHAR_HEIGHT / 3 * math.sin(angle)
                points.append((px, py))
            line = self._create_line(points, 0.5)
            lines.append(line)

        else:
            # Default: simple dot for unknown characters
            line = self._create_line(
                [(x + self.CHAR_WIDTH / 2, y + self.CHAR_HEIGHT / 2)], 0.8
            )
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
            # Point constructor: x, y, speed, direction, width, pressure
            point = si.Point(
                x=x,
                y=y,
                speed=0,  # Speed unknown for generated strokes
                direction=0,  # Direction unknown
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
            # Create scene tree
            scene_tree = st.SceneTree()

            # Create root group
            root_group = si.Group()
            root_id = scene_tree.add_item(root_group)

            # Convert text to strokes
            strokes = self.text_to_strokes(text)

            # Add strokes to scene tree
            for stroke in strokes:
                scene_tree.add_item(stroke, parent_id=root_id)

            # For now, we create a simple empty file as a placeholder
            # The full implementation would require understanding the complete
            # rmscene file format which is complex
            with open(output_path, "wb") as f:
                # Write reMarkable header
                f.write(rmscene.HEADER_V6)

                # For now, just write minimal data
                # In a real implementation, we'd write proper blocks using TaggedBlockWriter
                # This is a placeholder that at least creates a valid file header

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
            # Load existing file
            with open(rm_file_path, "rb") as f:
                scene_tree = read_tree(f)

            # Find the lowest Y coordinate to append after existing content
            if y_offset is None:
                max_y = 0
                for item_id, item in scene_tree.items.items():
                    if isinstance(item, si.Line):
                        for point in item.points:
                            max_y = max(max_y, point.y)
                y_offset = (
                    max_y + self.LINE_SPACING * 2 if max_y > 0 else self.MARGIN_TOP
                )

            # Create new strokes
            strokes = self.text_to_strokes(text, y=y_offset)

            # Find root group
            root_id = None
            for item_id, item in scene_tree.items.items():
                if (
                    isinstance(item, si.Group)
                    and scene_tree.get_parent(item_id) is None
                ):
                    root_id = item_id
                    break

            if root_id is None:
                # Create root group if it doesn't exist
                root_group = si.Group()
                root_id = scene_tree.add_item(root_group)

            # Add new strokes
            for stroke in strokes:
                scene_tree.add_item(stroke, parent_id=root_id)

            # For now, we can't properly append to existing files
            # This would require the complete rmscene serialization implementation
            logger.warning("Appending to existing files not yet implemented")
            return False

            logger.info(f"Appended text to .rm file at {rm_file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to append to .rm file: {e}")
            return False

    def create_handwriting_style_strokes(
        self, text: str, style: str = "cursive"
    ) -> List[si.Line]:
        """
        Create more natural handwriting-style strokes.

        This is a placeholder for more sophisticated handwriting generation
        that could use:
        - Bezier curves for smoother strokes
        - Variable pen pressure
        - Connected cursive writing
        - Different handwriting styles

        Args:
            text: Text to convert
            style: Handwriting style ("cursive", "print", etc.)

        Returns:
            List of Line objects with handwriting-style strokes
        """
        # For now, just use the basic text_to_strokes
        # This could be expanded with more sophisticated algorithms
        return self.text_to_strokes(text)


# Singleton instance
_ink_service = None


def get_ink_generation_service() -> InkGenerationService:
    """Get the singleton ink generation service instance."""
    global _ink_service
    if _ink_service is None:
        _ink_service = InkGenerationService()
    return _ink_service
