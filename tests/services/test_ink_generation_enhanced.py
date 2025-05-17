"""Tests for enhanced ink generation service with comprehensive character mapping."""

import os
import tempfile

import pytest

from inklink.services.ink_generation_service import InkGenerationService

# Mark as integration test that requires rmscene
pytestmark = pytest.mark.integration

try:
    import rmscene

    RMSCENE_AVAILABLE = True
except ImportError:
    RMSCENE_AVAILABLE = False


@pytest.mark.skipif(not RMSCENE_AVAILABLE, reason="rmscene not available")
class TestEnhancedInkGeneration:
    """Test enhanced ink generation with comprehensive character set."""

    def setup_method(self):
        """Set up test environment."""
        self.service = InkGenerationService()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up temp files
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_full_alphabet(self):
        """Test generating all letters of the alphabet."""
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        strokes = self.service.text_to_strokes(text)

        # Should have multiple strokes for each letter
        assert len(strokes) > 26, "Should have multiple strokes for the alphabet"

        # Test lowercase too
        text_lower = "abcdefghijklmnopqrstuvwxyz"
        strokes_lower = self.service.text_to_strokes(text_lower)
        assert len(strokes_lower) > 26, "Should handle lowercase letters"

    def test_numbers(self):
        """Test generating all digits."""
        text = "0123456789"
        strokes = self.service.text_to_strokes(text)

        # Should have strokes for each digit
        assert len(strokes) >= 10, "Should have strokes for all digits"

    def test_punctuation(self):
        """Test generating common punctuation."""
        text = ".,!?-_()[]{}'\":;+="
        strokes = self.service.text_to_strokes(text)

        # Should have strokes for punctuation
        assert len(strokes) > 0, "Should handle punctuation marks"

    def test_special_characters(self):
        """Test generating special characters."""
        text = "@#$%^&*<>/\\|"
        strokes = self.service.text_to_strokes(text)

        # Should have strokes for special characters
        assert len(strokes) > 0, "Should handle special characters"

    def test_mixed_content(self):
        """Test generating mixed content with text, numbers, and symbols."""
        text = "Hello World! 123 @#$"
        strokes = self.service.text_to_strokes(text)

        # Should have strokes for all characters
        assert len(strokes) > 10, "Should handle mixed content"

    def test_multiline_text(self):
        """Test generating multiline text."""
        text = "Line 1\nLine 2\nLine 3"
        strokes = self.service.text_to_strokes(text)

        # Should have strokes for all lines
        assert len(strokes) > 0, "Should handle multiline text"

        # Check that y-coordinates increase for different lines
        first_line_y = max(point.y for stroke in strokes[:5] for point in stroke.points)
        last_line_y = max(point.y for stroke in strokes[-5:] for point in stroke.points)
        assert last_line_y > first_line_y, "Lines should be positioned vertically"

    def test_create_file_with_all_characters(self):
        """Test creating .rm file with all supported characters."""
        # Create a sample text with various characters
        text = """The quick brown fox jumps over the lazy dog.
ABCDEFGHIJKLMNOPQRSTUVWXYZ
0123456789
Special: !@#$%^&*()_+-=[]{}\\|;:'"<>,.?/"""

        output_path = os.path.join(self.temp_dir, "all_characters.rm")

        # Create the file
        success = self.service.create_rm_file_with_text(text, output_path)
        assert success, "Should create .rm file successfully"
        assert os.path.exists(output_path), "File should exist"
        assert os.path.getsize(output_path) > 0, "File should not be empty"

    def test_unknown_character_fallback(self):
        """Test that unknown characters fall back to a dot."""
        # Use some uncommon Unicode characters
        text = "Test: \u2603 \u2764 \u263a"  # snowman, heart, smiley
        strokes = self.service.text_to_strokes(text)

        # Should still generate strokes (dots for unknown chars)
        assert len(strokes) > 0, "Should handle unknown characters gracefully"

    def test_character_spacing(self):
        """Test proper character spacing."""
        text = "HI"
        strokes = self.service.text_to_strokes(text)

        # Get x-coordinates of H and I
        h_strokes = strokes[:3]  # H has 3 strokes
        i_strokes = strokes[3:]  # I has 3 strokes

        h_max_x = max(point.x for stroke in h_strokes for point in stroke.points)
        i_min_x = min(point.x for stroke in i_strokes for point in stroke.points)

        # I should be to the right of H
        assert i_min_x > h_max_x, "Characters should be properly spaced"
