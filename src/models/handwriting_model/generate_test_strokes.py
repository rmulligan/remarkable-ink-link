#!/usr/bin/env python3
"""
Utility script to generate test stroke data for handwriting recognition.

This script creates artificial stroke data that resembles handwritten characters
for testing the recognition model without requiring real .rm files.
"""

import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple, Optional

# Character templates (simplified stroke paths for common characters)
CHAR_TEMPLATES = {
    "a": [
        # First stroke - circular body
        [
            (10, 15),
            (8, 12),
            (10, 8),
            (15, 7),
            (18, 9),
            (20, 13),
            (18, 17),
            (15, 18),
            (12, 17),
        ],
        # Second stroke - vertical line on right
        [(18, 9), (20, 15), (19, 20)],
    ],
    "b": [
        # First stroke - vertical line
        [(10, 5), (10, 20)],
        # Second stroke - curved right side
        [(10, 10), (15, 8), (20, 10), (21, 15), (18, 18), (13, 18), (10, 16)],
    ],
    "c": [
        # Single stroke
        [(20, 10), (15, 8), (10, 10), (8, 15), (10, 20), (15, 22), (20, 20)]
    ],
    "d": [
        # First stroke - vertical line on right
        [(20, 5), (20, 20)],
        # Second stroke - curved left side
        [(20, 15), (18, 18), (15, 20), (10, 18), (8, 15), (10, 10), (15, 8), (20, 10)],
    ],
    "e": [
        # Single stroke
        [
            (20, 15),
            (15, 18),
            (10, 15),
            (8, 10),
            (10, 7),
            (15, 5),
            (20, 7),
            (8, 12),
            (20, 12),
        ]
    ],
    "f": [
        # First stroke - vertical line
        [(15, 5), (15, 20)],
        # Second stroke - horizontal top
        [(10, 10), (20, 10)],
        # Third stroke - horizontal middle
        [(10, 15), (18, 15)],
    ],
    "g": [
        # Single stroke - like 'c' with horizontal
        [
            (20, 10),
            (15, 8),
            (10, 10),
            (8, 15),
            (10, 20),
            (15, 22),
            (20, 20),
            (20, 25),
            (15, 28),
            (10, 25),
        ]
    ],
    "h": [
        # First stroke - left vertical
        [(10, 5), (10, 20)],
        # Second stroke - right vertical
        [(20, 5), (20, 20)],
        # Third stroke - horizontal middle
        [(10, 13), (20, 13)],
    ],
    "i": [
        # First stroke - vertical
        [(15, 10), (15, 20)],
        # Second stroke - dot
        [(15, 7), (15, 6)],
    ],
    "j": [
        # First stroke - vertical with curve
        [(15, 10), (15, 20), (12, 25), (8, 25)],
        # Second stroke - dot
        [(15, 7), (15, 6)],
    ],
    "k": [
        # First stroke - vertical
        [(10, 5), (10, 20)],
        # Second stroke - upper diagonal
        [(10, 13), (20, 5)],
        # Third stroke - lower diagonal
        [(10, 13), (20, 20)],
    ],
    "l": [
        # Single stroke
        [(15, 5), (15, 20)]
    ],
    "m": [
        # Single stroke
        [(10, 20), (10, 10), (13, 7), (15, 10), (17, 7), (20, 10), (20, 20)]
    ],
    "n": [
        # Single stroke
        [(10, 20), (10, 10), (15, 7), (20, 10), (20, 20)]
    ],
    "o": [
        # Single stroke - circle
        [
            (15, 8),
            (10, 10),
            (8, 15),
            (10, 20),
            (15, 22),
            (20, 20),
            (22, 15),
            (20, 10),
            (15, 8),
        ]
    ],
    "p": [
        # First stroke - vertical
        [(10, 10), (10, 25)],
        # Second stroke - curved right
        [(10, 10), (15, 8), (20, 10), (21, 15), (18, 18), (13, 18), (10, 16)],
    ],
    "q": [
        # First stroke - circle like 'o'
        [
            (15, 8),
            (10, 10),
            (8, 15),
            (10, 20),
            (15, 22),
            (20, 20),
            (22, 15),
            (20, 10),
            (15, 8),
        ],
        # Second stroke - tail
        [(18, 18), (20, 22), (22, 25)],
    ],
    "r": [
        # First stroke - vertical
        [(10, 10), (10, 20)],
        # Second stroke - curve
        [(10, 10), (13, 8), (18, 8), (20, 10)],
    ],
    "s": [
        # Single stroke
        [(20, 10), (15, 8), (10, 10), (12, 14), (18, 16), (20, 20), (15, 22), (10, 20)]
    ],
    "t": [
        # First stroke - vertical
        [(15, 8), (15, 20)],
        # Second stroke - horizontal
        [(10, 12), (20, 12)],
    ],
    "u": [
        # Single stroke
        [(10, 10), (10, 18), (15, 20), (20, 18), (20, 10)]
    ],
    "v": [
        # Single stroke
        [(10, 10), (15, 20), (20, 10)]
    ],
    "w": [
        # Single stroke
        [(10, 10), (12, 20), (15, 15), (18, 20), (20, 10)]
    ],
    "x": [
        # First stroke - forward diagonal
        [(10, 10), (20, 20)],
        # Second stroke - backward diagonal
        [(20, 10), (10, 20)],
    ],
    "y": [
        # Single stroke
        [(10, 10), (15, 15), (20, 10), (15, 25)]
    ],
    "z": [
        # Single stroke
        [(10, 10), (20, 10), (10, 20), (20, 20)]
    ],
    " ": [
        # Space - empty stroke
        []
    ],
    ".": [
        # Single dot
        [(15, 20), (16, 20)]
    ],
    ",": [
        # Single stroke
        [(15, 20), (14, 22)]
    ],
    "!": [
        # First stroke - vertical
        [(15, 10), (15, 18)],
        # Second stroke - dot
        [(15, 20), (15, 21)],
    ],
    "?": [
        # First stroke - question mark
        [(10, 10), (15, 8), (20, 10), (20, 13), (15, 15), (15, 18)],
        # Second stroke - dot
        [(15, 20), (15, 21)],
    ],
}


