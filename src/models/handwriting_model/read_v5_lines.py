#!/usr/bin/env python3
"""
Simple script to read and render reMarkable .lines format version 5 files.
"""

import os
import sys
import struct
import numpy as np
import matplotlib.pyplot as plt


def read_v5_file(file_path):
    """
    Read a reMarkable .lines format version 5 file.
    """
    with open(file_path, "rb") as f:
        # Read the header
        header = f.read(43)
        if not header.startswith(b"reMarkable .lines file, version=5"):
            print(f"Warning: File does not have expected version 5 header.")
            print(f"Header: {header}")

        # Read strokes
        strokes = []

        while True:
            # Try to read stroke information
            try:
                # Read 4 bytes to see if there's more data
                chunk = f.read(4)
                if not chunk or len(chunk) < 4:
                    break

                # Appears to be the layer number, pen type, etc
                # Skip 4 more bytes (unknown data)
                f.read(4)

                # Next 8 bytes are pen type and color
                pen_data = f.read(8)
                if not pen_data or len(pen_data) < 8:
                    break

                # Read point count
                point_count_data = f.read(4)
                if not point_count_data or len(point_count_data) < 4:
                    break

                point_count = struct.unpack("<I", point_count_data)[0]

                # Skip width, height, etc (16 bytes)
                f.read(16)

                # Read points
                points = []
                for _ in range(point_count):
                    point_data = f.read(16)
                    if not point_data or len(point_data) < 16:
                        break

                    # x, y, width, pressure, etc
                    try:
                        x, y, pressure, _ = struct.unpack("<ffff", point_data)
                        points.append((x, y, pressure))
                    except Exception as e:
                        print(f"Error unpacking point data: {e}")
                        break

                # Add the stroke
                if points:
                    strokes.append(
                        {
                            "pen": 1,  # Default to ballpoint
                            "color": (0, 0, 1.0),  # Default to blue
                            "width": 1.0,
                            "points": points,
                        }
                    )

                print(f"Read stroke with {len(points)} points")

            except Exception as e:
                print(f"Error reading stroke: {e}")
                break

    return strokes


def render_strokes(strokes, output_path, width=1872, height=1404, dpi=150):
    """
    Render strokes to an image file.
    """
    # Create a figure with the reMarkable dimensions
    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)  # Flip y-axis to match reMarkable coordinates
    ax.axis("off")
    ax.set_facecolor("white")  # White background

    # For each stroke
    for stroke in strokes:
        if not stroke["points"]:
            continue

        # Get points
        points = stroke["points"]
        xs, ys, pressures = zip(*points)

        # Simply plot the line
        color = stroke.get("color", (0, 0, 1.0))  # Default to blue
        width = stroke.get("width", 1.0)
        ax.plot(xs, ys, color=color, linewidth=width * 0.5, solid_capstyle="round")

    # Save the figure
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    print(f"Rendered {len(strokes)} strokes to {output_path}")

    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python read_v5_lines.py <path_to_rm_file>")
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

    # Read the v5 file
    strokes = read_v5_file(rm_file)
    print(f"Extracted {len(strokes)} strokes from {rm_file}")

    # Render strokes to PNG
    render_strokes(strokes, output_png)

    print(f"Output image saved to: {output_png}")


if __name__ == "__main__":
    main()
