#!/usr/bin/env python3
"""
Improved script for rendering reMarkable notebook pages to PNG files.
Supports v5 and v6 file formats.
"""

import os
import sys
import struct
import numpy as np
import matplotlib.pyplot as plt
import zipfile
import argparse
from pathlib import Path


def extract_notebook(notebook_path, output_dir=None):
    """Extract notebook contents to directory."""
    if output_dir is None:
        output_dir = Path("extracted")
    else:
        output_dir = Path(output_dir)

    os.makedirs(output_dir, exist_ok=True)

    # Open the notebook archive (either .rmdoc or .zip)
    with zipfile.ZipFile(notebook_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)

    # Find all .rm files
    rm_files = list(output_dir.glob("**/*.rm"))
    print(f"Extracted {len(rm_files)} .rm files to {output_dir}")

    return output_dir, rm_files


def read_rm_file(file_path):
    """Read a reMarkable .rm file and extract strokes."""
    with open(file_path, "rb") as f:
        # Read the header to determine version
        header = f.read(43)

        # Check version and parse accordingly
        if header.startswith(b"reMarkable .lines file, version=5"):
            return read_v5_rm_file(file_path)
        elif header.startswith(b"reMarkable .lines file, version=6"):
            return read_v6_rm_file(file_path)
        else:
            print(f"Unknown file format: {header[:30]}")
            return []


def read_v5_rm_file(file_path):
    """Read a version 5 .rm file."""
    strokes = []

    with open(file_path, "rb") as f:
        # Skip header
        header = f.read(43)

        # Parse strokes
        while True:
            try:
                # Read 4 bytes to see if there's more data
                chunk = f.read(4)
                if not chunk or len(chunk) < 4:
                    break

                # Read pen parameters
                # Skip 4 more bytes
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

                # Skip 16 bytes (unknown data)
                f.read(16)

                # Read points
                points = []
                for _ in range(point_count):
                    point_data = f.read(16)
                    if not point_data or len(point_data) < 16:
                        break

                    # x, y, pressure, etc.
                    try:
                        x, y, pressure, _ = struct.unpack("<ffff", point_data)
                        points.append((x, y, pressure))
                    except Exception as e:
                        print(f"Error unpacking point data: {e}")
                        break

                # Add stroke if it has points
                if points:
                    strokes.append(
                        {
                            "pen": 2,  # Default to fineliner
                            "color": (0, 0, 0),  # Default to black
                            "width": 2.0,
                            "points": points,
                        }
                    )

            except Exception as e:
                print(f"Error reading stroke: {e}")
                break

    return strokes


def read_v6_rm_file(file_path):
    """Read a version 6 .rm file using custom parser."""
    strokes = []

    try:
        # Use rmscene if available
        try:
            import rmscene
            from rmscene.scene_stream import read_tree
            from rmscene.scene_items import Line

            with open(file_path, "rb") as f:
                scene_tree = read_tree(f)

            # Extract strokes from scene tree
            for item_id, item in scene_tree.items.items():
                if isinstance(item, Line):
                    points = []
                    for point in item.points:
                        points.append((point.x, point.y, point.pressure))

                    # Get pen color
                    color = (0, 0, 0)  # Default black
                    if hasattr(item, "color"):
                        # Convert to RGB
                        color_str = str(item.color)
                        if color_str.startswith("Color("):
                            # Parse color components
                            color = (0, 0, 0)  # Simplified for now

                    # Get pen width
                    width = 2.0
                    if hasattr(item, "pen"):
                        width = float(item.pen.value)

                    strokes.append(
                        {
                            "pen": 2,  # Default to fineliner
                            "color": color,
                            "width": width,
                            "points": points,
                        }
                    )

            if strokes:
                print(f"Extracted {len(strokes)} strokes using rmscene")
                return strokes

        except (ImportError, Exception) as e:
            print(f"rmscene not available or failed: {e}, using manual parsing")

        # Fallback to manual parsing for v6
        with open(file_path, "rb") as f:
            # Skip header
            header = f.read(43)

            # Simplified parsing for v6 (not fully accurate but helps visualize)
            while True:
                try:
                    # Try to read next bytes
                    chunk = f.read(4)
                    if not chunk or len(chunk) < 4:
                        break

                    # Skip pen parameters
                    f.read(12)

                    # Try to read number of points
                    point_count_data = f.read(4)
                    if not point_count_data or len(point_count_data) < 4:
                        break

                    try:
                        point_count = struct.unpack("<I", point_count_data)[0]
                        if point_count > 10000:  # Sanity check
                            print(
                                f"Suspiciously large point count: {point_count}, skipping"
                            )
                            break

                        # Skip some bytes
                        f.read(12)

                        # Read points
                        points = []
                        for _ in range(point_count):
                            point_data = f.read(16)
                            if not point_data or len(point_data) < 16:
                                break

                            try:
                                x, y, pressure, _ = struct.unpack("<ffff", point_data)
                                points.append((x, y, pressure))
                            except Exception as e:
                                print(f"Error unpacking point data: {e}")
                                break

                        # Add stroke
                        if points:
                            strokes.append(
                                {
                                    "pen": 2,  # Default to fineliner
                                    "color": (0, 0, 0),  # Default to black
                                    "width": 2.0,
                                    "points": points,
                                }
                            )

                    except Exception as e:
                        print(f"Error reading point count: {e}")
                        # Try to recover by skipping ahead
                        f.read(100)

                except Exception as e:
                    print(f"Error in manual parsing: {e}")
                    break

    except Exception as e:
        print(f"Error opening or parsing file {file_path}: {e}")

    return strokes


