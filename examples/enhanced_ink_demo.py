"""Demo script showing enhanced ink generation with comprehensive character support."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from inklink.services.character_strokes import CharacterStrokes  # noqa: E402
from inklink.services.ink_generation_service import InkGenerationService  # noqa: E402


def create_demo_notebook():
    """Create a demo notebook showing all supported characters."""
    service = InkGenerationService()

    # Create demo text with all character types
    demo_text = """INKLINK CHARACTER DEMO
======================

Uppercase: ABCDEFGHIJKLMNOPQRSTUVWXYZ
Lowercase: abcdefghijklmnopqrstuvwxyz
Numbers: 0123456789

Basic Punctuation: . , ! ? - _ ' " : ;
Parentheses: ( ) [ ] { }
Math Operators: + - * / = < >
Special Characters: @ # $ % ^ & | \\ ~

Sample Text:
The quick brown fox jumps over the lazy dog.
Pack my box with five dozen liquor jugs.

Code Example:
def hello_world():
    print("Hello, World!")
    return 42

Math Example:
x^2 + y^2 = r^2
E = mc^2

Special Symbols:
Email: user@example.com
Phone: +1 (555) 123-4567
Price: $99.99 (20% off!)
Hashtags: #InkLink #ReMarkable
"""

    # Create output file
    output_path = os.path.join(os.path.dirname(__file__), "character_demo.rm")

    print("Creating demo notebook with comprehensive character set...")
    success = service.create_rm_file_with_text(demo_text, output_path)

    if success:
        print(f"Demo notebook created successfully: {output_path}")

        # Also create a visualization showing the character strokes
        create_character_visualization()
    else:
        print("Failed to create demo notebook")


def create_character_visualization():
    """Create a visual representation of character strokes for debugging."""
    import matplotlib.pyplot as plt
    import numpy as np

    # Create figure
    fig, axes = plt.subplots(6, 10, figsize=(20, 12))
    fig.suptitle("InkLink Character Stroke Patterns", fontsize=16)

    # Characters to display
    chars = (
        "ABCDEFGHIJ"
        + "KLMNOPQRST"
        + "UVWXYZ0123"
        + "456789.!?-"
        + "()[]{}@#$%"
        + "+-=<>/*&^|"
    )

    char_strokes = CharacterStrokes()

    for i, (ax, char) in enumerate(zip(axes.flat, chars)):
        ax.set_xlim(0, CharacterStrokes.CHAR_WIDTH)
        ax.set_ylim(CharacterStrokes.CHAR_HEIGHT, 0)  # Invert y-axis
        ax.set_aspect("equal")
        ax.set_title(f"'{char}'", fontsize=10)
        ax.axis("off")

        # Get strokes for character
        strokes = char_strokes.get_strokes(char, 0, 0)

        # Plot each stroke
        for stroke in strokes:
            if stroke:
                x_coords = [p[0] for p in stroke]
                y_coords = [p[1] for p in stroke]
                ax.plot(x_coords, y_coords, "b-", linewidth=2)

                # Mark start and end points
                if len(stroke) > 1:
                    ax.plot(stroke[0][0], stroke[0][1], "go", markersize=4)  # Start
                    ax.plot(stroke[-1][0], stroke[-1][1], "ro", markersize=4)  # End

    # Remove any empty subplots
    for i in range(len(chars), len(axes.flat)):
        fig.delaxes(axes.flat[i])

    plt.tight_layout()
    output_path = os.path.join(
        os.path.dirname(__file__), "character_strokes_visualization.png"
    )
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Character visualization saved: {output_path}")
    plt.close()


def test_specific_characters():
    """Test specific character combinations."""
    service = InkGenerationService()

    test_cases = [
        ("Hello", "Basic word"),
        ("A1B2", "Letters and numbers"),
        ("user@email", "Email format"),
        ("$19.99", "Currency"),
        ("C++", "Programming language"),
        ("1+1=2", "Math equation"),
        ("(x)", "Parentheses"),
        ("[OK]", "Brackets"),
        ("{code}", "Braces"),
        ('"quote"', "Quotes"),
    ]

    print("\nTesting specific character combinations:")
    for text, description in test_cases:
        strokes = service.text_to_strokes(text)
        print(f"  {description:20} '{text}' -> {len(strokes)} strokes")


if __name__ == "__main__":
    print("InkLink Enhanced Character Mapping Demo")
    print("=====================================")

    # Create demo notebook
    create_demo_notebook()

    # Test specific characters
    test_specific_characters()

    print("\nDemo complete!")
    print("Upload the generated .rm file to your reMarkable device to see the results.")
