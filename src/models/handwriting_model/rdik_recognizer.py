#!/usr/bin/env python3
"""
RDIK Handwriting Recognizer

This module implements a handwriting recognition system using Google's
Recognizer for Digital Ink (RDIK) through MediaPipe, which provides
high-quality pre-trained models for online handwriting recognition.
"""

import os
import time
import json
import tempfile
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

# Import MediaPipe dependencies
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    # Check if the digital ink recognition module is available
    HAVE_DIGITAL_INK = hasattr(mp.tasks, "python") and hasattr(mp.tasks.python, "text")

    if HAVE_DIGITAL_INK:
        try:
            from mediapipe.tasks.python.text import handwriting_recognizer
            from mediapipe.tasks.python.text.handwriting_recognizer import (
                HandwritingRecognizer,
            )

            HAVE_DIGITAL_INK = True
        except (ImportError, AttributeError):
            HAVE_DIGITAL_INK = False
except ImportError:
    mp = None
    HAVE_DIGITAL_INK = False
    print("MediaPipe not available. Please install with 'pip install mediapipe'")

# Import our utility functions for stroke extraction
from preprocessing import (
    extract_strokes_from_rm_file,
    normalize_strokes,
    save_strokes_to_json,
)


class RDIKHandwritingRecognizer:
    """
    Handwriting recognition system using Google's RDIK pre-trained models.
    """

    # Language mapping for MediaPipe models
    LANGUAGE_MAPPING = {
        "en": "zh",  # English
        "en_US": "zh",  # English (US)
        "fr": "fr",  # French
        "de": "de",  # German
        "es": "es",  # Spanish
        "it": "it",  # Italian
        "ja": "ja",  # Japanese
        "ko": "ko",  # Korean
        "zh": "zh",  # Chinese
        "zh_CN": "zh",  # Chinese (Simplified)
        "zh_TW": "zh",  # Chinese (Traditional)
        "ru": "ru",  # Russian
    }

    def __init__(self, language: str = "en"):
        """
        Initialize the RDIK handwriting recognizer.

        Args:
            language: Language code for recognition (e.g., "en", "fr", "zh")
        """
        if not HAVE_DIGITAL_INK:
            raise ImportError("MediaPipe Digital Ink Recognition not available")

        # Map language to supported model code
        self.language = self._map_language(language)

        # Initialize the recognizer
        base_options = python.BaseOptions(model_asset_path=self._get_model_path())
        options = handwriting_recognizer.HandwritingRecognizerOptions(
            base_options=base_options
        )

        # Create the recognizer
        self.recognizer = HandwritingRecognizer.create_from_options(options)

        print(f"Initialized RDIK Handwriting Recognizer (language: {language})")

    def _map_language(self, language: str) -> str:
        """
        Map language code to supported model language.

        Args:
            language: Language code

        Returns:
            Mapped language code for RDIK
        """
        # Convert to lowercase and strip region
        lang_code = language.lower().split("_")[0]

        # Map to supported language or default to English
        return self.LANGUAGE_MAPPING.get(lang_code, "zh")

    def _get_model_path(self) -> str:
        """
        Get the path to the pre-trained model file.
        MediaPipe will download the model if it doesn't exist.

        Returns:
            Path to the model file
        """
        # MediaPipe will handle model download automatically
        return f"{self.language}.task"

    def convert_strokes_to_ink(
        self, strokes: List[Dict[str, Any]]
    ) -> handwriting_recognizer.HandwritingInk:
        """
        Convert reMarkable strokes to HandwritingInk format.

        Args:
            strokes: List of stroke dictionaries

        Returns:
            HandwritingInk object for recognition
        """
        # Create HandwritingInk object
        ink = handwriting_recognizer.HandwritingInk()

        # Add each stroke
        for stroke_dict in strokes:
            # Create a new stroke
            stroke = ink.strokes.add()

            # Add points to the stroke
            for i in range(len(stroke_dict["x"])):
                point = stroke.points.add()
                point.x = float(stroke_dict["x"][i])
                point.y = float(stroke_dict["y"][i])
                # Add timestamp if available, otherwise use index as placeholder
                point.timestamp_ms = (
                    int(stroke_dict["t"][i]) if "t" in stroke_dict else i * 10
                )

        return ink

    def recognize_strokes(
        self, strokes: List[Dict[str, Any]]
    ) -> Tuple[str, float, List[Dict[str, Any]]]:
        """
        Recognize text from stroke data.

        Args:
            strokes: List of stroke dictionaries

        Returns:
            Tuple of (recognized text, confidence score, candidate list)
        """
        if not strokes:
            return "", 0.0, []

        # Normalize strokes (scale to appropriate range for recognition)
        normalized_strokes = normalize_strokes(strokes)

        # Convert to HandwritingInk format
        ink = self.convert_strokes_to_ink(normalized_strokes)

        # Perform recognition
        recognition_result = self.recognizer.recognize(ink)

        # Get best result
        if recognition_result.candidates:
            best_candidate = recognition_result.candidates[0]
            text = best_candidate.text
            score = best_candidate.score

            # Build candidate list
            candidates = [
                {"text": c.text, "score": c.score}
                for c in recognition_result.candidates
            ]

            return text, score, candidates
        else:
            return "", 0.0, []

    def recognize_from_file(
        self, rm_file_path: str
    ) -> Tuple[str, float, List[Dict[str, Any]]]:
        """
        Recognize text directly from a reMarkable file.

        Args:
            rm_file_path: Path to .rm file

        Returns:
            Tuple of (recognized text, confidence score, candidates)
        """
        # Extract strokes
        strokes = extract_strokes_from_rm_file(rm_file_path)

        if not strokes:
            return "No strokes found", 0.0, []

        # Recognize text
        return self.recognize_strokes(strokes)


# Example usage
if __name__ == "__main__":
    import argparse

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Recognize handwriting using Google's RDIK"
    )
    parser.add_argument("input", help="Path to .rm file or JSON stroke file")
    parser.add_argument(
        "--language", default="en", help="Language code for recognition"
    )
    parser.add_argument("--output", help="Output path for recognized text")

    # Parse arguments
    args = parser.parse_args()

    # Check if MediaPipe is available
    if not HAVE_DIGITAL_INK:
        print("Error: MediaPipe Digital Ink Recognition not available")
        print("Please install with: pip install mediapipe")
        exit(1)

    try:
        # Initialize recognizer
        recognizer = RDIKHandwritingRecognizer(language=args.language)

        # Process input file
        if args.input.endswith(".json"):
            # Load strokes from JSON
            with open(args.input, "r") as f:
                strokes = json.load(f)

            # Recognize text
            text, confidence, candidates = recognizer.recognize_strokes(strokes)
        else:
            # Process .rm file
            text, confidence, candidates = recognizer.recognize_from_file(args.input)

        # Print results
        print(f"\nRecognized text: {text}")
        print(f"Confidence: {confidence:.4f}")

        # Show top 3 candidates if available
        if len(candidates) > 1:
            print("\nTop candidates:")
            for i, candidate in enumerate(candidates[:3]):
                print(
                    f"{i+1}. \"{candidate['text']}\" (score: {candidate['score']:.4f})"
                )

        # Save output if requested
        if args.output:
            with open(args.output, "w") as f:
                f.write(text)
            print(f"Saved recognized text to {args.output}")

    except Exception as e:
        print(f"Error: {e}")
        exit(1)
