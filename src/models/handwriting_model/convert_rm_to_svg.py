#!/usr/bin/env python3
"""
Convert a reMarkable .rm file to SVG for visualization.
This script attempts to extract strokes from a reMarkable .rm file
by skipping the header and parsing the binary data as best as possible.
"""

import os
import sys
import struct
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def extract_strokes_from_rm_file(file_path):
    """Extract strokes from a .rm file as best as possible."""
    strokes = []

    try:
        with open(file_path, "rb") as f:
            # Read header
            header = f.read(43)
            if header.startswith(b"reMarkable .lines file, version=5"):
                version = 5
            elif header.startswith(b"reMarkable .lines file, version=6"):
                version = 6
            else:
                print(f"Unknown file format: {header[:30]}")
                return []

            print(f"Detected version {version} file")

            # Skip rest of header if needed
            if version == 6:
                f.read(2)  # Extra bytes in v6 header

            # Attempt to read strokes
            while True:
                try:
                    # Try to read a chunk header - size may vary
                    chunk_header = f.read(4)
                    if not chunk_header or len(chunk_header) < 4:
                        break

                    # Skip some bytes that might contain pen info
                    f.read(4)

                    # Try different offsets to find point count
                    found_points = False

                    # These offsets are guesses and may not be correct for all files
                    for offset in [8, 12, 16, 20]:
                        f.seek(-4 - offset, 1)  # Go back to try a different offset
                        f.read(offset)  # Skip ahead to where point count might be

                        point_count_data = f.read(4)
                        if not point_count_data or len(point_count_data) < 4:
                            break

                        try:
                            point_count = struct.unpack("<I", point_count_data)[0]
                            if 0 < point_count < 10000:  # Reasonable range
                                found_points = True

                                # Skip some more bytes (might be stroke header)
                                f.read(12)

                                # Read points
                                points = []
                                for _ in range(point_count):
                                    point_data = f.read(16)
                                    if not point_data or len(point_data) < 16:
                                        break

                                    try:
                                        x, y, pressure, _ = struct.unpack(
                                            "<ffff", point_data
                                        )
                                        points.append((x, y, pressure))
                                    except Exception:
                                        pass

                                if points:
                                    strokes.append(points)

                                break  # Found points, move to next stroke
                        except Exception:
                            pass  # Try next offset

                    if not found_points:
                        # Skip ahead a bit to try to find next stroke
                        f.read(32)

                except Exception as e:
                    print(f"Error reading stroke: {e}")
                    # Skip ahead to try to recover
                    f.read(32)

            print(f"Found {len(strokes)} potential strokes")
            return strokes

    except Exception as e:
        print(f"Error processing file: {e}")
        return []


def strokes_to_svg(strokes, output_path, width=1404, height=1872):
    """Convert strokes to SVG."""
    # Create SVG root element
    svg = Element("svg")
    svg.set("width", str(width))
    svg.set("height", str(height))
    svg.set("xmlns", "http://www.w3.org/2000/svg")

    # Add white background
    background = SubElement(svg, "rect")
    background.set("width", "100%")
    background.set("height", "100%")
    background.set("fill", "white")

    # Add each stroke as a path
    for i, points in enumerate(strokes):
        if len(points) < 2:
            continue

        # Create a path for the stroke
        path = SubElement(svg, "path")

        # Generate path data
        d = f"M {points[0][0]} {points[0][1]}"
        for x, y, _ in points[1:]:
            d += f" L {x} {y}"

        path.set("d", d)
        path.set("stroke", "black")
        path.set("stroke-width", "2")
        path.set("fill", "none")

    # Write SVG to file
    with open(output_path, "w") as f:
        f.write(prettify(svg))

    print(f"SVG saved to {output_path}")
    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_rm_to_svg.py <path_to_rm_file>")
        return

    rm_file = sys.argv[1]
    if not os.path.exists(rm_file):
        print(f"Error: File {rm_file} does not exist")
        return

    # Generate output filename
    base_name = os.path.splitext(os.path.basename(rm_file))[0]
    output_dir = os.path.dirname(os.path.abspath(rm_file))
    svg_path = os.path.join(output_dir, f"{base_name}.svg")

    # Extract strokes and convert to SVG
    strokes = extract_strokes_from_rm_file(rm_file)
    if strokes:
        strokes_to_svg(strokes, svg_path)
    else:
        print("No strokes found to convert")


if __name__ == "__main__":
    main()
