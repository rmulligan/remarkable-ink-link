#!/usr/bin/env python3
"""Extract text from Claude Code Integration Implementation Plan PDF"""

import os
import sys

from inklink.adapters.pdf_adapter import PDFAdapter

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import after path manipulation to satisfy flake8


def main():
    # Path to the PDF file
    pdf_path = "/home/ryan/dev/remarkable-ink-link/docs/Implementation Plan_ Integrating Claude Code into InkLink.pdf"

    # Create PDFAdapter instance
    pdf_adapter = PDFAdapter()

    try:
        # Extract text from PDF
        extracted_text = pdf_adapter.extract_text(pdf_path)

        # Print the extracted text
        print("=== Implementation Plan: Integrating Claude Code into InkLink ===")
        print()
        print(extracted_text)

    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
