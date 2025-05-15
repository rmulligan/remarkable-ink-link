#!/usr/bin/env python3
import os
import sys
import argparse
import svgwrite
import xml.etree.ElementTree as ET
from pathlib import Path
import cairosvg
import random
import numpy as np


def add_response_to_svg(
    svg_path, response_text, output_svg_path=None, output_png_path=None, start_y=300
):
    """Add handwritten-style text to a reMarkable notebook SVG file."""
    if output_svg_path is None:
        output_svg_path = svg_path.with_suffix(".response.svg")

    if output_png_path is None:
        output_png_path = Path(str(output_svg_path).replace(".svg", ".png"))

    # Parse the original SVG
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Extract SVG dimensions
    width = float(root.attrib.get("width", 1404))
    height = float(root.attrib.get("height", 1872))
    # viewBox = root.attrib.get("viewBox", f"0 0 {width} {height}")  # Unused variable

    # Create new SVG with same dimensions
    # Find the main group element (usually with id="p1")
    main_group = None
    for group in root.findall(".//{http://www.w3.org/2000/svg}g"):
        if "id" in group.attrib and group.attrib["id"] == "p1":
            main_group = group
            break

    if not main_group:
        print("Warning: Could not find main group in SVG. Creating a new one.")
        main_group = ET.SubElement(
            root, "{http://www.w3.org/2000/svg}g", {"id": "claude_response"}
        )

    # Parameters for handwriting simulation
    line_height = 30
    char_spacing = 12
    left_margin = -150  # Adjust based on the SVG viewBox
    line_variation = 5  # Vertical variation for handwriting effect

    # Split response into lines (max 40 chars per line)
    words = response_text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        # If adding this word would exceed line length, start a new line
        if current_length + len(word) + 1 > 40:  # +1 for space
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word) + 1  # +1 for space

    if current_line:
        lines.append(" ".join(current_line))

    # Process each line and add to SVG
    y_position = start_y

    # Create a new group for Claude's response
    response_group = ET.SubElement(
        main_group, "{http://www.w3.org/2000/svg}g", {"id": "claude_response"}
    )

    # Add a signature line
    signature_text = "- Claude"
    signature_y = y_position + (len(lines) + 1) * line_height

    for i, line in enumerate(lines):
        x_position = left_margin

        # Add some randomness to the y position for a more natural look
        line_y = (
            y_position
            + i * line_height
            + random.uniform(-line_variation, line_variation)
        )

        # Create a polyline for each line of text
        points = []

        # Simulate handwriting with points
        for char in line:
            # Skip spaces, just advance x position
            if char == " ":
                x_position += char_spacing
                continue

            # Create a few points per character to simulate handwriting
            num_points = random.randint(3, 6)
            for j in range(num_points):
                x = x_position + j * (char_spacing / num_points) + random.uniform(-2, 2)
                y = line_y + random.uniform(-3, 3)
                points.append(f"{x},{y}")

            x_position += char_spacing

        # Create polyline element
        if points:
            polyline = ET.SubElement(
                response_group,
                "{http://www.w3.org/2000/svg}polyline",
                {
                    "style": "fill:none; stroke:rgb(0, 0, 150); stroke-width:1.147; opacity:1",
                    "stroke-linecap": "round",
                    "points": " ".join(points),
                },
            )

    # Add signature
    signature_points = []
    x_position = left_margin
    for char in signature_text:
        if char == " ":
            x_position += char_spacing
            continue

        num_points = random.randint(3, 6)
        for j in range(num_points):
            x = x_position + j * (char_spacing / num_points) + random.uniform(-2, 2)
            y = signature_y + random.uniform(-3, 3)
            signature_points.append(f"{x},{y}")

        x_position += char_spacing

    if signature_points:
        polyline = ET.SubElement(
            response_group,
            "{http://www.w3.org/2000/svg}polyline",
            {
                "style": "fill:none; stroke:rgb(0, 0, 150); stroke-width:1.147; opacity:1",
                "stroke-linecap": "round",
                "points": " ".join(signature_points),
            },
        )

    # Save the modified SVG
    tree.write(output_svg_path, encoding="utf-8", xml_declaration=True)
    print(f"Saved modified SVG to {output_svg_path}")

    # Convert to PNG if requested
    if output_png_path:
        cairosvg.svg2png(
            url=str(output_svg_path),
            write_to=str(output_png_path),
            output_width=1404,
            output_height=1872,
        )
        print(f"Converted SVG to PNG at {output_png_path}")

    return output_svg_path, output_png_path


def convert_to_rm(svg_path, output_rm_path=None):
    """Convert SVG back to reMarkable format using rmc."""
    svg_path = Path(svg_path)

    if output_rm_path is None:
        output_rm_path = svg_path.with_suffix(".rm")

    try:
        # Use rmc to convert SVG to .rm format
        import subprocess

        result = subprocess.run(
            ["rmc", "-f", "svg", "-t", "rm", "-o", str(output_rm_path), str(svg_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Converted SVG to RM format at {output_rm_path}")
        return output_rm_path
    except subprocess.CalledProcessError as e:
        print(f"Error converting SVG to RM: {e}")
        print(f"Command output: {e.output}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Add response text to a reMarkable notebook SVG file"
    )
    parser.add_argument("svg_path", help="Path to the SVG file")
    parser.add_argument("response", help="Response text to add")
    parser.add_argument("-o", "--output", help="Output path for the modified SVG")
    parser.add_argument("-p", "--png", help="Output path for PNG conversion")
    parser.add_argument("-r", "--rm", help="Output path for RM conversion")
    parser.add_argument(
        "-y",
        "--y-position",
        type=int,
        default=300,
        help="Y position to start response text",
    )

    args = parser.parse_args()

    svg_path = Path(args.svg_path)
    output_svg = args.output if args.output else svg_path.with_suffix(".response.svg")
    output_png = args.png if args.png else Path(str(output_svg).replace(".svg", ".png"))
    output_rm = args.rm if args.rm else Path(str(output_svg).replace(".svg", ".rm"))

    # Add response to SVG
    output_svg, output_png = add_response_to_svg(
        svg_path, args.response, output_svg, output_png, args.y_position
    )

    # Convert to RM format
    if args.rm:
        convert_to_rm(output_svg, output_rm)


if __name__ == "__main__":
    main()
