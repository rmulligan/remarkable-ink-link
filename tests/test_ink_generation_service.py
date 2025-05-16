"""Test ink generation service for creating editable strokes."""

import os
import pytest
import tempfile

try:
    import rmscene
    import rmscene.scene_items as si
    from rmscene.scene_stream import read

    RMSCENE_AVAILABLE = True
except ImportError:
    RMSCENE_AVAILABLE = False

from inklink.services.ink_generation_service import (
    InkGenerationService,
    get_ink_generation_service,
)


@pytest.mark.skipif(not RMSCENE_AVAILABLE, reason="rmscene not available")
class TestInkGenerationService:
    """Test ink generation functionality."""

    def test_singleton_instance(self):
        """Test that service returns singleton instance."""
        service1 = get_ink_generation_service()
        service2 = get_ink_generation_service()
        assert service1 is service2

    def test_text_to_strokes(self):
        """Test converting text to stroke Lines."""
        service = InkGenerationService()

        strokes = service.text_to_strokes("hello")

        assert len(strokes) > 0
        for stroke in strokes:
            assert isinstance(stroke, si.Line)
            assert stroke.pen == si.Pen.BALLPOINT_1
            assert stroke.color == si.PenColor.BLACK
            assert len(stroke.points) > 0

    def test_create_rm_file_with_text(self):
        """Test creating a .rm file with editable text."""
        service = InkGenerationService()

        with tempfile.NamedTemporaryFile(suffix=".rm", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            success = service.create_rm_file_with_text("Test Text", tmp_path)
            assert success
            assert os.path.exists(tmp_path)

            # Verify the file can be read back
            with open(tmp_path, "rb") as f:
                scene_tree = read(f)

            # Check that strokes were added
            has_lines = False
            for item_id, item in scene_tree.items.items():
                if isinstance(item, si.Line):
                    has_lines = True
                    break
            assert has_lines

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_append_text_to_rm_file(self):
        """Test appending text to existing .rm file."""
        service = InkGenerationService()

        with tempfile.NamedTemporaryFile(suffix=".rm", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Create initial file
            success = service.create_rm_file_with_text("First Line", tmp_path)
            assert success

            # Append text
            success = service.append_text_to_rm_file(tmp_path, "Second Line")
            assert success

            # Verify both texts are in the file
            with open(tmp_path, "rb") as f:
                scene_tree = read(f)

            # Count strokes - should have strokes for both lines
            stroke_count = 0
            for item_id, item in scene_tree.items.items():
                if isinstance(item, si.Line):
                    stroke_count += 1

            # Should have strokes for "First Line" and "Second Line"
            assert stroke_count > 10  # Both lines should generate multiple strokes

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_character_strokes(self):
        """Test that specific characters generate correct stroke patterns."""
        service = InkGenerationService()

        # Test individual characters
        for char in ["h", "e", "l", "o"]:
            strokes = service._create_character_strokes(char, 100, 100)
            assert len(strokes) > 0

            for stroke in strokes:
                assert isinstance(stroke, si.Line)
                assert len(stroke.points) > 0

    def test_multiline_text(self):
        """Test handling of multiline text."""
        service = InkGenerationService()

        text = "Line 1\nLine 2\nLine 3"
        strokes = service.text_to_strokes(text)

        assert len(strokes) > 0

        # Check that Y coordinates increase for different lines
        y_coords = []
        for stroke in strokes:
            for point in stroke.points:
                y_coords.append(point.y)

        # Should have multiple Y levels for different lines
        unique_y_levels = len(set(int(y / service.LINE_SPACING) for y in y_coords))
        assert unique_y_levels >= 3

    def test_custom_position(self):
        """Test creating strokes at custom position."""
        service = InkGenerationService()

        custom_x, custom_y = 200, 300
        strokes = service.text_to_strokes("Test", x=custom_x, y=custom_y)

        # Check that strokes start near the custom position
        first_point = strokes[0].points[0]
        assert abs(first_point.x - custom_x) < 50  # Within reasonable range
        assert abs(first_point.y - custom_y) < 50


@pytest.mark.skipif(RMSCENE_AVAILABLE, reason="Test for when rmscene is not available")
def test_rmscene_not_available():
    """Test behavior when rmscene is not available."""
    service = InkGenerationService()

    with pytest.raises(ImportError):
        service.text_to_strokes("test")

    with tempfile.NamedTemporaryFile(suffix=".rm") as tmp:
        success = service.create_rm_file_with_text("test", tmp.name)
        assert not success
