"""
Dataset module for handwriting recognition training.

This module handles creating datasets from reMarkable strokes and ground truth text.
It includes tools for extracting strokes, preprocessing, and creating PyTorch datasets.
"""

import os
import json
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Tuple, Optional, Union
import random
from pathlib import Path

# Import the stroke extraction functionality
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from preprocessing import extract_strokes_from_rm_file


class StrokeDataset(Dataset):
    """
    Dataset of handwriting strokes and their corresponding characters.
    """
    
    def __init__(
        self,
        strokes: List[Dict[str, List[float]]],
        labels: List[int],
        transform=None,
        max_length: int = 100
    ):
        """
        Initialize the dataset.
        
        Args:
            strokes: List of stroke dictionaries
            labels: List of character labels (as indices)
            transform: Optional transform to apply to the data
            max_length: Maximum sequence length for padding/truncation
        """
        self.strokes = strokes
        self.labels = labels
        self.transform = transform
        self.max_length = max_length
    
    def __len__(self) -> int:
        """
        Get the number of samples in the dataset.
        
        Returns:
            Number of samples
        """
        return len(self.strokes)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """
        Get a sample from the dataset.
        
        Args:
            idx: Index of the sample
            
        Returns:
            Tuple of (features, label)
        """
        # Get stroke and label
        stroke = self.strokes[idx]
        label = self.labels[idx]
        
        # Extract features
        features = self._extract_features(stroke)
        
        # Apply transform if available
        if self.transform:
            features = self.transform(features)
        
        return features, label
    
    def _extract_features(self, stroke: Dict[str, List[float]]) -> torch.Tensor:
        """
        Extract features from a stroke.
        
        Args:
            stroke: Dictionary with keys 'x', 'y', 'p' and optionally 't'
            
        Returns:
            Tensor of shape [seq_length, n_features]
        """
        # Extract coordinates and pressure
        x_points = np.array(stroke['x'], dtype=np.float32)
        y_points = np.array(stroke['y'], dtype=np.float32)
        pressures = np.array(stroke['p'], dtype=np.float32)
        
        # Compute deltas (dx, dy)
        dx = np.diff(x_points, prepend=x_points[0])
        dy = np.diff(y_points, prepend=y_points[0])
        
        # Normalize
        x_norm = (x_points - np.min(x_points)) / (np.max(x_points) - np.min(x_points) + 1e-8)
        y_norm = (y_points - np.min(y_points)) / (np.max(y_points) - np.min(y_points) + 1e-8)
        dx_norm = dx / (np.max(np.abs(dx)) + 1e-8)
        dy_norm = dy / (np.max(np.abs(dy)) + 1e-8)
        
        # Stack features
        features = np.column_stack([x_norm, y_norm, pressures, dx_norm, dy_norm])
        
        # Pad or truncate to max_length
        seq_length = len(features)
        if seq_length > self.max_length:
            # Truncate
            features = features[:self.max_length]
        elif seq_length < self.max_length:
            # Pad with zeros
            padding = np.zeros((self.max_length - seq_length, features.shape[1]), dtype=np.float32)
            features = np.vstack([features, padding])
        
        # Convert to tensor
        tensor = torch.tensor(features, dtype=torch.float32)
        
        return tensor


