#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
import subprocess
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import cairosvg

def create_handwritten_style_pdf(text, output_path, font_path=None):
    """Create a PDF with handwritten style text."""
    # Register a handwritten-style font if provided, otherwise use a default
    font_name = "Handwritten"
    try:
        if font_path and os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        else:
            # Use a standard font with handwritten appearance
            font_name = "Helvetica"
    except Exception as e:
        print(f"Error loading font: {e}")
        font_name = "Helvetica"

    # Create PDF
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    # Set font properties
    font_size = 14
    line_height = font_size * 1.2
    left_margin = 72  # 1 inch in points
    top_margin = height - 72
    
    # Set text color to blue
    c.setFillColor(blue)
    
    # Add signature 
    c.setFont(font_name, font_size)
    
    # Split text into lines
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    max_length = 60  # Characters per line
    
    for word in words:
        if current_length + len(word) + 1 > max_length:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
        else:
            current_line.append(word)
            current_length += len(word) + 1
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Add signature line
    lines.append("")
    lines.append("- Claude")
    
    # Draw text
    y = top_margin
    for line in lines:
        c.drawString(left_margin, y, line)
        y -= line_height
    
    # Save the canvas
    c.save()
    return output_path

def convert_pdf_to_rm(pdf_path, output_rm_path=None):
    """Convert PDF to reMarkable format using rmc."""
    pdf_path = Path(pdf_path)
    
    if output_rm_path is None:
        output_rm_path = pdf_path.with_suffix('.rm')
    
    # First convert to SVG as intermediate format
    svg_path = pdf_path.with_suffix('.svg')
    
    try:
        # Convert PDF to SVG
        cairosvg.svg2pdf(
            url=str(pdf_path),
            write_to=str(svg_path)
        )
        
        # Use rmc to convert SVG to .rm format
        subprocess.run(
            ['rmc', '-f', 'pdf', '-t', 'rm', '-o', str(output_rm_path), str(pdf_path)],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Converted PDF to RM format at {output_rm_path}")
        return output_rm_path
    except Exception as e:
        print(f"Error converting PDF to RM: {e}")
        return None

def overlay_rm_files(original_rm, response_rm, output_rm):
    """Overlay two .rm files to create a combined notebook page."""
    # This would require a specialized library or tool to merge stroke data
    # For now, we'll just return the response RM file
    print("Note: True RM file overlay not implemented. Using response file only.")
    
    # Copy the response file to the output path
    import shutil
    shutil.copy2(response_rm, output_rm)
    return output_rm

def main():
    parser = argparse.ArgumentParser(description='Create a PDF with handwritten-style text and convert to reMarkable format')
    parser.add_argument('text', help='Text to write in the PDF')
    parser.add_argument('-o', '--output', help='Output path for the RM file')
    parser.add_argument('-f', '--font', help='Path to a handwritten-style TTF font')
    parser.add_argument('-r', '--original-rm', help='Original RM file to overlay response onto')
    
    args = parser.parse_args()
    
    # Create temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate PDF with handwritten text
        pdf_path = os.path.join(temp_dir, 'response.pdf')
        create_handwritten_style_pdf(args.text, pdf_path, args.font)
        print(f"Created PDF at {pdf_path}")
        
        # Convert to RM format
        response_rm = os.path.join(temp_dir, 'response.rm')
        converted_rm = convert_pdf_to_rm(pdf_path, response_rm)
        
        if not converted_rm:
            print("Failed to convert PDF to RM format")
            return 1
        
        output_rm = args.output if args.output else 'claude_response.rm'
        
        # If original RM file provided, attempt to overlay
        if args.original_rm and os.path.exists(args.original_rm):
            overlay_rm_files(args.original_rm, converted_rm, output_rm)
        else:
            # Just copy the converted RM file to the output path
            import shutil
            shutil.copy2(converted_rm, output_rm)
            print(f"Saved RM file to {output_rm}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())