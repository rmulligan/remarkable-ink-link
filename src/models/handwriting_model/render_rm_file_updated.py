#!/usr/bin/env python3
import os
import sys
import json
from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch
import rmscene
from rmscene.scene_tree import SceneTree


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

        # Use BytesIO to create a stream from the file data
        stream = BytesIO(data)
        # Read the tree structure
        scene_tree = rmscene.read_tree(stream)
        return scene_tree
    except Exception as e:
        print(f"Error reading RM file: {e}")
        import traceback

        traceback.print_exc()
        return None


def extract_strokes(scene_tree):
    """Extract strokes from a scene tree."""
    strokes = []

    if not scene_tree:
        return strokes

    # Dump structure for debugging
    print(f"Scene tree type: {type(scene_tree)}")
    print(f"Scene tree dir: {dir(scene_tree)}")

    try:
        # Find all line items in the scene tree
        for block in scene_tree.blocks:
            print(f"Block type: {type(block)}")

            # Look for SceneLineItemBlock objects
            if hasattr(block, "points") and block.points:
                points = [
                    (p.x, p.y, p.pressure if hasattr(p, "pressure") else 1.0)
                    for p in block.points
                ]

                stroke = {
                    "points": points,
                    "width": (
                        block.brush_thickness
                        if hasattr(block, "brush_thickness")
                        else 2.0
                    ),
                    "color": (0, 0, 0),  # Default color
                }
                strokes.append(stroke)
            elif hasattr(block, "items"):
                for item in block.items:
                    if hasattr(item, "points") and item.points:
                        points = [
                            (p.x, p.y, p.pressure if hasattr(p, "pressure") else 1.0)
                            for p in item.points
                        ]

                        stroke = {
                            "points": points,
                            "width": (
                                item.brush_thickness
                                if hasattr(item, "brush_thickness")
                                else 2.0
                            ),
                            "color": (0, 0, 0),  # Default color
                        }
                        strokes.append(stroke)
    except Exception as e:
        print(f"Error extracting strokes: {e}")
        import traceback

        traceback.print_exc()

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


def visualize_binary(file_path, output_path):
    """Create a binary visualization of the file as a grayscale image."""
    with open(file_path, "rb") as f:
        data = f.read()

    # Convert bytes to integers
    int_data = list(data)

    # Create a square-ish grid
    size = int(np.ceil(np.sqrt(len(int_data))))
    grid = np.zeros((size, size), dtype=np.uint8)

    # Fill the grid with data values
    for i, val in enumerate(int_data):
        if i < size * size:
            row = i // size
            col = i % size
            grid[row, col] = val

    # Create visualization
    plt.figure(figsize=(10, 10))
    plt.imshow(grid, cmap="gray", vmin=0, vmax=255)
    plt.title(f"Binary visualization of {os.path.basename(file_path)}")
    plt.colorbar(label="Byte value")
    plt.savefig(output_path)
    plt.close()
    print(f"Saved binary visualization to {output_path}")


def dump_header_info(file_path):
    """Dump the first 1024 bytes of the file in a readable format."""
    with open(file_path, "rb") as f:
        header_data = f.read(1024)

    # Print as hex
    print("Hex representation of first 1024 bytes:")
    for i in range(0, len(header_data), 16):
        chunk = header_data[i : i + 16]
        hex_str = " ".join(f"{b:02x}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        print(f"{i:04x}: {hex_str.ljust(48)} | {ascii_str}")

    # Try to interpret as text
    print("\nAttempting to interpret as UTF-8 text:")
    try:
        text = header_data.decode("utf-8", errors="replace")
        print(text)
    except Exception as e:
        print(f"Failed to decode as text: {e}")


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
    binary_viz = os.path.join(output_dir, f"{base_name}_binary_viz.png")

    # Dump header info
    dump_header_info(rm_file)

    # Create binary visualization
    visualize_binary(rm_file, binary_viz)

    # Load the .rm file
    scene_tree = load_rm_file(rm_file)

    if scene_tree:
        # Extract and save strokes
        strokes = extract_strokes(scene_tree)
        print(f"Extracted {len(strokes)} strokes from {rm_file}")

        # Save strokes as JSON for debugging
        save_strokes_json(strokes, output_json)

        # Render strokes to PNG
        render_strokes(strokes, output_png)
    else:
        print(f"Failed to load {rm_file}")


if __name__ == "__main__":
    main()