def add_noise_to_point(
    point: Tuple[float, float], noise_level: float = 0.5
) -> Tuple[float, float]:
    """
    Add random noise to a point to simulate natural handwriting variation

    Args:
        point: (x, y) coordinate
        noise_level: Amount of noise to add

    Returns:
        Noisy point
    """
    x, y = point
    x_noise = np.random.normal(0, noise_level)
    y_noise = np.random.normal(0, noise_level)
    return (x + x_noise, y + y_noise)


def generate_stroke_data(text: str, noise_level: float = 0.5) -> List[Dict[str, Any]]:
    """
    Generate artificial stroke data for the given text

    Args:
        text: Text to generate strokes for
        noise_level: Amount of noise to add (0 = no noise, 1 = high noise)

    Returns:
        List of stroke dictionaries
    """
    strokes = []

    # Start position for characters
    x_offset = 5
    y_offset = 15
    char_width = 25

    # Current timestamp (simulate realistic timing)
    timestamp = int(1000 * 1692300000)  # Base timestamp

    # Process each character
    for char in text.lower():
        # Skip if character template not available
        if char not in CHAR_TEMPLATES:
            x_offset += char_width // 2  # Add half space
            continue

        # Get character template
        char_strokes = CHAR_TEMPLATES[char]

        # Add each stroke in the character
        for stroke_points in char_strokes:
            if not stroke_points:  # Skip empty strokes (e.g., for space)
                continue

            # Add noise to stroke points
            noisy_points = [add_noise_to_point(p, noise_level) for p in stroke_points]

            # Extract x and y coordinates
            x_points = [p[0] + x_offset for p in noisy_points]
            y_points = [p[1] + y_offset for p in noisy_points]

            # Generate pressures (random but realistic)
            n_points = len(x_points)
            base_pressure = 0.6 + np.random.uniform(-0.1, 0.1)
            pressures = [
                min(1.0, max(0.3, base_pressure + np.random.normal(0, 0.05)))
                for _ in range(n_points)
            ]

            # Generate timestamps (continuous)
            # Each point takes 10-20ms
            point_times = [
                timestamp + i * (10 + np.random.randint(10)) for i in range(n_points)
            ]
            timestamp = point_times[-1] + 50  # Gap between strokes

            # Create stroke dictionary
            stroke = {
                "id": f"stroke_{len(strokes)}",
                "x": x_points,
                "y": y_points,
                "p": pressures,
                "t": point_times,
                "color": "#000000",
                "width": 2.0,
            }

            strokes.append(stroke)

        # Move to next character position
        x_offset += char_width

    return strokes


def visualize_strokes(strokes: List[Dict[str, Any]], output_path: Optional[str] = None):
    """
    Visualize the generated strokes

    Args:
        strokes: List of stroke dictionaries
        output_path: Path to save the visualization (if None, display instead)
    """
    plt.figure(figsize=(10, 6))

    # Draw each stroke
    for i, stroke in enumerate(strokes):
        x_points = stroke["x"]
        y_points = stroke["y"]

        # Plot the stroke with connection lines
        plt.plot(x_points, y_points, "b-", linewidth=2, alpha=0.7)

        # Plot the points
        pressures = stroke["p"]
        sizes = [20 * p for p in pressures]
        plt.scatter(x_points, y_points, c="black", s=sizes, alpha=0.5)

    # Set plot properties
    plt.title("Generated Handwriting Strokes")
    plt.xlabel("X coordinate")
    plt.ylabel("Y coordinate")
    plt.axis("equal")
    plt.grid(True, linestyle="--", alpha=0.7)

    # Save or display
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Visualization saved to {output_path}")
    else:
        plt.show()

    plt.close()


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Generate test stroke data for handwriting recognition"
    )
    parser.add_argument("text", help="Text to convert to strokes")
    parser.add_argument(
        "--output", "-o", default="test_strokes.json", help="Output JSON file path"
    )
    parser.add_argument(
        "--noise", "-n", type=float, default=0.5, help="Noise level (0-1)"
    )
    parser.add_argument(
        "--visualize", "-v", action="store_true", help="Visualize generated strokes"
    )

    # Parse arguments
    args = parser.parse_args()

    # Generate strokes
    strokes = generate_stroke_data(args.text, args.noise)

    # Save to JSON file
    with open(args.output, "w") as f:
        json.dump(strokes, f, indent=2)

    print(f"Generated {len(strokes)} strokes for text: '{args.text}'")
    print(f"Saved to {args.output}")

    # Visualize if requested
    if args.visualize:
        viz_path = os.path.splitext(args.output)[0] + ".png"
        visualize_strokes(strokes, viz_path)


if __name__ == "__main__":
    main()
