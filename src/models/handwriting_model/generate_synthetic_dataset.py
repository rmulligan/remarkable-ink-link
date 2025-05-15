#!/usr/bin/env python3
"""
Generate synthetic stroke data for handwriting recognition testing.

This script creates a dataset of synthetic strokes resembling handwritten
characters, which can be used to test the handwriting recognition model
when real reMarkable data is not available.
"""

import os
import json
import random
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Import stroke saving utility
from preprocessing import save_strokes_to_json

# Set of characters to generate
CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def generate_stroke_for_char(char: str) -> Dict[str, List[float]]:
    """
    Generate a synthetic stroke for a specific character.

    Args:
        char: Character to generate stroke for

    Returns:
        Dictionary with stroke data (x, y, pressure)
    """
    # Base size of stroke
    base_size = 100

    # Center point
    center_x = base_size + random.randint(-10, 10)
    center_y = base_size + random.randint(-10, 10)

    # Number of points in the stroke
    num_points = random.randint(10, 30)

    # Generate stroke based on character
    if char in "il1|":
        # Vertical line
        x = [center_x + random.randint(-5, 5) for _ in range(num_points)]
        y = [
            center_y
            - base_size // 2
            + i * base_size // num_points
            + random.randint(-3, 3)
            for i in range(num_points)
        ]

    elif char in "oO0":
        # Circle
        t = np.linspace(0, 2 * np.pi, num_points)
        radius = base_size // 2 - random.randint(0, 10)
        x = [
            center_x + int(radius * np.cos(angle)) + random.randint(-2, 2)
            for angle in t
        ]
        y = [
            center_y + int(radius * np.sin(angle)) + random.randint(-2, 2)
            for angle in t
        ]

    elif char in "vwVW":
        # Zigzag
        x = []
        y = []
        zigs = 3 if char in "wW" else 2
        for i in range(zigs):
            t = np.linspace(0, 1, num_points // zigs)
            x_segment = [
                center_x
                - base_size // 2
                + base_size * i / zigs
                + base_size * t[j] / zigs
                + random.randint(-3, 3)
                for j in range(len(t))
            ]

            if i % 2 == 0:
                y_segment = [
                    center_y - base_size // 2 + base_size * t[j] + random.randint(-3, 3)
                    for j in range(len(t))
                ]
            else:
                y_segment = [
                    center_y + base_size // 2 - base_size * t[j] + random.randint(-3, 3)
                    for j in range(len(t))
                ]

            x.extend(x_segment)
            y.extend(y_segment)

    elif char in "cC(":
        # Half circle
        t = np.linspace(np.pi / 4, 7 * np.pi / 4, num_points)
        radius = base_size // 2 - random.randint(0, 10)
        x = [
            center_x + int(radius * np.cos(angle)) + random.randint(-2, 2)
            for angle in t
        ]
        y = [
            center_y + int(radius * np.sin(angle)) + random.randint(-2, 2)
            for angle in t
        ]

    elif char in "sS":
        # S-shape
        t = np.linspace(0, 2 * np.pi, num_points)
        x = [
            center_x + int((base_size // 2) * np.sin(angle)) + random.randint(-3, 3)
            for angle in t
        ]
        y = [
            center_y + int((base_size // 3) * np.sin(2 * angle)) + random.randint(-3, 3)
            for angle in t
        ]

    elif char in "mM":
        # M-shape
        x = []
        y = []
        for i in range(4):
            t = np.linspace(0, 1, num_points // 4)
            x_segment = [
                center_x
                - base_size // 2
                + base_size * i / 4
                + base_size * t[j] / 4
                + random.randint(-2, 2)
                for j in range(len(t))
            ]

            if i % 2 == 0:
                y_segment = [
                    center_y
                    + base_size // 2
                    - base_size * t[j] / 2
                    + random.randint(-2, 2)
                    for j in range(len(t))
                ]
            else:
                y_segment = [
                    center_y
                    - base_size // 2
                    + base_size * t[j] / 2
                    + random.randint(-2, 2)
                    for j in range(len(t))
                ]

            x.extend(x_segment)
            y.extend(y_segment)

    elif char in "7":
        # 7-shape
        x1 = np.linspace(
            center_x - base_size // 2, center_x + base_size // 2, num_points // 2
        )
        y1 = [center_y - base_size // 2 + random.randint(-2, 2) for _ in range(len(x1))]

        x2 = np.linspace(center_x + base_size // 2, center_x, num_points // 2)
        y2 = np.linspace(
            center_y - base_size // 2, center_y + base_size // 2, num_points // 2
        )

        x = list(x1) + list(x2)
        y = list(y1) + list(y2)

    else:
        # Random stroke for other characters
        # Start with random walk
        x = [center_x]
        y = [center_y]

        for _ in range(num_points - 1):
            last_x = x[-1]
            last_y = y[-1]

            x.append(last_x + random.randint(-10, 10))
            y.append(last_y + random.randint(-10, 10))

        # Normalize to keep within reasonable bounds
        min_x, max_x = min(x), max(x)
        min_y, max_y = min(y), max(y)

        width = max(max_x - min_x, 1)
        height = max(max_y - min_y, 1)

        x = [center_x - base_size // 2 + (xi - min_x) * base_size / width for xi in x]
        y = [center_y - base_size // 2 + (yi - min_y) * base_size / height for yi in y]

    # Generate pressure values that follow a natural pattern
    # Higher in the middle, lower at the beginning and end
    t = np.linspace(0, 1, len(x))
    pressure = [
        0.3 + 0.5 * np.sin(t[i] * np.pi) + random.uniform(-0.1, 0.1)
        for i in range(len(t))
    ]
    pressure = [max(0.1, min(0.9, p)) for p in pressure]  # Clip to reasonable range

    # Create stroke dictionary
    stroke = {
        "id": f"synthetic_{char}_{random.randint(1000, 9999)}",
        "x": [float(xi) for xi in x],
        "y": [float(yi) for yi in y],
        "p": pressure,
    }

    return stroke


def generate_dataset(output_dir: str, num_samples_per_char: int = 5) -> None:
    """
    Generate a synthetic dataset of character strokes.

    Args:
        output_dir: Directory to save the dataset
        num_samples_per_char: Number of samples to generate for each character
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Create a directory for visualizations
    viz_dir = os.path.join(output_dir, "visualizations")
    os.makedirs(viz_dir, exist_ok=True)

    # Track all strokes and labels
    all_strokes = []
    labels = {}

    # Generate strokes for each character
    for char in CHARS:
        print(f"Generating strokes for character: {char}")

        for i in range(num_samples_per_char):
            # Generate stroke
            stroke = generate_stroke_for_char(char)
            stroke_id = stroke["id"]

            # Save individual stroke
            stroke_file = os.path.join(output_dir, f"{stroke_id}.json")
            with open(stroke_file, "w") as f:
                json.dump(stroke, f, indent=2)

            # Add to collection
            all_strokes.append(stroke)
            labels[stroke_id] = char

            # Visualize first instance of each character
            if i == 0:
                plt.figure(figsize=(4, 4))
                plt.plot(stroke["x"], stroke["y"], "b-", alpha=0.5)
                plt.scatter(
                    stroke["x"],
                    stroke["y"],
                    c=stroke["p"],
                    s=50,
                    cmap="viridis",
                    alpha=0.7,
                )
                plt.title(f"Character: {char}")
                plt.axis("equal")
                plt.tight_layout()
                plt.savefig(os.path.join(viz_dir, f"char_{char}.png"))
                plt.close()

    # Save all strokes
    all_strokes_file = os.path.join(output_dir, "all_strokes.json")
    save_strokes_to_json(all_strokes, all_strokes_file)
    print(f"Saved {len(all_strokes)} strokes to {all_strokes_file}")

    # Save labels
    labels_file = os.path.join(output_dir, "labels.json")
    with open(labels_file, "w") as f:
        json.dump(labels, f, indent=2)
    print(f"Saved labels to {labels_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic stroke data")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/synthetic",
        help="Directory to save the dataset",
    )
    parser.add_argument(
        "--samples-per-char",
        type=int,
        default=5,
        help="Number of samples to generate for each character",
    )

    args = parser.parse_args()

    # Generate dataset
    generate_dataset(args.output_dir, args.samples_per_char)
