# Deep-Scribe for reMarkable

A handwriting recognition system for reMarkable tablet strokes, adapted from the Deep-Scribe project.

## Overview

This project provides a complete pipeline for recognizing handwritten text from reMarkable stroke data using a lightweight LSTM model. The key features are:

- **Stroke Extraction** from reMarkable .rm files
- **Dataset Creation** from paired strokes and text
- **LSTM-based Recognition Model** that works directly with stroke data
- **Training Pipeline** for customizing to your handwriting
- **Interactive Demo** for testing recognition

## Getting Started

### Installation

```bash
# Create and activate virtual environment
python -m venv env
source env/bin/activate  # Linux/Mac
# env\Scripts\activate    # Windows

# Install dependencies
pip install torch numpy matplotlib tqdm scipy pandas
```

### Quick Demo with Synthetic Data

```bash
# Run demo with synthetic data (no training required)
python demo.py --synthetic
```

### Using with reMarkable Files

```bash
# Extract strokes from a reMarkable file and recognize
python demo.py --file /path/to/your/file.rm
```

## Creating Your Own Dataset

The most powerful way to use this system is by creating a dataset from your own handwriting. You can use the existing MyScript recognition on your reMarkable to provide "ground truth" labels.

### 1. Extract Strokes and Text

Using your on-device MyScript recognition, extract pairs of strokes and recognized text:

```bash
# Create dataset directory
mkdir -p data/my_handwriting

# Use the labeling tool to create a dataset
# This assumes you have a file with text extracted from MyScript
python -c "from dataset import StrokeLabelingTool; tool = StrokeLabelingTool('data/my_handwriting/labels.json'); tool.label_strokes_from_myscript('/path/to/rm/file.rm', 'Text from MyScript')"
```

### 2. Train Your Model

```bash
# Train on your dataset
python train.py --data-dir data/my_handwriting --epochs 50 --bidirectional --model-dir checkpoints
```

### 3. Test Your Model

```bash
# Test on new strokes
python demo.py --file /path/to/test/file.rm --model checkpoints/best_model.pt
```

## Using in Your Projects

You can integrate the trained model into your own projects:

```python
from model import CharacterPredictor
from preprocessing import extract_strokes_from_rm_file

# Create predictor
predictor = CharacterPredictor(model_path="checkpoints/best_model.pt")

# Extract strokes from a file
strokes = extract_strokes_from_rm_file("path/to/file.rm")

# Recognize text (one character per stroke)
for stroke in strokes:
    character, confidence = predictor.predict(stroke)
    print(f"Recognized character: {character} (confidence: {confidence:.4f})")
```

## Project Structure

- `model.py` - LSTM-based recognition model
- `dataset.py` - Dataset utilities for creating and managing stroke data
- `train.py` - Training script with visualization
- `demo.py` - Interactive demo for testing recognition
- `preprocessing.py` - Utilities for extracting and preprocessing strokes

## References

This project is adapted from the deep-scribe handwriting recognition project:
- [deep-scribe/handwriting-recognition](https://github.com/deep-scribe/handwriting-recognition)

## Future Work

- Implement word-level recognition instead of individual characters
- Add support for mathematical expressions and diagrams
- Create a web UI for real-time recognition
- Improve preprocessing for better handling of different writing styles