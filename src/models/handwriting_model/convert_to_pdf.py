#!/usr/bin/env python3
import markdown
import pdfkit
import sys

def convert_md_to_pdf(md_file, pdf_file):
    with open(md_file, 'r') as f:
        md_content = f.read()
    
    # Convert markdown to HTML
    html = markdown.markdown(md_content)
    
    # Wrap with HTML structure for styling
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: sans-serif;
                margin: 40px;
                color: blue;
            }}
            h1 {{
                color: blue;
            }}
            p {{
                color: blue;
            }}
            em {{
                color: blue;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """
    
    # Convert HTML to PDF
    options = {
        'page-size': 'Letter',
        'margin-top': '10mm',
        'margin-right': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'encoding': 'UTF-8',
    }
    
    pdfkit.from_string(html_content, pdf_file, options=options)
    print(f"Converted {md_file} to {pdf_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_to_pdf.py input.md output.pdf")
        sys.exit(1)
    
    md_file = sys.argv[1]
    pdf_file = sys.argv[2]
    
    convert_md_to_pdf(md_file, pdf_file)