#!/usr/bin/env python3
"""
Simple script to render reMarkable strokes from a .rm file.
Works with both version 5 and 6 files.
"""

import os
import sys
import struct
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap


def read_rm_file(file_path):
    """Read a reMarkable .rm file and extract strokes."""
    with open(file_path, "rb") as f:
        # Read the header
        header = f.read(43)
        version = None

        if header.startswith(b"reMarkable .lines file, version=5"):
            version = 5
        elif header.startswith(b"reMarkable .lines file, version=6"):
            version = 6
        else:
            print(f"Unknown file format: {header[:30]}")
            return []

        print(f"Detected version {version} file")

        # Skip the rest of the header if needed
        remaining_header = f.read(version == 5 and 0 or 2)

        strokes = []

        # Read layer header (this is a guess and may not be accurate)
        layer_header = f.read(4)

        # Start reading strokes
        while True:
            try:
                # Read stroke header
                stroke_header = f.read(4)
                if not stroke_header or len(stroke_header) < 4:
                    break

                # Try to parse stroke properties
                pen_info = f.read(12)  # pen type, color, etc.
                if not pen_info or len(pen_info) < 12:
                    break

                # Try to get number of points
                num_points_data = f.read(4)
                if not num_points_data or len(num_points_data) < 4:
                    break

                try:
                    num_points = struct.unpack("<I", num_points_data)[0]
                    if num_points > 100000:  # sanity check
                        print(
                            f"Unreasonably large number of points: {num_points}, skipping"
                        )
                        break
                except Exception as e:
                    print(f"Error reading point count: {e}")
                    break

                # Skip unknown data
                f.read(12)

                # Read points
                points = []
                for _ in range(num_points):
                    point_data = f.read(16)
                    if not point_data or len(point_data) < 16:
                        break

                    try:
                        x, y, pressure, _ = struct.unpack("<ffff", point_data)
                        points.append((x, y, pressure))
                    except Exception as e:
                        print(f"Error reading point: {e}")
                        break

                # Add stroke if we have points
                if points:
                    # Simple interpretation of pen type and color (not accurate)
                    pen_type = pen_info[0] if len(pen_info) > 0 else 0

                    # Simplified color mapping (just a guess)
                    colors = {
                        0: "black",
                        1: "grey",
                        2: "white",
                        3: "blue",
                        4: "red",
                    }
                    color = colors.get(pen_type % len(colors), "black")

                    strokes.append({"points": points, "color": color, "width": 2.0})

            except Exception as e:
                print(f"Error reading stroke: {e}")
                # Try to skip ahead and recover
                continue

    print(f"Extracted {len(strokes)} strokes")
    return strokes


def render_strokes(strokes, output_path, width=1404, height=1872, dpi=150):
    """Render strokes to an image."""
    # Create figure with reMarkable dimensions
    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)  # Flip y-axis to match reMarkable coordinates
    ax.axis("off")
    ax.set_facecolor("white")

    # For each stroke
    for i, stroke in enumerate(strokes):
        if not stroke.get("points"):
            continue

        # Get points
        points = stroke["points"]
        if len(points) < 2:
            continue

        # Create line segments
        segments = []
        for i in range(len(points) - 1):
            p1 = (points[i][0], points[i][1])
            p2 = (points[i + 1][0], points[i + 1][1])
            segments.append([p1, p2])

        # Get pressures for line width variation
        pressures = [p[2] for p in points[:-1]]

        # Create line collection with varying width based on pressure
        lc = LineCollection(
            segments,
            linewidths=np.array(pressures) * 5,  # Scale pressure to reasonable width
            color=stroke.get("color", "black"),
            capstyle="round",
            zorder=i,  # Ensure proper layering
        )

        ax.add_collection(lc)

    # Save the figure
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0.1)
    plt.close()

    print(f"Rendered image saved to: {output_path}")
    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_render.py <path_to_rm_file>")
        return

    rm_file = sys.argv[1]
    if not os.path.exists(rm_file):
        print(f"Error: File {rm_file} does not exist")
        return

    # Create output directory
    output_dir = os.path.dirname(os.path.abspath(rm_file))
    os.makedirs(output_dir, exist_ok=True)

    # Generate output filename
    base_name = os.path.splitext(os.path.basename(rm_file))[0]
    output_path = os.path.join(output_dir, f"{base_name}_rendered.png")

    # Read and render strokes
    strokes = read_rm_file(rm_file)
    if not strokes:
        print("No strokes found to render")
        return

    render_strokes(strokes, output_path)


if __name__ == "__main__":
    main()
