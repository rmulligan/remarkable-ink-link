#!/usr/bin/env python3
import os
import sys
import json
import struct
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch

# reMarkable .rm file header
RM_HEADER = b'reMarkable .lines file, version=6          '

class Stroke:
    def __init__(self, points=None, width=2.0, color=(0, 0, 0)):
        self.points = points or []
        self.width = width
        self.color = color
    
    def add_point(self, x, y, pressure):
        self.points.append((x, y, pressure))
    
    def to_dict(self):
        return {
            'points': self.points,
            'width': self.width,
            'color': self.color
        }

def direct_extract_strokes(file_path):
    """Extract strokes directly from the binary format."""
    strokes = []
    current_stroke = None
    
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Check if this is a reMarkable file
    if not data.startswith(RM_HEADER):
        print(f"Warning: Not a reMarkable v6 file. Expected header not found.")
        return []
    
    # Look for stroke data pattern in the binary
    # The pattern for points in v6 is typically a sequence of 3 floats
    # representing x, y, and pressure
    
    # Skip the 43-byte header
    pos = len(RM_HEADER)
    
    while pos < len(data) - 24:  # Need at least 3 floats (12 bytes) + some header bytes
        # Look for sequences of point data
        # Each point is typically stored as 3 consecutive float32 values
        
        # Check for a possible stroke segment (looking for markers 0x18 which might indicate point data)
        if data[pos+2] == 0x18 and pos+14 < len(data):
            # Try to extract x, y, pressure values
            try:
                # In some variants, there's a single byte before each triple of floats
                x = struct.unpack("<f", data[pos+3:pos+7])[0]
                y = struct.unpack("<f", data[pos+7:pos+11])[0]
                pressure = struct.unpack("<f", data[pos+11:pos+15])[0]
                
                # Filter out unreasonable values that are likely not actual stroke data
                if -5000 < x < 5000 and -5000 < y < 5000 and 0 <= pressure <= 1.0:
                    # Start a new stroke if needed
                    if current_stroke is None:
                        current_stroke = Stroke()
                    
                    current_stroke.add_point(x, y, pressure)
                    
                    # Check for possible end of stroke (could be refined)
                    if pos+15 < len(data) and data[pos+15] == 0x00:
                        if current_stroke and current_stroke.points:
                            strokes.append(current_stroke.to_dict())
                            current_stroke = None
                
                # Move to the next point data
                pos += 15
                continue
            except Exception as e:
                # Not a valid float sequence, just continue
                pass
        
        # If we found a complete stroke, add it to our collection
        if current_stroke and len(current_stroke.points) > 0 and (
            pos >= len(data) - 24 or  # End of file
            (pos+3 < len(data) and data[pos+2] != 0x18)  # Pattern break
        ):
            strokes.append(current_stroke.to_dict())
            current_stroke = None
        
        pos += 1
    
    # Add the last stroke if there is one
    if current_stroke and current_stroke.points:
        strokes.append(current_stroke.to_dict())
    
    return strokes

def render_strokes(strokes, output_path, width=1404, height=1872, dpi=150):
    """Render strokes to an image file."""
    # Create a figure with the reMarkable dimensions
    fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)  # Flip y-axis to match reMarkable coordinates
    ax.axis('off')
    
    for stroke in strokes:
        points = stroke['points']
        if not points or len(points) < 2:
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
        width = stroke.get('width', 2.0)
        color = stroke.get('color', (0, 0, 0))
        # Convert color to matplotlib format if needed
        if isinstance(color, tuple) and len(color) >= 3:
            color = tuple(c/255 if c > 1 else c for c in color[:3])
            
        patch = PathPatch(path, fill=False, edgecolor=color, linewidth=width)
        ax.add_patch(patch)
    
    # Save the figure
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
    plt.close()
    print(f"Rendered strokes to {output_path}")
    return output_path

def save_strokes_json(strokes, output_path):
    """Save strokes to a JSON file for debugging."""
    with open(output_path, 'w') as f:
        json.dump(strokes, f, indent=2)
    print(f"Saved strokes data to {output_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python direct_stroke_extract.py <path_to_rm_file>")
        return
        
    rm_file = sys.argv[1]
    if not os.path.exists(rm_file):
        print(f"Error: File {rm_file} does not exist.")
        return
        
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendered_pages")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output file paths
    base_name = os.path.splitext(os.path.basename(rm_file))[0]
    output_png = os.path.join(output_dir, f"{base_name}_direct.png")
    output_json = os.path.join(output_dir, f"{base_name}_direct.json")
    
    # Extract strokes directly
    strokes = direct_extract_strokes(rm_file)
    print(f"Extracted {len(strokes)} strokes with {sum(len(s['points']) for s in strokes)} points from {rm_file}")
    
    # Save strokes as JSON for debugging
    save_strokes_json(strokes, output_json)
    
    # Render strokes to PNG
    render_strokes(strokes, output_png)

if __name__ == "__main__":
    main()