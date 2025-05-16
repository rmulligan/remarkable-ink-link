#!/usr/bin/env python3
"""Very simple ink generation test."""

import os
import sys
import tempfile

import inklink.services.ink_generation_service as ink_mod

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Override the RMSCENE_AVAILABLE check for testing

ink_mod.RMSCENE_AVAILABLE = True

# Create service instance
service = ink_mod.InkGenerationService()

# Test creating strokes
try:
    # Simply test the stroke generation without file I/O
    strokes = service.text_to_strokes("Test")
    print(f"Generated {len(strokes)} strokes")

    for i, stroke in enumerate(strokes):
        print(f"  Stroke {i}: {len(stroke.points)} points")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
