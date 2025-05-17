#!/usr/bin/env python3
"""Script to extract text from the Claude Code integration plan PDF."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import after path manipulation to satisfy flake8
from src.inklink.adapters.pdf_adapter import PDFAdapter

# Initialize PDF adapter with temp directory
pdf_adapter = PDFAdapter("/tmp/inklink/pdf_extract")

# Path to the implementation plan PDF
pdf_path = "/home/ryan/dev/remarkable-ink-link/docs/Implementation Plan_ Integrating Claude Code into InkLink.pdf"

# Extract text from all pages
text_pages = pdf_adapter.extract_text(pdf_path)

# Output the extracted text
print("=== Claude Code Integration Plan ===\n")
for i, page_text in enumerate(text_pages, 1):
    print(f"--- Page {i} ---")
    print(page_text)
    print("\n")
