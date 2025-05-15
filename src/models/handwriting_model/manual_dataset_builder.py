#!/usr/bin/env python3
"""
Manual dataset builder for handwriting recognition.

This script provides a simpler approach to creating training datasets when you have:
1. reMarkable files (.rm) with handwriting
2. Text transcriptions of the handwriting

Instead of trying to automatically align strokes with transcriptions, this tool
allows you to manually specify which strokes correspond to which characters/words.
"""

import os
import sys
import json
import argparse
import tempfile
import subprocess
import logging
import numpy as np
import uuid
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add parent directory to path to import preprocessing utilities
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import preprocessing functions
from preprocessing import extract_strokes_from_rm_file, save_strokes_to_json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_strokes_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract strokes from a reMarkable file.
    
    Args:
        file_path: Path to the .rm file
        
    Returns:
        List of stroke dictionaries
    """
    try:
        # Extract strokes
        strokes = extract_strokes_from_rm_file(file_path)
        
        if not strokes:
            logger.warning(f"No strokes found in {file_path}")
            return []
            
        logger.info(f"Extracted {len(strokes)} strokes from {file_path}")
        return strokes
        
    except Exception as e:
        logger.error(f"Failed to extract strokes from {file_path}: {e}")
        return []


def visualize_strokes(strokes: List[Dict[str, Any]], labels: Optional[List[str]] = None) -> None:
    """
    Visualize strokes for inspection.
    
    Args:
        strokes: List of stroke dictionaries
        labels: Optional list of labels for each stroke
    """
    num_strokes = len(strokes)
    
    if num_strokes == 0:
        logger.warning("No strokes to visualize")
        return
    
    # Calculate grid dimensions
    cols = min(5, num_strokes)
    rows = (num_strokes + cols - 1) // cols
    
    # Create figure
    plt.figure(figsize=(cols*3, rows*3))
    
    # Plot each stroke
    for i, stroke in enumerate(strokes):
        plt.subplot(rows, cols, i+1)
        
        x = stroke['x']
        y = stroke['y']
        p = stroke['p']
        
        # Plot stroke line
        plt.plot(x, y, 'b-', alpha=0.3)
        
        # Plot points with pressure
        plt.scatter(x, y, c=range(len(x)), s=[p_val*100 for p_val in p], 
                   cmap='viridis', alpha=0.7)
        
        # Add label if provided
        title = f"Stroke {i+1}"
        if labels and i < len(labels):
            title += f": {labels[i]}"
        plt.title(title)
        
        plt.axis('equal')
        plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.show()


def create_character_dataset(strokes_file: str, transcription: str, 
                            output_dir: str) -> Dict[str, str]:
    """
    Create a character dataset from a reMarkable file and its transcription.
    
    Args:
        strokes_file: Path to the .rm file
        transcription: Text transcription
        output_dir: Directory to save extracted character strokes
        
    Returns:
        Dictionary mapping stroke IDs to character labels
    """
    # Extract strokes
    strokes = extract_strokes_from_file(strokes_file)
    if not strokes:
        return {}
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Display strokes for manual labeling
    logger.info("Displaying strokes for manual labeling...")
    visualize_strokes(strokes)
    
    # Manual labeling process
    labels = {}
    print(f"\nTranscription: {transcription}")
    print(f"Total strokes: {len(strokes)}")
    print("Enter character labels for each stroke (press Enter to skip, 'q' to quit):")
    
    for i, stroke in enumerate(strokes):
        label = input(f"Stroke {i+1}: ")
        
        if label.lower() == 'q':
            break
            
        if label:
            # Create ID for this stroke
            char = label[0]  # Take first character if multiple are entered
            stroke_id = f"char_{char}_{uuid.uuid4().hex[:8]}"
            
            # Save stroke
            stroke_with_id = dict(stroke)
            stroke_with_id["id"] = stroke_id
            
            stroke_file = os.path.join(output_dir, f"{stroke_id}.json")
            with open(stroke_file, 'w') as f:
                json.dump(stroke_with_id, f, indent=2)
            
            # Add to labels
            labels[stroke_id] = char
            logger.info(f"Saved stroke {i+1} as '{char}' to {stroke_file}")
    
    # Save labels
    labels_file = os.path.join(output_dir, "labels.json")
    with open(labels_file, 'w') as f:
        json.dump(labels, f, indent=2)
    
    logger.info(f"Saved {len(labels)} character labels to {labels_file}")
    return labels


def create_character_dataset_batch(strokes_file: str, transcription: str, 
                                 output_dir: str) -> Dict[str, str]:
    """
    Create a character dataset in batch mode, by entering all labels at once.
    
    Args:
        strokes_file: Path to the .rm file
        transcription: Text transcription
        output_dir: Directory to save extracted character strokes
        
    Returns:
        Dictionary mapping stroke IDs to character labels
    """
    # Extract strokes
    strokes = extract_strokes_from_file(strokes_file)
    if not strokes:
        return {}
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Display strokes for manual labeling
    logger.info("Displaying strokes for manual labeling...")
    visualize_strokes(strokes)
    
    # Manual labeling process
    labels = {}
    print(f"\nTranscription: {transcription}")
    print(f"Total strokes: {len(strokes)}")
    print("Enter a character label for each stroke, separated by spaces.")
    print("Use a . (period) to skip a stroke.")
    print("Example: a b c . e (labels 4 strokes, skips the 4th one)")
    
    label_string = input("Labels: ")
    char_labels = label_string.split()
    
    for i, stroke in enumerate(strokes):
        if i < len(char_labels) and char_labels[i] != '.':
            char = char_labels[i]
            
            # Create ID for this stroke
            stroke_id = f"char_{char}_{uuid.uuid4().hex[:8]}"
            
            # Save stroke
            stroke_with_id = dict(stroke)
            stroke_with_id["id"] = stroke_id
            
            stroke_file = os.path.join(output_dir, f"{stroke_id}.json")
            with open(stroke_file, 'w') as f:
                json.dump(stroke_with_id, f, indent=2)
            
            # Add to labels
            labels[stroke_id] = char
            logger.info(f"Saved stroke {i+1} as '{char}' to {stroke_file}")
    
    # Save labels
    labels_file = os.path.join(output_dir, "labels.json")
    with open(labels_file, 'w') as f:
        json.dump(labels, f, indent=2)
    
    logger.info(f"Saved {len(labels)} character labels to {labels_file}")
    return labels


def create_word_dataset(strokes_file: str, words: List[str], 
                      output_dir: str) -> Dict[str, str]:
    """
    Create a word dataset by manually grouping strokes into words.
    
    Args:
        strokes_file: Path to the .rm file
        words: List of words in the handwriting
        output_dir: Directory to save extracted word strokes
        
    Returns:
        Dictionary mapping stroke IDs to word labels
    """
    # Extract strokes
    strokes = extract_strokes_from_file(strokes_file)
    if not strokes:
        return {}
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Display strokes for grouping
    logger.info("Displaying strokes for manual grouping into words...")
    visualize_strokes(strokes)
    
    # Manual grouping process
    labels = {}
    print(f"\nWords: {words}")
    print(f"Total strokes: {len(strokes)}")
    print("For each word, enter the stroke indices that make up the word, separated by spaces.")
    print("Example: For the word 'hello', enter: 1 2 3 4 5")
    
    for word_idx, word in enumerate(words):
        indices_str = input(f"Word '{word}' (stroke indices): ")
        if not indices_str:
            continue
            
        try:
            # Parse stroke indices (1-based in input, convert to 0-based)
            indices = [int(idx) - 1 for idx in indices_str.split()]
            
            # Check if indices are valid
            if any(idx < 0 or idx >= len(strokes) for idx in indices):
                logger.error(f"Invalid stroke indices for word '{word}'")
                continue
            
            # Create word ID
            word_id = f"word_{word}_{uuid.uuid4().hex[:8]}"
            
            # Combine strokes for this word
            word_strokes = [strokes[idx] for idx in indices]
            
            # Sort strokes from left to right
            word_strokes.sort(key=lambda s: min(s['x']) if s['x'] else 0)
            
            # Combine points
            x_points = []
            y_points = []
            p_points = []
            
            for stroke in word_strokes:
                x_points.extend(stroke['x'])
                y_points.extend(stroke['y'])
                p_points.extend(stroke['p'])
            
            # Create combined stroke
            combined_stroke = {
                "id": word_id,
                "x": x_points,
                "y": y_points,
                "p": p_points
            }
            
            # Save word stroke
            stroke_file = os.path.join(output_dir, f"{word_id}.json")
            with open(stroke_file, 'w') as f:
                json.dump(combined_stroke, f, indent=2)
            
            # Add to labels
            labels[word_id] = word
            logger.info(f"Saved word '{word}' with {len(indices)} strokes to {stroke_file}")
            
        except ValueError:
            logger.error(f"Invalid input for word '{word}'")
    
    # Save labels
    labels_file = os.path.join(output_dir, "labels.json")
    with open(labels_file, 'w') as f:
        json.dump(labels, f, indent=2)
    
    logger.info(f"Saved {len(labels)} word labels to {labels_file}")
    return labels


def create_dataset_from_file(rm_file: str, text_file: str, output_dir: str, dataset_type: str) -> None:
    """
    Create a dataset from a reMarkable file and a text file.
    
    Args:
        rm_file: Path to the .rm file
        text_file: Path to the text file with transcription
        output_dir: Directory to save extracted strokes
        dataset_type: Type of dataset to create ("characters" or "words")
    """
    # Read transcription
    with open(text_file, 'r') as f:
        transcription = f.read().strip()
    
    # Create dataset based on type
    if dataset_type == "characters":
        create_character_dataset_batch(rm_file, transcription, output_dir)
    elif dataset_type == "words":
        words = transcription.split()
        create_word_dataset(rm_file, words, output_dir)
    else:
        logger.error(f"Unsupported dataset type: {dataset_type}")


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
            text=True
        )
        logger.info(f"Extracted notebook to {temp_dir}")
        
        # Find and load metadata
        metadata_files = list(Path(temp_dir).glob("*.metadata"))
        if not metadata_files:
            logger.error("No metadata file found in the notebook")
            return {}, temp_dir
            
        with open(metadata_files[0], 'r') as f:
            metadata = json.load(f)
            
        return metadata, temp_dir
        
    except Exception as e:
        logger.error(f"Failed to extract notebook: {e}")
        return {}, temp_dir


def process_notebook_with_transcriptions(notebook_path: str, transcriptions_file: str, 
                                       output_dir: str, dataset_type: str) -> None:
    """
    Process a reMarkable notebook using a transcriptions file.
    
    Args:
        notebook_path: Path to the .rmdoc file
        transcriptions_file: Path to a file with transcriptions for each page
        output_dir: Directory to save extracted strokes
        dataset_type: Type of dataset to create ("characters" or "words")
    """
    # Extract notebook content
    metadata, temp_dir = extract_notebook_content(notebook_path)
    if not metadata:
        logger.error("Failed to extract notebook metadata")
        return
    
    # Read transcriptions
    with open(transcriptions_file, 'r') as f:
        transcriptions = f.read().strip().split("\n---PAGE---\n")
    
    # Find all .rm files (pages)
    rm_files = sorted(list(Path(temp_dir).glob("*.rm")))
    if not rm_files:
        logger.error("No .rm files found in the notebook")
        return
    
    logger.info(f"Found {len(rm_files)} pages in the notebook")
    logger.info(f"Found {len(transcriptions)} transcriptions")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each page with its transcription
    for i, rm_file in enumerate(rm_files):
        if i < len(transcriptions):
            page_output_dir = os.path.join(output_dir, f"page_{i}")
            
            if dataset_type == "characters":
                create_character_dataset_batch(
                    str(rm_file),
                    transcriptions[i],
                    page_output_dir
                )
            elif dataset_type == "words":
                words = transcriptions[i].split()
                create_word_dataset(
                    str(rm_file),
                    words,
                    page_output_dir
                )
    
    # Combine all labels
    all_labels = {}
    for page_dir in os.listdir(output_dir):
        page_path = os.path.join(output_dir, page_dir)
        if os.path.isdir(page_path):
            labels_file = os.path.join(page_path, "labels.json")
            if os.path.exists(labels_file):
                with open(labels_file, 'r') as f:
                    page_labels = json.load(f)
                all_labels.update(page_labels)
    
    # Save combined labels
    combined_labels_file = os.path.join(output_dir, "labels.json")
    with open(combined_labels_file, 'w') as f:
        json.dump(all_labels, f, indent=2)
    
    logger.info(f"Saved combined labels with {len(all_labels)} entries to {combined_labels_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Manual dataset builder for handwriting recognition."
    )
    parser.add_argument("--rm-file", type=str, help="Path to the .rm file")
    parser.add_argument("--text-file", type=str, help="Path to the text file with transcription")
    parser.add_argument("--notebook", type=str, help="Path to the .rmdoc notebook file")
    parser.add_argument("--transcriptions", type=str, 
                       help="Path to file with transcriptions for notebook pages")
    parser.add_argument("--output-dir", type=str, default="data/manual",
                       help="Directory to save extracted strokes")
    parser.add_argument("--type", type=str, choices=["characters", "words"],
                       default="characters", help="Type of dataset to create")
    
    args = parser.parse_args()
    
    # Check input methods
    if args.rm_file and args.text_file:
        # Process single file
        create_dataset_from_file(args.rm_file, args.text_file, args.output_dir, args.type)
    elif args.notebook and args.transcriptions:
        # Process notebook with transcriptions
        process_notebook_with_transcriptions(
            args.notebook, 
            args.transcriptions, 
            args.output_dir, 
            args.type
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    import sys
    import matplotlib
    matplotlib.use('TkAgg')  # Use TkAgg backend for interactive plotting
    main()