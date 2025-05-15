#!/usr/bin/env python3
"""
Process a reMarkable notebook with alternating handwritten pages and transcriptions.

This script extracts stroke data from handwritten pages and pairs them with
the transcriptions on the following pages to create a labeled dataset for
handwriting recognition training.
"""

import os
import json
import argparse
import tempfile
import subprocess
import logging
import numpy as np
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

# Add parent directory to path to import preprocessing utilities
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import preprocessing functions
from preprocessing import extract_strokes_from_rm_file, save_strokes_to_json

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_notebook_content(notebook_path: str) -> Tuple[Dict[str, Any], str]:
    """
    Extract the content from a reMarkable notebook.

    Args:
        notebook_path: Path to the .rmdoc file

    Returns:
        Tuple of (metadata dict, temp directory with extracted files)
    """
    logger.info(f"Extracting notebook: {notebook_path}")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="rm_training_")

    # Extract the .rmdoc file (which is a zip archive)
    try:
        subprocess.run(
            ["unzip", "-o", notebook_path, "-d", temp_dir],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Extracted notebook to {temp_dir}")

        # Find and load metadata
        metadata_files = list(Path(temp_dir).glob("*.metadata"))
        if not metadata_files:
            logger.error("No metadata file found in the notebook")
            return {}, temp_dir

        with open(metadata_files[0], "r") as f:
            metadata = json.load(f)

        return metadata, temp_dir

    except Exception as e:
        logger.error(f"Failed to extract notebook: {e}")
        return {}, temp_dir


def extract_strokes_from_page(page_file: str) -> List[Dict[str, Any]]:
    """
    Extract strokes from a single page .rm file.

    Args:
        page_file: Path to the .rm file

    Returns:
        List of stroke dictionaries
    """
    try:
        # Extract strokes using the preprocessing function
        strokes = extract_strokes_from_rm_file(page_file)

        if not strokes:
            logger.warning(f"No strokes found in {page_file}")
            return []

        logger.info(f"Extracted {len(strokes)} strokes from {page_file}")
        return strokes

    except Exception as e:
        logger.error(f"Failed to extract strokes from {page_file}: {e}")
        return []


def read_transcription_page(page_file: str) -> str:
    """
    Read the transcription from a text page.
    This is a placeholder - in a real implementation, you would need OCR or
    another method to extract text from the transcription page.

    Args:
        page_file: Path to the transcription page file

    Returns:
        Transcription text
    """
    # This is a placeholder - replace with actual text extraction
    # If the transcription pages have recognizable text, we might use:
    # 1. OCR on the PDF version of the page
    # 2. reMarkable's built-in text conversion (if accessible)
    # 3. Manual input of the transcriptions

    # For now, we'll just return a placeholder and log the page file
    logger.info(f"Need transcription for page: {page_file}")
    return ""


def segment_strokes_by_line(
    strokes: List[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """
    Group strokes by line, assuming strokes in the same line have similar y-coordinates.

    Args:
        strokes: List of stroke dictionaries

    Returns:
        List of lists of strokes, grouped by line
    """
    if not strokes:
        return []

    # Calculate the center y-coordinate for each stroke
    stroke_centers = []
    for stroke in strokes:
        y_values = stroke["y"]
        center_y = sum(y_values) / len(y_values) if y_values else 0
        stroke_centers.append((stroke, center_y))

    # Sort strokes by center y-coordinate
    stroke_centers.sort(key=lambda x: x[1])

    # Group strokes by line (using a threshold for y-coordinate difference)
    y_threshold = 50  # Adjust based on your handwriting
    lines = []
    current_line = [stroke_centers[0][0]]
    current_y = stroke_centers[0][1]

    for stroke, center_y in stroke_centers[1:]:
        if abs(center_y - current_y) > y_threshold:
            # New line
            lines.append(current_line)
            current_line = [stroke]
            current_y = center_y
        else:
            # Same line
            current_line.append(stroke)

    # Add the last line
    if current_line:
        lines.append(current_line)

    # Sort strokes within each line by x-coordinate
    for i, line in enumerate(lines):
        # Calculate the leftmost x-coordinate for each stroke
        line_with_x = [
            (stroke, min(stroke["x"]) if stroke["x"] else 0) for stroke in line
        ]
        line_with_x.sort(key=lambda x: x[1])  # Sort by x-coordinate
        lines[i] = [stroke for stroke, _ in line_with_x]  # Replace with sorted line

    return lines


def segment_strokes_by_word(
    line_strokes: List[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """
    Group strokes by word, assuming spaces between words have larger x-gaps than
    spaces between characters within words.

    Args:
        line_strokes: List of stroke dictionaries for a single line

    Returns:
        List of lists of strokes, grouped by word
    """
    if not line_strokes:
        return []

    # Calculate the rightmost x-coordinate of each stroke and the leftmost of the next
    spaces = []
    sorted_strokes = sorted(line_strokes, key=lambda s: min(s["x"]) if s["x"] else 0)

    for i in range(len(sorted_strokes) - 1):
        curr_stroke = sorted_strokes[i]
        next_stroke = sorted_strokes[i + 1]

        curr_right = max(curr_stroke["x"]) if curr_stroke["x"] else 0
        next_left = min(next_stroke["x"]) if next_stroke["x"] else 0

        spaces.append((i, next_left - curr_right))

    # If no spaces, return the line as a single word
    if not spaces:
        return [line_strokes]

    # Sort spaces by width (descending)
    spaces.sort(key=lambda x: x[1], reverse=True)

    # Take the largest 30% of spaces as word boundaries
    num_word_spaces = max(1, int(len(spaces) * 0.3))
    word_spaces = set(idx for idx, _ in spaces[:num_word_spaces])

    # Group strokes by word
    words = []
    current_word = [sorted_strokes[0]]

    for i in range(len(sorted_strokes) - 1):
        if i in word_spaces:
            # End of word
            words.append(current_word)
            current_word = [sorted_strokes[i + 1]]
        else:
            # Same word
            current_word.append(sorted_strokes[i + 1])

    # Add the last word
    if current_word:
        words.append(current_word)

    return words


def process_handwriting_page(
    page_file: str,
    transcription: str,
    output_dir: str,
    dataset_type: str = "characters",
) -> Tuple[List[str], Dict[str, str]]:
    """
    Process a handwriting page and its transcription to create labeled stroke data.

    Args:
        page_file: Path to the handwriting page file
        transcription: Text transcription of the handwriting
        output_dir: Directory to save extracted strokes
        dataset_type: Type of dataset to create ("characters", "words", or "lines")

    Returns:
        Tuple of (list of created stroke file paths, label dictionary)
    """
    # Extract strokes from the page
    strokes = extract_strokes_from_page(page_file)
    if not strokes:
        return [], {}

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Create mapping for labels
    labels = {}
    stroke_files = []

    # Process based on dataset type
    if dataset_type == "characters":
        # Process character by character
        # This requires alignment between strokes and transcription characters

        # Group strokes by line
        lines = segment_strokes_by_line(strokes)

        # Process each line
        transcription_index = 0
        for line_idx, line in enumerate(lines):
            # Group by word to handle spacing
            words = segment_strokes_by_word(line)

            # Process each word
            for word_idx, word in enumerate(words):
                # Sort strokes from left to right
                word.sort(key=lambda s: min(s["x"]) if s["x"] else 0)

                # Try to assign characters from transcription to strokes
                for stroke_idx, stroke in enumerate(word):
                    if transcription_index < len(transcription):
                        char = transcription[transcription_index]

                        # Skip whitespace in transcription
                        while char.isspace() and transcription_index + 1 < len(
                            transcription
                        ):
                            transcription_index += 1
                            char = transcription[transcription_index]

                        if not char.isspace():
                            # Create an ID for this stroke
                            stroke_id = f"char_{char}_{uuid.uuid4().hex[:8]}"

                            # Save stroke
                            stroke_file = os.path.join(output_dir, f"{stroke_id}.json")

                            # Update stroke ID
                            stroke_with_id = dict(stroke)
                            stroke_with_id["id"] = stroke_id

                            # Save stroke to file
                            with open(stroke_file, "w") as f:
                                json.dump(stroke_with_id, f, indent=2)

                            # Add to labels
                            labels[stroke_id] = char
                            stroke_files.append(stroke_file)

                            # Move to next character
                            transcription_index += 1

    elif dataset_type == "words":
        # Process word by word
        # Group strokes by line
        lines = segment_strokes_by_line(strokes)

        # Split transcription into words
        transcription_words = transcription.split()
        word_index = 0

        # Process each line
        for line_idx, line in enumerate(lines):
            # Group by word
            words = segment_strokes_by_word(line)

            # Process each word
            for word_idx, word_strokes in enumerate(words):
                if word_index < len(transcription_words):
                    word_text = transcription_words[word_index]

                    # Create an ID for this word
                    word_id = f"word_{word_text}_{uuid.uuid4().hex[:8]}"

                    # Combine all strokes for this word
                    x_points = []
                    y_points = []
                    p_points = []

                    # Sort strokes from left to right
                    word_strokes.sort(key=lambda s: min(s["x"]) if s["x"] else 0)

                    for stroke in word_strokes:
                        x_points.extend(stroke["x"])
                        y_points.extend(stroke["y"])
                        p_points.extend(stroke["p"])

                    # Create combined stroke
                    combined_stroke = {
                        "id": word_id,
                        "x": x_points,
                        "y": y_points,
                        "p": p_points,
                    }

                    # Save combined stroke
                    stroke_file = os.path.join(output_dir, f"{word_id}.json")
                    with open(stroke_file, "w") as f:
                        json.dump(combined_stroke, f, indent=2)

                    # Add to labels
                    labels[word_id] = word_text
                    stroke_files.append(stroke_file)

                    # Move to next word
                    word_index += 1

    elif dataset_type == "lines":
        # Process line by line
        # Group strokes by line
        lines = segment_strokes_by_line(strokes)

        # Split transcription into lines
        transcription_lines = transcription.strip().split("\n")

        # Process each line
        for line_idx, line_strokes in enumerate(lines):
            if line_idx < len(transcription_lines):
                line_text = transcription_lines[line_idx]

                # Create an ID for this line
                line_id = f"line_{line_idx}_{uuid.uuid4().hex[:8]}"

                # Combine all strokes for this line
                x_points = []
                y_points = []
                p_points = []

                # Sort strokes from left to right
                line_strokes.sort(key=lambda s: min(s["x"]) if s["x"] else 0)

                for stroke in line_strokes:
                    x_points.extend(stroke["x"])
                    y_points.extend(stroke["y"])
                    p_points.extend(stroke["p"])

                # Create combined stroke
                combined_stroke = {
                    "id": line_id,
                    "x": x_points,
                    "y": y_points,
                    "p": p_points,
                }

                # Save combined stroke
                stroke_file = os.path.join(output_dir, f"{line_id}.json")
                with open(stroke_file, "w") as f:
                    json.dump(combined_stroke, f, indent=2)

                # Add to labels
                labels[line_id] = line_text
                stroke_files.append(stroke_file)

    return stroke_files, labels


def process_notebook(
    notebook_path: str,
    output_dir: str,
    dataset_type: str = "characters",
    transcriptions: Optional[Dict[int, str]] = None,
) -> None:
    """
    Process a reMarkable notebook with alternating handwritten pages and transcription pages.

    Args:
        notebook_path: Path to the .rmdoc file
        output_dir: Directory to save extracted strokes
        dataset_type: Type of dataset to create ("characters", "words", or "lines")
        transcriptions: Optional dictionary mapping page numbers to transcriptions
                       If provided, skips the transcription page processing
    """
    # Extract notebook content
    metadata, temp_dir = extract_notebook_content(notebook_path)
    if not metadata:
        logger.error("Failed to extract notebook metadata")
        return

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Find all .rm files (pages)
    rm_files = sorted(list(Path(temp_dir).glob("*.rm")))
    if not rm_files:
        logger.error("No .rm files found in the notebook")
        return

    logger.info(f"Found {len(rm_files)} pages in the notebook")

    # Create a labels dictionary
    all_labels = {}
    all_stroke_files = []

    # Process pages
    for i in range(0, len(rm_files), 2):
        if i + 1 < len(rm_files):
            # Handwritten page (even index)
            handwriting_page = str(rm_files[i])
            logger.info(f"Processing handwriting page: {handwriting_page}")

            # Get transcription
            if transcriptions and i // 2 in transcriptions:
                # Use provided transcription
                transcription = transcriptions[i // 2]
                logger.info(f"Using provided transcription for page {i//2}")
            else:
                # Try to read from the next page
                transcription_page = str(rm_files[i + 1])
                transcription = read_transcription_page(transcription_page)
                logger.info(f"Read transcription from page: {transcription_page}")

            # Process this handwriting page and its transcription
            page_output_dir = os.path.join(output_dir, f"page_{i//2}")
            stroke_files, labels = process_handwriting_page(
                handwriting_page, transcription, page_output_dir, dataset_type
            )

            # Update the global collections
            all_labels.update(labels)
            all_stroke_files.extend(stroke_files)

    # Save labels
    labels_file = os.path.join(output_dir, "labels.json")
    with open(labels_file, "w") as f:
        json.dump(all_labels, f, indent=2)

    logger.info(f"Processed notebook with {len(all_stroke_files)} strokes")
    logger.info(f"Labels saved to {labels_file}")


def process_transcriptions_file(file_path: str) -> Dict[int, str]:
    """
    Process a file containing transcriptions for each page.

    Args:
        file_path: Path to the transcription file

    Returns:
        Dictionary mapping page numbers to transcriptions
    """
    transcriptions = {}

    with open(file_path, "r") as f:
        content = f.read()

    # Split by page markers (adjust based on your file format)
    pages = content.split("---PAGE---")

    for i, page in enumerate(pages):
        transcriptions[i] = page.strip()

    return transcriptions


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Process a reMarkable notebook with alternating handwritten and transcription pages."
    )
    parser.add_argument("notebook_path", type=str, help="Path to the .rmdoc file")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/remarkable",
        help="Directory to save extracted strokes",
    )
    parser.add_argument(
        "--dataset-type",
        type=str,
        choices=["characters", "words", "lines"],
        default="characters",
        help="Type of dataset to create",
    )
    parser.add_argument(
        "--transcriptions-file",
        type=str,
        help="Optional file containing transcriptions for each page",
    )

    args = parser.parse_args()

    # Load transcriptions from file if provided
    transcriptions = None
    if args.transcriptions_file:
        transcriptions = process_transcriptions_file(args.transcriptions_file)

    # Process notebook
    process_notebook(
        args.notebook_path, args.output_dir, args.dataset_type, transcriptions
    )


if __name__ == "__main__":
    import sys

    main()
