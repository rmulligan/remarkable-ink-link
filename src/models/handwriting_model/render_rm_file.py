#!/usr/bin/env python3
import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import rmscene


def load_rm_file(file_path):
    """Load a .rm file using rmscene and extract the strokes."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        # Check if the file starts with the expected header
        header = rmscene.HEADER_V6
        if not data.startswith(header):
            print(f"Warning: File does not start with expected V6 header.")
            print(f"Expected: {header}")
            print(f"Actual: {data[:len(header)]}")

        scene = rmscene.SceneTree.from_bytes(data)
        return scene
    except Exception as e:
        print(f"Error reading RM file: {e}")
        return None


def extract_strokes(scene):
    """Extract strokes from a scene tree."""
    strokes = []

    if not scene:
        return strokes

    for layer in scene.layers:
        for item in layer.items:
            if hasattr(item, "path") and item.path:
                stroke = {
                    "points": [
                        (p.x, p.y, p.pressure if hasattr(p, "pressure") else 1.0)
                        for p in item.path
                    ],
                    "width": (
                        item.brush_thickness
                        if hasattr(item, "brush_thickness")
                        else 2.0
                    ),
                    "color": (
                        item.color.as_tuple() if hasattr(item, "color") else (0, 0, 0)
                    ),
                }
                strokes.append(stroke)

    return strokes


def render_strokes(strokes, output_path, width=1404, height=1872, dpi=150):
    """Render strokes to an image file."""
    # Create a figure with the reMarkable dimensions
    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)  # Flip y-axis to match reMarkable coordinates
    ax.axis("off")

    for stroke in strokes:
        points = stroke["points"]
        if not points:
            continue

        # Extract x, y coordinates
        xs, ys, pressures = zip(*points)

        # Create path
        path_data = []
        path_data.append((Path.MOVETO, (xs[0], ys[0])))
        for x, y in zip(xs[1:], ys[1:]):
            path_data.append((Path.LINETO, (x, y)))

        path = Path(*zip(*path_data))

        # Create patch with path
        width = stroke.get("width", 2.0)
        color = stroke.get("color", (0, 0, 0))
        # Convert color to matplotlib format if needed
        if isinstance(color, tuple) and len(color) >= 3:
            color = tuple(c / 255 if c > 1 else c for c in color[:3])

        patch = PathPatch(path, fill=False, edgecolor=color, linewidth=width)
        ax.add_patch(patch)

    # Save the figure
    plt.savefig(output_path, bbox_inches="tight", pad_inches=0)
    plt.close()
    print(f"Rendered strokes to {output_path}")
    return output_path


def save_strokes_json(strokes, output_path):
    """Save strokes to a JSON file for debugging."""
    with open(output_path, "w") as f:
        json.dump(strokes, f, indent=2)
    print(f"Saved strokes data to {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python render_rm_file.py <path_to_rm_file>")
        return

    rm_file = sys.argv[1]
    if not os.path.exists(rm_file):
        print(f"Error: File {rm_file} does not exist.")
        return

    # Create output directory if it doesn't exist
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "rendered_pages"
    )
    os.makedirs(output_dir, exist_ok=True)

    # Generate output file paths
    base_name = os.path.splitext(os.path.basename(rm_file))[0]
    output_png = os.path.join(output_dir, f"{base_name}.png")
    output_json = os.path.join(output_dir, f"{base_name}.json")

    # Load the .rm file
    scene = load_rm_file(rm_file)

    if scene:
        # Extract and save strokes
        strokes = extract_strokes(scene)
        print(f"Extracted {len(strokes)} strokes from {rm_file}")

        # Save strokes as JSON for debugging
        save_strokes_json(strokes, output_json)

        # Render strokes to PNG
        render_strokes(strokes, output_png)
    else:
        print(f"Failed to load {rm_file}")


if __name__ == "__main__":
    main()
