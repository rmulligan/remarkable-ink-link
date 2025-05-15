#!/usr/bin/env python3
"""
Integration module that connects our handwriting recognition system
with the stroke extraction from reMarkable files.

This allows for a complete pipeline from .rm file to recognized text.
"""

import os
import json
import argparse
import torch
from typing import List, Dict, Any, Tuple, Optional

# Import our modules
from model import HandwritingRecognitionSystem
from preprocessing import (
    extract_strokes_from_rm_file,
    normalize_strokes,
    save_strokes_to_json,
)


# Define a simplified adapter that doesn't rely on external dependencies
class SimpleHandwritingAdapter:
    """
    Simple adapter class that works without external dependencies.
    """

    def __init__(self):
        pass

    def extract_strokes_from_rm_file(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """
        Extract strokes from a reMarkable file (simplified version).
        """
        try:
            # Try direct extraction using our function
            return extract_strokes_from_rm_file(rm_file_path)
        except Exception as e:
            print(f"Error extracting strokes from {rm_file_path}: {e}")
            return []


class RemarkableHandwritingRecognizer:
    """
    Complete system for recognizing handwriting from reMarkable files.
    This class integrates the updated rmscene extraction with our model.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        """
        Initialize the recognizer.

        Args:
            model_path: Path to pretrained model (optional)
            device: Device to run inference on ('cuda' or 'cpu')
        """
        self.device = device

        # Initialize recognition system
        self.recognition_system = HandwritingRecognitionSystem(
            model_path=model_path, device=device
        )

        # Initialize simplified adapter
        self.adapter = SimpleHandwritingAdapter()

        print(f"Initialized RemarkableHandwritingRecognizer (device: {device})")
        if model_path:
            print(f"Using pretrained model: {model_path}")
        else:
            print("No pretrained model specified. Using default initialized model.")
            print("Note: A trained model is required for accurate recognition.")

    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """
        Extract strokes from a reMarkable file.

        Args:
            rm_file_path: Path to .rm file

        Returns:
            List of stroke dictionaries
        """
        try:
            # First try using our adapter's extraction method
            strokes = self.adapter.extract_strokes_from_rm_file(rm_file_path)

            if not strokes:
                # If that fails, use our direct implementation
                strokes = extract_strokes_from_rm_file(rm_file_path)

            return strokes

        except Exception as e:
            print(f"Error extracting strokes from {rm_file_path}: {e}")
            return []

    def recognize_from_file(
        self, rm_file_path: str
    ) -> Tuple[str, float, List[Dict[str, Any]]]:
        """
        Recognize text directly from a reMarkable file.

        Args:
            rm_file_path: Path to .rm file

        Returns:
            Tuple of (recognized text, confidence score, extracted strokes)
        """
        # Extract strokes
        strokes = self.extract_strokes(rm_file_path)

        if not strokes:
            return "No strokes found", 0.0, []

        # Recognize text
        text, confidence = self.recognition_system.recognize(strokes)

        return text, confidence, strokes

    def recognize_from_strokes(
        self, strokes: List[Dict[str, Any]]
    ) -> Tuple[str, float]:
        """
        Recognize text from already extracted strokes.

        Args:
            strokes: List of stroke dictionaries

        Returns:
            Tuple of (recognized text, confidence score)
        """
        # Recognize text
        text, confidence = self.recognition_system.recognize(strokes)

        return text, confidence


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Recognize handwriting from reMarkable files"
    )
    parser.add_argument("input", help="Path to .rm file or JSON stroke file")
    parser.add_argument("--model", help="Path to pretrained model")
    parser.add_argument(
        "--save-strokes", action="store_true", help="Save extracted strokes to JSON"
    )
    parser.add_argument("--output", help="Output path for recognized text")
    parser.add_argument("--cpu", action="store_true", help="Force CPU inference")

    # Parse arguments
    args = parser.parse_args()

    # Determine device
    device = "cpu" if args.cpu else ("cuda" if torch.cuda.is_available() else "cpu")

    # Initialize recognizer
    recognizer = RemarkableHandwritingRecognizer(model_path=args.model, device=device)

    # Check input type
    if args.input.endswith(".rm") or args.input.endswith(".content"):
        # Process .rm file
        text, confidence, strokes = recognizer.recognize_from_file(args.input)

        # Save strokes if requested
        if args.save_strokes and strokes:
            strokes_path = os.path.splitext(args.input)[0] + "_strokes.json"
            save_strokes_to_json(strokes, strokes_path)

    elif args.input.endswith(".json"):
        # Load strokes from JSON
        with open(args.input, "r") as f:
            strokes = json.load(f)

        # Recognize text
        text, confidence = recognizer.recognize_from_strokes(strokes)

    else:
        print(f"Unsupported input format: {args.input}")
        return

    # Print results
    print(f"\nRecognized text: {text}")
    print(f"Confidence: {confidence:.4f}")

    # Save output if requested
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Saved recognized text to {args.output}")


if __name__ == "__main__":
    main()