def render_strokes(strokes, output_path, width=1872, height=1404, dpi=150):
    """Render strokes to a PNG image."""
    # Create figure with the reMarkable dimensions
    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)  # Flip y-axis to match reMarkable coordinates
    ax.axis("off")
    ax.set_facecolor("white")  # White background

    # For each stroke
    for stroke in strokes:
        if not stroke.get("points"):
            continue

        # Get points
        points = stroke["points"]
        if not points:
            continue

        xs, ys, pressures = zip(*points)

        # Get color and width
        color = stroke.get("color", (0, 0, 0))
        if isinstance(color, tuple) and len(color) >= 3:
            color = tuple(c / 255 if c > 1 else c for c in color[:3])
        width = stroke.get("width", 2.0) * 0.5  # Scale down for better rendering

        # Plot the stroke
        ax.plot(xs, ys, color=color, linewidth=width, solid_capstyle="round")

    # Save the figure
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0.1)
    plt.close()

    print(f"Rendered image saved to: {output_path}")
    return output_path


def render_notebook(notebook_path, output_dir=None):
    """Render all pages in a notebook."""
    # Set default output directory
    if output_dir is None:
        output_dir = Path("rendered_pages")
    else:
        output_dir = Path(output_dir)

    os.makedirs(output_dir, exist_ok=True)

    # Extract notebook
    try:
        extracted_dir, rm_files = extract_notebook(notebook_path)
    except Exception as e:
        print(f"Error extracting notebook: {e}")
        return []

    # Render each .rm file
    rendered_files = []
    for i, rm_file in enumerate(rm_files):
        try:
            # Read strokes
            strokes = read_rm_file(rm_file)

            if not strokes:
                print(f"No strokes found in {rm_file}")
                continue

            # Generate output filename
            page_num = i + 1
            output_path = output_dir / f"page_{page_num}_{rm_file.stem}.png"

            # Render strokes
            render_strokes(strokes, output_path)
            rendered_files.append(output_path)

        except Exception as e:
            print(f"Error rendering {rm_file}: {e}")

    return rendered_files


def main():
    parser = argparse.ArgumentParser(description="Render reMarkable notebook pages")
    parser.add_argument("notebook", help="Path to .rmdoc or .zip notebook file")
    parser.add_argument(
        "-o", "--output-dir", help="Output directory for rendered images"
    )

    args = parser.parse_args()

    # Render the notebook
    rendered_files = render_notebook(args.notebook, args.output_dir)

    # Print results
    if rendered_files:
        print(f"\nRendered {len(rendered_files)} pages:")
        for i, path in enumerate(rendered_files):
            print(f"Page {i+1}: {path}")
    else:
        print("No pages were rendered")


if __name__ == "__main__":
    main()
