"""Character stroke definitions for ink generation.

This module provides comprehensive stroke patterns for generating
readable handwritten characters in the reMarkable format.
"""

import math
from typing import List, Tuple


class CharacterStrokes:
    """Stroke patterns for generating handwritten characters."""

    # Character dimensions
    CHAR_WIDTH = 20
    CHAR_HEIGHT = 30
    STROKE_SPACING = 2  # Space between strokes in multi-stroke chars

    @staticmethod
    def get_strokes(char: str, x: float, y: float) -> List[List[Tuple[float, float]]]:
        """
        Get stroke patterns for a character.

        Args:
            char: Character to render
            x: Starting x position
            y: Starting y position

        Returns:
            List of strokes, where each stroke is a list of (x, y) points
        """
        char = char.upper()

        # Map characters to their stroke generation methods
        stroke_map = {
            # Uppercase letters
            "A": CharacterStrokes._stroke_A,
            "B": CharacterStrokes._stroke_B,
            "C": CharacterStrokes._stroke_C,
            "D": CharacterStrokes._stroke_D,
            "E": CharacterStrokes._stroke_E,
            "F": CharacterStrokes._stroke_F,
            "G": CharacterStrokes._stroke_G,
            "H": CharacterStrokes._stroke_H,
            "I": CharacterStrokes._stroke_I,
            "J": CharacterStrokes._stroke_J,
            "K": CharacterStrokes._stroke_K,
            "L": CharacterStrokes._stroke_L,
            "M": CharacterStrokes._stroke_M,
            "N": CharacterStrokes._stroke_N,
            "O": CharacterStrokes._stroke_O,
            "P": CharacterStrokes._stroke_P,
            "Q": CharacterStrokes._stroke_Q,
            "R": CharacterStrokes._stroke_R,
            "S": CharacterStrokes._stroke_S,
            "T": CharacterStrokes._stroke_T,
            "U": CharacterStrokes._stroke_U,
            "V": CharacterStrokes._stroke_V,
            "W": CharacterStrokes._stroke_W,
            "X": CharacterStrokes._stroke_X,
            "Y": CharacterStrokes._stroke_Y,
            "Z": CharacterStrokes._stroke_Z,
            # Numbers
            "0": CharacterStrokes._stroke_0,
            "1": CharacterStrokes._stroke_1,
            "2": CharacterStrokes._stroke_2,
            "3": CharacterStrokes._stroke_3,
            "4": CharacterStrokes._stroke_4,
            "5": CharacterStrokes._stroke_5,
            "6": CharacterStrokes._stroke_6,
            "7": CharacterStrokes._stroke_7,
            "8": CharacterStrokes._stroke_8,
            "9": CharacterStrokes._stroke_9,
            # Common punctuation
            ".": CharacterStrokes._stroke_period,
            ",": CharacterStrokes._stroke_comma,
            "!": CharacterStrokes._stroke_exclamation,
            "?": CharacterStrokes._stroke_question,
            "-": CharacterStrokes._stroke_dash,
            "_": CharacterStrokes._stroke_underscore,
            "(": CharacterStrokes._stroke_left_paren,
            ")": CharacterStrokes._stroke_right_paren,
            "[": CharacterStrokes._stroke_left_bracket,
            "]": CharacterStrokes._stroke_right_bracket,
            "{": CharacterStrokes._stroke_left_brace,
            "}": CharacterStrokes._stroke_right_brace,
            '"': CharacterStrokes._stroke_quote,
            "'": CharacterStrokes._stroke_apostrophe,
            ":": CharacterStrokes._stroke_colon,
            ";": CharacterStrokes._stroke_semicolon,
            "+": CharacterStrokes._stroke_plus,
            "=": CharacterStrokes._stroke_equals,
            "<": CharacterStrokes._stroke_less_than,
            ">": CharacterStrokes._stroke_greater_than,
            "/": CharacterStrokes._stroke_slash,
            "\\": CharacterStrokes._stroke_backslash,
            "|": CharacterStrokes._stroke_pipe,
            "@": CharacterStrokes._stroke_at,
            "#": CharacterStrokes._stroke_hash,
            "$": CharacterStrokes._stroke_dollar,
            "%": CharacterStrokes._stroke_percent,
            "^": CharacterStrokes._stroke_caret,
            "&": CharacterStrokes._stroke_ampersand,
            "*": CharacterStrokes._stroke_asterisk,
        }

        # Get strokes for the character
        if char in stroke_map:
            strokes = stroke_map[char](x, y)
        else:
            # Default: small dot for unknown characters
            strokes = [
                [
                    (
                        x + CharacterStrokes.CHAR_WIDTH / 2,
                        y + CharacterStrokes.CHAR_HEIGHT / 2,
                    )
                ]
            ]

        return strokes

    # Letter stroke definitions
    @staticmethod
    def _stroke_A(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter A."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Left diagonal
            [(x, y + h), (x + w / 2, y)],
            # Right diagonal
            [(x + w / 2, y), (x + w, y + h)],
            # Horizontal bar
            [(x + w / 4, y + h / 2), (x + 3 * w / 4, y + h / 2)],
        ]

    @staticmethod
    def _stroke_B(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter B."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x, y), (x, y + h)],
            # Top curve
            [(x, y), (x + 3 * w / 4, y), (x + 3 * w / 4, y + h / 2), (x, y + h / 2)],
            # Bottom curve
            [
                (x, y + h / 2),
                (x + 3 * w / 4, y + h / 2),
                (x + 3 * w / 4, y + h),
                (x, y + h),
            ],
        ]

    @staticmethod
    def _stroke_C(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter C."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Arc from top to bottom
        points = []
        for i in range(15):
            angle = math.pi * (0.3 + 1.4 * i / 14)
            px = x + w / 2 + w / 2 * math.cos(angle)
            py = y + h / 2 + h / 2 * math.sin(angle)
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_D(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter D."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x, y), (x, y + h)],
            # Curved part
            [
                (x, y),
                (x + 3 * w / 4, y),
                (x + w, y + h / 2),
                (x + 3 * w / 4, y + h),
                (x, y + h),
            ],
        ]

    @staticmethod
    def _stroke_E(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter E."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x, y), (x, y + h)],
            # Top horizontal
            [(x, y), (x + 3 * w / 4, y)],
            # Middle horizontal
            [(x, y + h / 2), (x + 2 * w / 3, y + h / 2)],
            # Bottom horizontal
            [(x, y + h), (x + 3 * w / 4, y + h)],
        ]

    @staticmethod
    def _stroke_F(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter F."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x, y), (x, y + h)],
            # Top horizontal
            [(x, y), (x + 3 * w / 4, y)],
            # Middle horizontal
            [(x, y + h / 2), (x + 2 * w / 3, y + h / 2)],
        ]

    @staticmethod
    def _stroke_G(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter G."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Arc similar to C
        points = []
        for i in range(15):
            angle = math.pi * (0.3 + 1.4 * i / 14)
            px = x + w / 2 + w / 2 * math.cos(angle)
            py = y + h / 2 + h / 2 * math.sin(angle)
            points.append((px, py))
        return [
            points,
            # Horizontal bar
            [(x + w / 2, y + h / 2), (x + 3 * w / 4, y + h / 2)],
            # Vertical bar
            [(x + 3 * w / 4, y + h / 2), (x + 3 * w / 4, y + 3 * h / 4)],
        ]

    @staticmethod
    def _stroke_H(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter H."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Left vertical
            [(x, y), (x, y + h)],
            # Right vertical
            [(x + w, y), (x + w, y + h)],
            # Horizontal bar
            [(x, y + h / 2), (x + w, y + h / 2)],
        ]

    @staticmethod
    def _stroke_I(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter I."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Top horizontal
            [(x + w / 4, y), (x + 3 * w / 4, y)],
            # Vertical
            [(x + w / 2, y), (x + w / 2, y + h)],
            # Bottom horizontal
            [(x + w / 4, y + h), (x + 3 * w / 4, y + h)],
        ]

    @staticmethod
    def _stroke_J(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter J."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Vertical line with curve at bottom
        points = [(x + 2 * w / 3, y)]
        for i in range(10):
            py = y + i * h * 0.7 / 9
            points.append((x + 2 * w / 3, py))
        # Add curve
        for i in range(5):
            angle = math.pi * i / 4
            px = x + w / 3 + w / 3 * math.cos(angle)
            py = y + 3 * h / 4 + h / 4 * math.sin(angle)
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_K(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter K."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x, y), (x, y + h)],
            # Upper diagonal
            [(x + w, y), (x, y + h / 2)],
            # Lower diagonal
            [(x, y + h / 2), (x + w, y + h)],
        ]

    @staticmethod
    def _stroke_L(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter L."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x, y), (x, y + h)],
            # Horizontal line
            [(x, y + h), (x + 3 * w / 4, y + h)],
        ]

    @staticmethod
    def _stroke_M(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter M."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Left vertical
            [(x, y + h), (x, y)],
            # Left diagonal
            [(x, y), (x + w / 2, y + h / 2)],
            # Right diagonal
            [(x + w / 2, y + h / 2), (x + w, y)],
            # Right vertical
            [(x + w, y), (x + w, y + h)],
        ]

    @staticmethod
    def _stroke_N(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter N."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Left vertical
            [(x, y + h), (x, y)],
            # Diagonal
            [(x, y), (x + w, y + h)],
            # Right vertical
            [(x + w, y + h), (x + w, y)],
        ]

    @staticmethod
    def _stroke_O(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter O."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Circle
        points = []
        for i in range(20):
            angle = 2 * math.pi * i / 19
            px = x + w / 2 + w / 2.5 * math.cos(angle)
            py = y + h / 2 + h / 2.5 * math.sin(angle)
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_P(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter P."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x, y), (x, y + h)],
            # Top curve
            [(x, y), (x + 3 * w / 4, y), (x + 3 * w / 4, y + h / 2), (x, y + h / 2)],
        ]

    @staticmethod
    def _stroke_Q(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter Q."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Circle
        points = []
        for i in range(20):
            angle = 2 * math.pi * i / 19
            px = x + w / 2 + w / 2.5 * math.cos(angle)
            py = y + h / 2 + h / 2.5 * math.sin(angle)
            points.append((px, py))
        return [
            points,
            # Tail
            [(x + 2 * w / 3, y + 2 * h / 3), (x + w, y + h)],
        ]

    @staticmethod
    def _stroke_R(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter R."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x, y), (x, y + h)],
            # Top curve
            [(x, y), (x + 3 * w / 4, y), (x + 3 * w / 4, y + h / 2), (x, y + h / 2)],
            # Diagonal leg
            [(x, y + h / 2), (x + w, y + h)],
        ]

    @staticmethod
    def _stroke_S(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter S."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # S-curve
        points = []
        for i in range(15):
            t = i / 14
            if t < 0.5:
                # Top curve
                angle = math.pi * (0.5 - t)
                px = x + 3 * w / 4 + w / 4 * math.cos(angle)
                py = y + h / 4 + h / 4 * math.sin(angle)
            else:
                # Bottom curve
                angle = math.pi * (1.5 - t)
                px = x + w / 4 + w / 4 * math.cos(angle)
                py = y + 3 * h / 4 + h / 4 * math.sin(angle)
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_T(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter T."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Horizontal top
            [(x, y), (x + w, y)],
            # Vertical
            [(x + w / 2, y), (x + w / 2, y + h)],
        ]

    @staticmethod
    def _stroke_U(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter U."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # U-shape
        points = [(x, y)]
        # Left side
        for i in range(5):
            py = y + i * h * 0.7 / 4
            points.append((x, py))
        # Bottom curve
        for i in range(6):
            angle = math.pi + math.pi * i / 5
            px = x + w / 2 + w / 2 * math.cos(angle)
            py = y + 3 * h / 4 + h / 4 * math.sin(angle)
            points.append((px, py))
        # Right side
        for i in range(5):
            py = y + 3 * h / 4 - i * h * 0.7 / 4
            points.append((x + w, py))
        return [points]

    @staticmethod
    def _stroke_V(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter V."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Left diagonal
            [(x, y), (x + w / 2, y + h)],
            # Right diagonal
            [(x + w / 2, y + h), (x + w, y)],
        ]

    @staticmethod
    def _stroke_W(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter W."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # First downstroke
            [(x, y), (x + w / 4, y + h)],
            # First upstroke
            [(x + w / 4, y + h), (x + w / 2, y + h / 2)],
            # Second downstroke
            [(x + w / 2, y + h / 2), (x + 3 * w / 4, y + h)],
            # Second upstroke
            [(x + 3 * w / 4, y + h), (x + w, y)],
        ]

    @staticmethod
    def _stroke_X(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter X."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Diagonal 1
            [(x, y), (x + w, y + h)],
            # Diagonal 2
            [(x + w, y), (x, y + h)],
        ]

    @staticmethod
    def _stroke_Y(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter Y."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Left diagonal
            [(x, y), (x + w / 2, y + h / 2)],
            # Right diagonal
            [(x + w, y), (x + w / 2, y + h / 2)],
            # Vertical
            [(x + w / 2, y + h / 2), (x + w / 2, y + h)],
        ]

    @staticmethod
    def _stroke_Z(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for letter Z."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Top horizontal
            [(x, y), (x + w, y)],
            # Diagonal
            [(x + w, y), (x, y + h)],
            # Bottom horizontal
            [(x, y + h), (x + w, y + h)],
        ]

    # Number stroke definitions
    @staticmethod
    def _stroke_0(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 0."""
        return CharacterStrokes._stroke_O(x, y)  # Same as letter O

    @staticmethod
    def _stroke_1(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 1."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x + w / 2, y), (x + w / 2, y + h)],
            # Small diagonal at top
            [(x + w / 3, y + h / 6), (x + w / 2, y)],
        ]

    @staticmethod
    def _stroke_2(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 2."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Curve at top then diagonal to bottom
        points = []
        # Top curve
        for i in range(8):
            angle = -math.pi / 2 + math.pi * i / 7
            px = x + w / 2 + w / 3 * math.cos(angle)
            py = y + h / 4 + h / 4 * math.sin(angle)
            points.append((px, py))
        # Diagonal down
        points.extend([(x, y + h), (x + w, y + h)])
        return [points]

    @staticmethod
    def _stroke_3(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 3."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Top curve
            [
                (x, y),
                (x + 3 * w / 4, y),
                (x + 3 * w / 4, y + h / 2),
                (x + w / 4, y + h / 2),
            ],
            # Bottom curve
            [
                (x + w / 4, y + h / 2),
                (x + 3 * w / 4, y + h / 2),
                (x + 3 * w / 4, y + h),
                (x, y + h),
            ],
        ]

    @staticmethod
    def _stroke_4(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 4."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical
            [(x + 3 * w / 4, y), (x + 3 * w / 4, y + h)],
            # Diagonal
            [(x, y + 2 * h / 3), (x + 3 * w / 4, y), (x + 3 * w / 4, y + 2 * h / 3)],
            # Horizontal
            [(x, y + 2 * h / 3), (x + w, y + 2 * h / 3)],
        ]

    @staticmethod
    def _stroke_5(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 5."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Top horizontal
            [(x + w, y), (x, y)],
            # Vertical
            [(x, y), (x, y + h / 2)],
            # Curve
            [
                (x, y + h / 2),
                (x + 3 * w / 4, y + h / 2),
                (x + 3 * w / 4, y + h),
                (x, y + h),
            ],
        ]

    @staticmethod
    def _stroke_6(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 6."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Large curve with loop at bottom
        points = []
        for i in range(20):
            if i < 12:
                # Top curve
                angle = math.pi / 2 + math.pi * i / 11
                px = x + w / 2 + w / 2 * math.cos(angle)
                py = y + h / 3 + h / 3 * math.sin(angle)
            else:
                # Bottom circle
                angle = 2 * math.pi * (i - 12) / 7
                px = x + w / 2 + w / 3 * math.cos(angle)
                py = y + 2 * h / 3 + h / 3 * math.sin(angle)
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_7(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 7."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Top horizontal
            [(x, y), (x + w, y)],
            # Diagonal
            [(x + w, y), (x + w / 3, y + h)],
        ]

    @staticmethod
    def _stroke_8(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 8."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Figure-8 shape
        points = []
        for i in range(20):
            t = 2 * math.pi * i / 19
            if math.sin(t) >= 0:
                # Top loop
                px = x + w / 2 + w / 3 * math.cos(t)
                py = y + h / 3 + h / 4 * math.sin(t)
            else:
                # Bottom loop
                px = x + w / 2 + w / 3 * math.cos(t)
                py = y + 2 * h / 3 + h / 3 * math.sin(t)
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_9(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for number 9."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Circle at top with tail
        points = []
        # Top circle
        for i in range(15):
            angle = 2 * math.pi * i / 14
            px = x + w / 2 + w / 3 * math.cos(angle)
            py = y + h / 3 + h / 3 * math.sin(angle)
            points.append((px, py))
        # Tail
        points.extend([(x + 5 * w / 6, y + h / 3), (x + 5 * w / 6, y + h)])
        return [points]

    # Punctuation and special characters
    @staticmethod
    def _stroke_period(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for period."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [[(x + w / 2, y + 4 * h / 5), (x + w / 2 + 1, y + 4 * h / 5 + 1)]]

    @staticmethod
    def _stroke_comma(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for comma."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [[(x + w / 2, y + 3 * h / 4), (x + w / 2 - 2, y + h)]]

    @staticmethod
    def _stroke_exclamation(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for exclamation mark."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical line
            [(x + w / 2, y), (x + w / 2, y + 2 * h / 3)],
            # Dot
            [(x + w / 2, y + 5 * h / 6), (x + w / 2 + 1, y + 5 * h / 6 + 1)],
        ]

    @staticmethod
    def _stroke_question(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for question mark."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Question curve
        points = []
        for i in range(10):
            angle = -math.pi / 2 + math.pi * i / 9
            px = x + w / 2 + w / 3 * math.cos(angle)
            py = y + h / 4 + h / 4 * math.sin(angle)
            points.append((px, py))
        points.extend([(x + w / 2, y + h / 2), (x + w / 2, y + 2 * h / 3)])
        return [
            points,
            # Dot
            [(x + w / 2, y + 5 * h / 6), (x + w / 2 + 1, y + 5 * h / 6 + 1)],
        ]

    @staticmethod
    def _stroke_dash(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for dash/hyphen."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [[(x + w / 4, y + h / 2), (x + 3 * w / 4, y + h / 2)]]

    @staticmethod
    def _stroke_underscore(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for underscore."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [[(x, y + h), (x + w, y + h)]]

    @staticmethod
    def _stroke_left_paren(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for left parenthesis."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        points = []
        for i in range(10):
            t = i / 9
            px = x + 2 * w / 3 - w / 3 * (0.5 - abs(0.5 - t))
            py = y + t * h
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_right_paren(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for right parenthesis."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        points = []
        for i in range(10):
            t = i / 9
            px = x + w / 3 + w / 3 * (0.5 - abs(0.5 - t))
            py = y + t * h
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_left_bracket(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for left bracket."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            [
                (x + 2 * w / 3, y),
                (x + w / 3, y),
                (x + w / 3, y + h),
                (x + 2 * w / 3, y + h),
            ]
        ]

    @staticmethod
    def _stroke_right_bracket(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for right bracket."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            [
                (x + w / 3, y),
                (x + 2 * w / 3, y),
                (x + 2 * w / 3, y + h),
                (x + w / 3, y + h),
            ]
        ]

    @staticmethod
    def _stroke_left_brace(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for left brace."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        points = []
        # Top curve
        for i in range(5):
            angle = math.pi / 2 * i / 4
            px = x + 2 * w / 3 - w / 6 * math.cos(angle)
            py = y + h / 6 + h / 6 * math.sin(angle)
            points.append((px, py))
        # Middle point
        points.append((x + w / 3, y + h / 2))
        # Bottom curve
        for i in range(5):
            angle = -math.pi / 2 * i / 4
            px = x + 2 * w / 3 - w / 6 * math.cos(angle)
            py = y + 5 * h / 6 + h / 6 * math.sin(angle)
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_right_brace(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for right brace."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        points = []
        # Top curve
        for i in range(5):
            angle = math.pi - math.pi / 2 * i / 4
            px = x + w / 3 + w / 6 * math.cos(angle)
            py = y + h / 6 + h / 6 * math.sin(angle)
            points.append((px, py))
        # Middle point
        points.append((x + 2 * w / 3, y + h / 2))
        # Bottom curve
        for i in range(5):
            angle = math.pi + math.pi / 2 * i / 4
            px = x + w / 3 + w / 6 * math.cos(angle)
            py = y + 5 * h / 6 + h / 6 * math.sin(angle)
            points.append((px, py))
        return [points]

    @staticmethod
    def _stroke_quote(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for double quote."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            [(x + w / 3, y + h / 6), (x + w / 3, y + h / 3)],
            [(x + 2 * w / 3, y + h / 6), (x + 2 * w / 3, y + h / 3)],
        ]

    @staticmethod
    def _stroke_apostrophe(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for apostrophe/single quote."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [[(x + w / 2, y + h / 6), (x + w / 2, y + h / 3)]]

    @staticmethod
    def _stroke_colon(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for colon."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            [(x + w / 2, y + h / 3), (x + w / 2 + 1, y + h / 3 + 1)],
            [(x + w / 2, y + 2 * h / 3), (x + w / 2 + 1, y + 2 * h / 3 + 1)],
        ]

    @staticmethod
    def _stroke_semicolon(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for semicolon."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            [(x + w / 2, y + h / 3), (x + w / 2 + 1, y + h / 3 + 1)],
            [(x + w / 2, y + 2 * h / 3), (x + w / 2 - 2, y + 5 * h / 6)],
        ]

    @staticmethod
    def _stroke_plus(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for plus sign."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Horizontal
            [(x + w / 6, y + h / 2), (x + 5 * w / 6, y + h / 2)],
            # Vertical
            [(x + w / 2, y + h / 3), (x + w / 2, y + 2 * h / 3)],
        ]

    @staticmethod
    def _stroke_equals(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for equals sign."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Top line
            [(x + w / 6, y + 2 * h / 5), (x + 5 * w / 6, y + 2 * h / 5)],
            # Bottom line
            [(x + w / 6, y + 3 * h / 5), (x + 5 * w / 6, y + 3 * h / 5)],
        ]

    @staticmethod
    def _stroke_less_than(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for less than sign."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            [
                (x + 3 * w / 4, y + h / 3),
                (x + w / 4, y + h / 2),
                (x + 3 * w / 4, y + 2 * h / 3),
            ]
        ]

    @staticmethod
    def _stroke_greater_than(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for greater than sign."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            [
                (x + w / 4, y + h / 3),
                (x + 3 * w / 4, y + h / 2),
                (x + w / 4, y + 2 * h / 3),
            ]
        ]

    @staticmethod
    def _stroke_slash(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for forward slash."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [[(x + w / 4, y + h), (x + 3 * w / 4, y)]]

    @staticmethod
    def _stroke_backslash(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for backslash."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [[(x + w / 4, y), (x + 3 * w / 4, y + h)]]

    @staticmethod
    def _stroke_pipe(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for pipe/vertical bar."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [[(x + w / 2, y), (x + w / 2, y + h)]]

    @staticmethod
    def _stroke_at(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for at sign."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Outer circle
        points_outer = []
        for i in range(15):
            angle = 2 * math.pi * i / 14
            px = x + w / 2 + w / 2 * math.cos(angle)
            py = y + h / 2 + h / 2 * math.sin(angle)
            points_outer.append((px, py))
        # Inner spiral
        points_inner = []
        for i in range(10):
            angle = 2 * math.pi * i / 9
            r = w / 6 + w / 6 * i / 9
            px = x + w / 2 + r * math.cos(angle)
            py = y + h / 2 + r * math.sin(angle)
            points_inner.append((px, py))
        return [points_outer, points_inner]

    @staticmethod
    def _stroke_hash(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for hash/pound sign."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            # Vertical 1
            [(x + w / 3, y + h / 6), (x + w / 3, y + 5 * h / 6)],
            # Vertical 2
            [(x + 2 * w / 3, y + h / 6), (x + 2 * w / 3, y + 5 * h / 6)],
            # Horizontal 1
            [(x + w / 6, y + h / 3), (x + 5 * w / 6, y + h / 3)],
            # Horizontal 2
            [(x + w / 6, y + 2 * h / 3), (x + 5 * w / 6, y + 2 * h / 3)],
        ]

    @staticmethod
    def _stroke_dollar(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for dollar sign."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        s_strokes = CharacterStrokes._stroke_S(x, y)
        return s_strokes + [
            # Vertical line through S
            [(x + w / 2, y - h / 8), (x + w / 2, y + 9 * h / 8)]
        ]

    @staticmethod
    def _stroke_percent(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for percent sign."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Small circles and diagonal
        return [
            # Top circle
            [
                (x + w / 4, y + h / 4),
                (x + w / 4 + 2, y + h / 4),
                (x + w / 4 + 2, y + h / 4 + 2),
                (x + w / 4, y + h / 4 + 2),
                (x + w / 4, y + h / 4),
            ],
            # Bottom circle
            [
                (x + 3 * w / 4, y + 3 * h / 4),
                (x + 3 * w / 4 + 2, y + 3 * h / 4),
                (x + 3 * w / 4 + 2, y + 3 * h / 4 + 2),
                (x + 3 * w / 4, y + 3 * h / 4 + 2),
                (x + 3 * w / 4, y + 3 * h / 4),
            ],
            # Diagonal
            [(x + w / 4, y + 3 * h / 4), (x + 3 * w / 4, y + h / 4)],
        ]

    @staticmethod
    def _stroke_caret(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for caret/circumflex."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        return [
            [(x + w / 4, y + h / 3), (x + w / 2, y + h / 6), (x + 3 * w / 4, y + h / 3)]
        ]

    @staticmethod
    def _stroke_ampersand(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for ampersand."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        # Complex curve for &
        points = []
        # Top circle
        for i in range(8):
            angle = -math.pi / 2 + math.pi * i / 7
            px = x + w / 2 + w / 4 * math.cos(angle)
            py = y + h / 4 + h / 4 * math.sin(angle)
            points.append((px, py))
        # Diagonal
        points.extend([(x + w / 4, y + h / 2), (x + 3 * w / 4, y + 3 * h / 4)])
        # Bottom curve
        points.extend(
            [
                (x + 3 * w / 4, y + 3 * h / 4),
                (x + w / 4, y + h),
                (x + 3 * w / 4, y + h / 2),
            ]
        )
        return [points]

    @staticmethod
    def _stroke_asterisk(x: float, y: float) -> List[List[Tuple[float, float]]]:
        """Strokes for asterisk."""
        w = CharacterStrokes.CHAR_WIDTH
        h = CharacterStrokes.CHAR_HEIGHT
        cx = x + w / 2
        cy = y + h / 3
        r = w / 4
        return [
            # Vertical
            [(cx, cy - r), (cx, cy + r)],
            # Horizontal
            [(cx - r, cy), (cx + r, cy)],
            # Diagonal 1
            [(cx - r * 0.7, cy - r * 0.7), (cx + r * 0.7, cy + r * 0.7)],
            # Diagonal 2
            [(cx + r * 0.7, cy - r * 0.7), (cx - r * 0.7, cy + r * 0.7)],
        ]
