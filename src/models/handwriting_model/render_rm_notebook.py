#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
import subprocess
import cairosvg

def extract_rm_file(notebook_path, output_dir=None):
    """Extract .rm files from a downloaded notebook (.zip or .rmdoc)"""
    notebook_path = Path(notebook_path).absolute()
    
    if output_dir is None:
        output_dir = Path('downloads/extracted')
    else:
        output_dir = Path(output_dir)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if it's a .zip file (old format) or .rmdoc (new format)
    if notebook_path.suffix in ['.zip', '.rmdoc']:
        print(f"Extracting {notebook_path}...")
        # Extract the archive
        subprocess.run(
            ['unzip', '-o', str(notebook_path), '-d', str(output_dir)], 
            check=True,
            capture_output=True
        )
    else:
        print(f"Not a notebook archive: {notebook_path}")
        return None
    
    # Find .rm files in the extracted directory
    rm_files = list(output_dir.glob('**/*.rm'))
    print(f"Found {len(rm_files)} .rm files")
    return rm_files

def render_rm_file(rm_file_path, output_dir=None, width=1404, height=1872):
    """Render a .rm file to SVG and PNG using rmc"""
    rm_file_path = Path(rm_file_path).absolute()
    
    if output_dir is None:
        output_dir = Path('rendered_pages')
    else:
        output_dir = Path(output_dir)
    
    svg_dir = output_dir / 'svg'
    os.makedirs(svg_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output paths
    base_name = rm_file_path.stem
    svg_path = svg_dir / f"{base_name}.svg"
    png_path = output_dir / f"{base_name}.png"
    
    # Convert to SVG using rmc
    print(f"Converting {rm_file_path} to SVG...")
    subprocess.run(
        ['rmc', '-t', 'svg', '-o', str(svg_path), str(rm_file_path)],
        check=True,
        capture_output=True
    )
    
    # Convert SVG to PNG
    print(f"Rendering SVG to PNG...")
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(png_path),
        output_width=width,
        output_height=height
    )
    
    return {
        'svg': svg_path,
        'png': png_path
    }

def render_notebook(notebook_path, output_dir=None, width=1404, height=1872):
    """Render all pages in a notebook to PNG"""
    # Extract the notebook
    rm_files = extract_rm_file(notebook_path, output_dir)
    
    if not rm_files:
        print("No .rm files found in the notebook.")
        return []
    
    # Render each .rm file
    rendered_files = []
    for rm_file in rm_files:
        try:
            result = render_rm_file(rm_file, output_dir, width, height)
            rendered_files.append(result)
            print(f"Successfully rendered {rm_file}")
        except Exception as e:
            print(f"Error rendering {rm_file}: {e}")
    
    return rendered_files

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Render reMarkable notebooks to PNG images')
    parser.add_argument('notebook', help='Path to the .rmdoc or .zip notebook file')
    parser.add_argument('-o', '--output-dir', help='Output directory for rendered images')
    parser.add_argument('--width', type=int, default=1404, help='Output image width')
    parser.add_argument('--height', type=int, default=1872, help='Output image height')
    
    args = parser.parse_args()
    
    # Render the notebook
    rendered_files = render_notebook(
        args.notebook,
        args.output_dir,
        args.width,
        args.height
    )
    
    # Print results
    if rendered_files:
        print("\nRendered files:")
        for i, result in enumerate(rendered_files):
            print(f"Page {i+1}:")
            print(f"  SVG: {result['svg']}")
            print(f"  PNG: {result['png']}")
    else:
        print("No files were rendered.")

if __name__ == '__main__':
    main()