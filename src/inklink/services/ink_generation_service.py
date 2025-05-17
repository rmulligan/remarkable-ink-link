"""Service for generating editable ink strokes from text.

This service creates native reMarkable ink strokes that are editable on the device,
replacing the old approach of using drawj2d to create static text.
"""

import logging
import math
from typing import List

from inklink.services.character_strokes import CharacterStrokes

logger = logging.getLogger(__name__)

try:
    import rmscene
    import rmscene.scene_items as si
    from rmscene.scene_stream import TaggedBlockWriter, read_tree
    from rmscene.scene_tree import SceneTree

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
            List of Line objects
        """
        if not RMSCENE_AVAILABLE:
            raise ImportError("rmscene is not available")

        if x is None:
            x = self.MARGIN_LEFT
        if y is None:
            y = self.MARGIN_TOP

        lines = []
        current_x = x
        current_y = y

        for char in text:
            if char == "\n":
                # Move to next line
                current_x = x
                current_y += self.LINE_SPACING
                continue

            if char == " ":
                # Just advance space without drawing
                current_x += self.CHAR_WIDTH
                continue

            # Get strokes for this character with the current position
            char_strokes = CharacterStrokes.get_strokes(
                char.upper(), current_x, current_y
            )

            for stroke in char_strokes:
                # Create points for this stroke
                points = []
                for i, (px, py) in enumerate(stroke):
                    # Points are already positioned by get_strokes
                    point_x = px
                    point_y = py

                    # Create point with parameters
                    # More pressure at the middle of the stroke
                    pressure = int(
                        127 + 50 * math.sin(i * math.pi / len(stroke))
                    )  # Convert to int 0-255

                    # Calculate speed based on point spacing
                    speed = 50  # Moderate speed
                    direction = 0  # Not used for drawing
                    width = 50  # Standard width

                    point = si.Point(
                        x=point_x,
                        y=point_y,
                        speed=speed,
                        direction=direction,
                        width=width,
                        pressure=pressure,
                    )
                    points.append(point)

                # Create line with points
                line = self._create_line(points)
                lines.append(line)

            # Advance to next character position
            current_x += self.CHAR_WIDTH + 5

        return lines

    def _create_line(self, points: List[si.Point]) -> si.Line:
        """
        Create a Line object from points.

        Args:
            points: List of Point objects

        Returns:
            Line object
        """
        # Line constructor requires all parameters
        line = si.Line(
            color=self.color,
            tool=self.pen_type,
            points=points,
            thickness_scale=1.0,
            starting_length=0.0,
        )
        return line

    @staticmethod
    def create_rm_file_with_text(text: str, output_path: str) -> bool:
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
            # Create simple text document using rmscene helper
            from rmscene.scene_stream import simple_text_document

            # Generate blocks for text document
            blocks = list(simple_text_document(text))

            logger.info(f"Generated {len(blocks)} blocks for text")

            # For now, let's just write the simple text document
            # TODO: Replace text with actual strokes later

            # Write to file
            with open(output_path, "wb") as f:
                # Use rmscene's write_blocks function to write all blocks
                from rmscene.scene_stream import write_blocks

                write_blocks(f, blocks)

            logger.info(f"Created .rm file with text at {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create .rm file: {e}")
            import traceback

            traceback.print_exc()
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
            # Read existing scene tree
            with open(rm_file_path, "rb") as f:
                existing_tree = read_tree(f)

            # Find the maximum Y position in existing content
            max_y = 0
            for item in existing_tree.items.values():
                if isinstance(item, si.Line) and item.points:
                    for point in item.points:
                        max_y = max(max_y, point.y)

            # Calculate Y offset
            if y_offset is None:
                y_offset = max_y + self.LINE_SPACING * 2

            # Create new strokes
            new_strokes = self.text_to_strokes(text, y=y_offset)

            # Find the root node
            root_id = None
            for item_id, item in existing_tree.items.items():
                if isinstance(item, si.Group):
                    root_id = item_id
                    break

            if root_id is None:
                logger.error("Could not find root group in existing file")
                return False

            # Add new strokes to existing tree
            for stroke in new_strokes:
                existing_tree.add_item(stroke, parent_id=root_id)

            # Write back to file
            with open(rm_file_path, "wb") as f:
                # Create a TaggedBlockWriter
                writer = TaggedBlockWriter(f)

                # Write the header
                writer.write_tag(
                    tag=rmscene.scene_stream.TagType.FILE_ID_V2, data=rmscene.HEADER_V6
                )

                # Write tree structure
                existing_tree.to_stream(writer)

                # Finalize
                writer.flush()

            logger.info(f"Appended text to .rm file at {rm_file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to append to .rm file: {e}")
            return False


# Global instance for singleton access
_ink_generation_service = None


def get_ink_generation_service() -> InkGenerationService:
    """Get the global ink generation service instance."""
    global _ink_generation_service
    if _ink_generation_service is None:
        _ink_generation_service = InkGenerationService()
    return _ink_generation_service
