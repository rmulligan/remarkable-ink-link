#!/usr/bin/env python3
"""
Demo script for the handwriting recognition model.

This script provides an interactive demo for testing the handwriting recognition model
using stroke data from reMarkable files or generated test data.
"""

import os
import json
import torch
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional
import argparse
import glob
from pathlib import Path
import sys

# Add parent directory to path for importing from preprocessing
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import custom modules
from model import RemarkableLSTM, CharacterPredictor
from preprocessing import extract_strokes_from_rm_file
from dataset import create_synthetic_dataset


def plot_stroke(stroke: Dict[str, List[float]], title: str = "Stroke"):
    """
    Plot a stroke.

    Args:
        stroke: Stroke dictionary with keys 'x', 'y', 'p'
        title: Plot title
    """
    plt.figure(figsize=(8, 6))

    # Plot stroke
    x = stroke["x"]
    y = stroke["y"]
    pressure = stroke["p"]

    # Normalize pressure to marker size
    s = [p * 100 for p in pressure]

    # Plot stroke trajectory
    plt.plot(x, y, "b-", alpha=0.3)

    # Plot points with pressure as size
    scatter = plt.scatter(x, y, c=range(len(x)), s=s, cmap="viridis", alpha=0.7)

    # Add colorbar to show point order
    cbar = plt.colorbar(scatter)
    cbar.set_label("Point Order")

    # Set title and labels
    plt.title(title)
    plt.xlabel("X")
    plt.ylabel("Y")

    # Set aspect ratio to be equal
    plt.axis("equal")

    # Add grid
    plt.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()


def demo_from_file(
    model_path: str,
    file_path: str,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
):
    """
    Demo using a file.

    Args:
        model_path: Path to model file
        file_path: Path to stroke file or .rm file
        device: Device to run inference on ('cuda' or 'cpu')
    """
    # Create predictor
    predictor = CharacterPredictor(model_path=model_path, device=device)

    # Load strokes
    if file_path.endswith(".rm") or file_path.endswith(".content"):
        # Extract strokes from .rm file
        strokes = extract_strokes_from_rm_file(file_path)
    else:
        # Load strokes from JSON file
        with open(file_path, "r") as f:
            strokes = json.load(f)

    # Check if it's a list of strokes or a single stroke
    if not isinstance(strokes, list):
        strokes = [strokes]

    # Process each stroke
    results = []
    for i, stroke in enumerate(strokes):
        # Plot stroke
        plot_stroke(stroke, title=f"Stroke {i + 1}")

        # Predict
        character, confidence = predictor.predict(stroke)
        results.append((character, confidence))

        # Print result
        print(f"Stroke {i + 1}: {character} (confidence: {confidence:.4f})")

    # Show all plots
    plt.show()

    # Print full text
    text = "".join([r[0] for r in results])
    print(f"Recognized text: {text}")


def demo_from_synthetic(
    model_path: str, device: str = "cuda" if torch.cuda.is_available() else "cpu"
):
    """
    Demo using synthetic data.

    Args:
        model_path: Path to model file
        device: Device to run inference on ('cuda' or 'cpu')
    """
    # Create predictor
    predictor = CharacterPredictor(model_path=model_path, device=device)

    # Create temporary directory for synthetic data
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create synthetic data
        create_synthetic_dataset(temp_dir, num_samples=10)

        # Get files
        files = glob.glob(os.path.join(temp_dir, "synthetic_*.json"))

        # Load labels
        with open(os.path.join(temp_dir, "labels.json"), "r") as f:
            labels = json.load(f)

        # Process each file
        for file_path in files:
            # Get stroke ID from filename
            stroke_id = os.path.splitext(os.path.basename(file_path))[0]

            # Get ground truth
            ground_truth = labels[stroke_id]

            # Load stroke
            with open(file_path, "r") as f:
                stroke = json.load(f)

            # Plot stroke
            plot_stroke(stroke, title=f"Stroke: {ground_truth}")

            # Predict
            character, confidence = predictor.predict(stroke)

            # Print result
            print(f"Ground truth: {ground_truth}")
            print(f"Prediction: {character} (confidence: {confidence:.4f})")
            print()

        # Show all plots
        plt.show()


def main():
    """Main function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Demo handwriting recognition model")

    # Input arguments
    parser.add_argument(
        "--model",
        type=str,
        default="checkpoints/best_model.pt",
        help="Path to model file",
    )
    parser.add_argument("--file", type=str, help="Path to stroke file or .rm file")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data")

    # Device arguments
    parser.add_argument("--cpu", action="store_true", help="Force CPU usage")

    # Parse arguments
    args = parser.parse_args()

    # Set device
    device = "cpu" if args.cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Check if model file exists
    if not os.path.exists(args.model):
        print(f"Model file not found: {args.model}")
        print("Using untrained model (predictions will be random)")
        args.model = None

    # Run demo
    if args.synthetic:
        demo_from_synthetic(args.model, device)
    elif args.file:
        demo_from_file(args.model, args.file, device)
    else:
        print("Please specify a file or use synthetic data")
        parser.print_help()


if __name__ == "__main__":
    main()
