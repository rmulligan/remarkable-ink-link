"""
Preprocessing utilities for handwriting recognition

This module contains functions for preprocessing stroke data extracted
from reMarkable files for handwriting recognition.
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import torch

# Try importing rmscene
try:
    import rmscene
    from rmscene.scene_stream import read_tree
    from rmscene.scene_items import Line
    RMSCENE_AVAILABLE = True
except ImportError:
    RMSCENE_AVAILABLE = False
    print("rmscene not available, some functionality will be limited")


def extract_strokes_from_rm_file(rm_file_path: str) -> List[Dict[str, Any]]:
    """
    Extract strokes from a reMarkable file using rmscene

    Args:
        rm_file_path: Path to .rm file

    Returns:
        List of stroke dictionaries
    """
    if not RMSCENE_AVAILABLE:
        raise ImportError("rmscene is required for extracting strokes from .rm files")

    try:
        # Parse .rm file
        with open(rm_file_path, "rb") as f:
            scene_tree = read_tree(f)

        # Extract strokes
        strokes = []
        
        # Find all Line items in the tree
        for item_id, item in scene_tree.items.items():
            if isinstance(item, Line):
                # Extract x, y, pressure and timestamps for each point
                x_points = []
                y_points = []
                pressures = []
                timestamps = []
                
                for point in item.points:
                    x_points.append(point.x)
                    y_points.append(point.y)
                    pressures.append(point.pressure)
                    # Use 't' attribute for timestamp in newer API
                    timestamps.append(point.t if hasattr(point, 't') else 0)
                
                # Create stroke dictionary
                stroke = {
                    "id": str(item_id),
                    "x": x_points,
                    "y": y_points,
                    "p": pressures,
                    "t": timestamps,
                    "color": str(item.color) if hasattr(item, 'color') else "#000000",
                    "width": float(item.pen.value) if hasattr(item, 'pen') else 2.0,
                }
                
                strokes.append(stroke)

        return strokes

    except Exception as e:
        print(f"Error extracting strokes from {rm_file_path}: {e}")
        return []


def normalize_strokes(strokes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize stroke data for better model performance

    Args:
        strokes: List of stroke dictionaries

    Returns:
        Normalized stroke dictionaries
    """
    # Deep copy to avoid modifying original
    normalized_strokes = []
    
    # If no strokes, return empty list
    if not strokes:
        return []
    
    # First pass: find min/max values for normalization
    all_x = []
    all_y = []
    
    for stroke in strokes:
        all_x.extend(stroke['x'])
        all_y.extend(stroke['y'])
    
    # Calculate statistics
    min_x = min(all_x) if all_x else 0
    max_x = max(all_x) if all_x else 1
    min_y = min(all_y) if all_y else 0
    max_y = max(all_y) if all_y else 1
    
    # Ensure we don't divide by zero
    width = max(max_x - min_x, 1)
    height = max(max_y - min_y, 1)
    
    # Second pass: normalize strokes
    for stroke in strokes:
        norm_stroke = {}
        
        # Copy all fields
        for key in stroke:
            norm_stroke[key] = stroke[key].copy() if isinstance(stroke[key], list) else stroke[key]
        
        # Normalize x and y coordinates to range [0, 1]
        norm_stroke['x'] = [(x - min_x) / width for x in stroke['x']]
        norm_stroke['y'] = [(y - min_y) / height for y in stroke['y']]
        
        # Pressure should already be in [0, 1]
        
        normalized_strokes.append(norm_stroke)
    
    return normalized_strokes


def compute_stroke_features(strokes: List[Dict[str, Any]]) -> np.ndarray:
    """
    Compute features for each point in the strokes

    Args:
        strokes: List of stroke dictionaries

    Returns:
        Array of shape [n_points, n_features] with computed features
    """
    # Features: [x, y, pressure, dx, dy, pen_up]
    features = []
    
    for i, stroke in enumerate(strokes):
        x_points = stroke['x']
        y_points = stroke['y']
        pressures = stroke['p']
        
        # Must have same number of points
        assert len(x_points) == len(y_points) == len(pressures), "Stroke points must have same length"
        
        for j in range(len(x_points)):
            # Calculate deltas (set to 0 for first point in stroke)
            dx = 0 if j == 0 else x_points[j] - x_points[j-1]
            dy = 0 if j == 0 else y_points[j] - y_points[j-1]
            
            # Pen state (0 = down, 1 = up)
            # For reMarkable, all points within a stroke are pen-down
            # Only include pen-up signal for the last point of the stroke
            pen_up = 1.0 if j == len(x_points) - 1 else 0.0
            
            # Add features [x, y, pressure, dx, dy, pen_up]
            features.append([x_points[j], y_points[j], pressures[j], dx, dy, pen_up])
    
    return np.array(features, dtype=np.float32) if features else np.zeros((0, 6), dtype=np.float32)


def strokes_to_tensor(strokes: List[Dict[str, Any]], max_length: int = 2000) -> torch.Tensor:
    """
    Convert strokes to tensor format required by the model

    Args:
        strokes: List of stroke dictionaries
        max_length: Maximum sequence length

    Returns:
        Tensor of shape [1, seq_length, 5] containing features
    """
    # Normalize strokes
    normalized_strokes = normalize_strokes(strokes)
    
    # Compute features
    features = compute_stroke_features(normalized_strokes)
    
    # Create tensor (without pen_up for the model, which uses only 5 features)
    if len(features) == 0:
        return torch.zeros((1, 1, 5), dtype=torch.float32)
        
    features_tensor = torch.tensor(features[:, :5], dtype=torch.float32)
    
    # Add batch dimension
    features_tensor = features_tensor.unsqueeze(0)
    
    # Pad or truncate to max_length
    if features_tensor.size(1) > max_length:
        features_tensor = features_tensor[:, :max_length, :]
    elif features_tensor.size(1) < max_length:
        padding = torch.zeros(
            (1, max_length - features_tensor.size(1), 5),
            dtype=torch.float32
        )
        features_tensor = torch.cat([features_tensor, padding], dim=1)
    
    return features_tensor


def save_strokes_to_json(strokes: List[Dict[str, Any]], output_path: str):
    """
    Save extracted strokes to a JSON file for later use

    Args:
        strokes: List of stroke dictionaries
        output_path: Path to save JSON file
    """
    with open(output_path, 'w') as f:
        json.dump(strokes, f, indent=2)
    
    print(f"Saved {len(strokes)} strokes to {output_path}")


def load_strokes_from_json(input_path: str) -> List[Dict[str, Any]]:
    """
    Load strokes from a JSON file

    Args:
        input_path: Path to JSON file

    Returns:
        List of stroke dictionaries
    """
    with open(input_path, 'r') as f:
        strokes = json.load(f)
    
    print(f"Loaded {len(strokes)} strokes from {input_path}")
    return strokes


# Example usage
if __name__ == "__main__":
    import sys
    
    # Check if a .rm file path is provided
    if len(sys.argv) > 1:
        rm_file_path = sys.argv[1]
        
        # Extract strokes
        strokes = extract_strokes_from_rm_file(rm_file_path)
        
        # Generate output path
        output_path = os.path.splitext(rm_file_path)[0] + "_strokes.json"
        
        # Save strokes
        save_strokes_to_json(strokes, output_path)
        
        # Print statistics
        print(f"Extracted {len(strokes)} strokes with {sum(len(s['x']) for s in strokes)} points")
    else:
        print("Usage: python preprocessing.py <rm_file_path>")