def create_character_dataset(
    stroke_files: List[str],
    label_file: str,
    max_length: int = 100,
    test_split: float = 0.2,
    val_split: float = 0.1,
    batch_size: int = 32,
    shuffle: bool = True,
    num_workers: int = 4
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Create train, validation, and test datasets from stroke files and labels.
    
    Args:
        stroke_files: List of paths to stroke JSON files or .rm files
        label_file: Path to label file (JSON format with stroke_id -> label mappings)
        max_length: Maximum sequence length for padding/truncation
        test_split: Fraction of data to use for testing
        val_split: Fraction of data to use for validation
        batch_size: Batch size for DataLoaders
        shuffle: Whether to shuffle the data
        num_workers: Number of workers for DataLoaders
        
    Returns:
        Tuple of (train_loader, val_loader, test_loader)
    """
    # Load labels
    with open(label_file, 'r') as f:
        label_dict = json.load(f)
    
    # Load strokes
    all_strokes = []
    all_labels = []
    
    for stroke_file in stroke_files:
        # Check if it's a .rm file or a JSON file
        if stroke_file.endswith('.rm') or stroke_file.endswith('.content'):
            # Extract strokes from .rm file
            strokes = extract_strokes_from_rm_file(stroke_file)
        else:
            # Load strokes from JSON file
            with open(stroke_file, 'r') as f:
                strokes = json.load(f)
        
        # Get stroke ID from filename
        stroke_id = os.path.splitext(os.path.basename(stroke_file))[0]
        
        # Check if this stroke has a label
        if stroke_id in label_dict:
            # Get label
            label = label_dict[stroke_id]
            
            # Convert label to index (ASCII value - 32)
            if isinstance(label, str) and len(label) == 1:
                label_idx = ord(label) - 32  # Convert to 0-based index
                
                # Add to dataset
                all_strokes.append(strokes)
                all_labels.append(label_idx)
    
    # Split into train, validation, and test sets
    num_samples = len(all_strokes)
    indices = list(range(num_samples))
    
    if shuffle:
        random.shuffle(indices)
    
    test_size = int(num_samples * test_split)
    val_size = int(num_samples * val_split)
    train_size = num_samples - test_size - val_size
    
    train_indices = indices[:train_size]
    val_indices = indices[train_size:train_size+val_size]
    test_indices = indices[train_size+val_size:]
    
    # Create datasets
    train_dataset = StrokeDataset(
        [all_strokes[i] for i in train_indices],
        [all_labels[i] for i in train_indices],
        max_length=max_length
    )
    
    val_dataset = StrokeDataset(
        [all_strokes[i] for i in val_indices],
        [all_labels[i] for i in val_indices],
        max_length=max_length
    )
    
    test_dataset = StrokeDataset(
        [all_strokes[i] for i in test_indices],
        [all_labels[i] for i in test_indices],
        max_length=max_length
    )
    
    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers
    )
    
    return train_loader, val_loader, test_loader


class StrokeLabelingTool:
    """
    Utility for labeling strokes with their corresponding characters.
    """
    
    def __init__(self, output_file: str):
        """
        Initialize the labeling tool.
        
        Args:
            output_file: Path to save the label dictionary
        """
        self.output_file = output_file
        self.labels = {}
        
        # Load existing labels if available
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                self.labels = json.load(f)
    
    def label_stroke(self, stroke_id: str, label: str):
        """
        Label a stroke with a character.
        
        Args:
            stroke_id: ID of the stroke
            label: Character label
        """
        self.labels[stroke_id] = label
        
        # Save labels
        with open(self.output_file, 'w') as f:
            json.dump(self.labels, f, indent=2)
    
    def label_strokes_from_myscript(self, stroke_file: str, text: str):
        """
        Label strokes using text from MyScript.
        
        Args:
            stroke_file: Path to stroke file
            text: Recognized text from MyScript
        """
        # Get stroke ID from filename
        stroke_id = os.path.splitext(os.path.basename(stroke_file))[0]
        
        # Load strokes
        if stroke_file.endswith('.rm') or stroke_file.endswith('.content'):
            # Extract strokes from .rm file
            strokes = extract_strokes_from_rm_file(stroke_file)
        else:
            # Load strokes from JSON file
            with open(stroke_file, 'r') as f:
                strokes = json.load(f)
        
        # Assign characters to strokes
        for i, char in enumerate(text):
            if i < len(strokes):
                stroke_char_id = f"{stroke_id}_{i}"
                self.labels[stroke_char_id] = char
        
        # Save labels
        with open(self.output_file, 'w') as f:
            json.dump(self.labels, f, indent=2)


def create_synthetic_dataset(
    output_dir: str,
    num_samples: int = 1000,
    chars: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,.",
):
    """
    Create a synthetic dataset of handwriting strokes.
    
    Args:
        output_dir: Directory to save the dataset
        num_samples: Number of samples to generate
        chars: Characters to include in the dataset
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Create label dictionary
    labels = {}
    
    # Generate samples
    for i in range(num_samples):
        # Choose a random character
        char = random.choice(chars)
        
        # Generate a simple stroke for the character
        if char in "il1|":
            # Vertical stroke
            x = [100] * 10
            y = list(range(100, 200, 10))
        elif char in "oO0":
            # Circle
            t = np.linspace(0, 2*np.pi, 20)
            x = (np.cos(t) * 50 + 100).tolist()
            y = (np.sin(t) * 50 + 100).tolist()
        elif char in "cC(":
            # Half circle
            t = np.linspace(np.pi/2, 3*np.pi/2, 15)
            x = (np.cos(t) * 50 + 100).tolist()
            y = (np.sin(t) * 50 + 100).tolist()
        else:
            # Random stroke
            length = random.randint(5, 20)
            x = [100]
            y = [100]
            for _ in range(length - 1):
                x.append(x[-1] + random.randint(-10, 10))
                y.append(y[-1] + random.randint(-10, 10))
        
        # Add pressure
        pressure = [random.uniform(0.3, 0.8) for _ in range(len(x))]
        
        # Create stroke dictionary
        stroke = {
            "id": f"synthetic_{i}",
            "x": x,
            "y": y,
            "p": pressure
        }
        
        # Save stroke
        stroke_file = os.path.join(output_dir, f"synthetic_{i}.json")
        with open(stroke_file, 'w') as f:
            json.dump(stroke, f, indent=2)
        
        # Add to labels
        labels[f"synthetic_{i}"] = char
    
    # Save labels
    label_file = os.path.join(output_dir, "labels.json")
    with open(label_file, 'w') as f:
        json.dump(labels, f, indent=2)
    
    print(f"Generated {num_samples} synthetic samples in {output_dir}")
    print(f"Labels saved to {label_file}")


# Example usage
if __name__ == "__main__":
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Dataset utilities for handwriting recognition")
    parser.add_argument("--create-synthetic", action="store_true", help="Create synthetic dataset")
    parser.add_argument("--output-dir", default="data/synthetic", help="Output directory for synthetic dataset")
    parser.add_argument("--num-samples", type=int, default=1000, help="Number of synthetic samples to generate")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create synthetic dataset if requested
    if args.create_synthetic:
        create_synthetic_dataset(args.output_dir, args.num_samples)
    else:
        parser.print_help()