# Remarkable Handwriting Recognition

This package provides a modular system for handwriting recognition using stroke data from reMarkable files. It supports both online and offline recognition methods.

## Features

- **Stroke Extraction**: Extract stroke data from reMarkable `.rm` files using rmscene
- **Preprocessing Pipeline**: Normalize and prepare stroke data for recognition
- **Multiple Recognition Options**:
  - Transformer-based model for custom training
  - Online API recognition via MyScript
  - Offline recognition with local models
- **GPU Acceleration**: Utilize GPU for faster inference when available
- **Test Utilities**: Generate and visualize artificial stroke data

## Installation

### Prerequisites

- Python 3.8+
- PyTorch 1.7+
- rmscene (for handling reMarkable files)

### Setup

1. Create a virtual environment:
   ```bash
   mkdir -p handwriting_model
   cd handwriting_model
   python -m venv env
   ```

2. Activate the environment:
   ```bash
   source env/bin/activate  # Linux/Mac
   env\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install torch numpy matplotlib tqdm scipy scikit-learn pandas
   pip install transformers einops tensorboard
   pip install mediapipe
   ```

4. If using rmscene for reMarkable file parsing:
   ```bash
   pip install rmscene
   ```

## Usage

### Generating Test Strokes

```bash
python generate_test_strokes.py "hello world" --visualize --output test_strokes.json
```

Options:
- `--noise`: Set noise level (0-1) to simulate natural variation
- `--visualize`: Generate a visualization of the strokes
- `--output`: Specify output file (default: test_strokes.json)

### Recognition

#### Using the stroke recognition system:

```bash
python stroke_recognition.py test_strokes.json
```

Options:
- `--app-key`: MyScript application key (for online recognition)
- `--hmac-key`: MyScript HMAC key (for online recognition)
- `--output`: Save recognized text to file

#### Using the transformer model (requires training):

```bash
python remarkable_integration.py test_strokes.json --model checkpoints/model.pt
```

### Training the Transformer Model

1. Generate a training dataset (not included)
2. Train the model:
   ```bash
   python train.py --data path/to/dataset --epochs 50
   ```

3. For quick testing, use the mock model:
   ```bash
   python mock_train.py
   ```

## Module Overview

### `preprocessing.py`

Contains utilities for processing stroke data:
- `extract_strokes_from_rm_file()`: Extract strokes from reMarkable files
- `normalize_strokes()`: Normalize stroke coordinates and attributes
- `compute_stroke_features()`: Generate additional features from strokes
- `strokes_to_tensor()`: Convert strokes to tensor format for model input

### `model.py`

Transformer-based handwriting recognition model:
- `StrokeEmbedding`: Embeds stroke points into a learnable representation
- `HandwritingTransformer`: Core transformer model architecture
- `HandwritingRecognitionSystem`: Complete system with preprocessing and inference

### `stroke_recognition.py`

Adaptable recognition system:
- `StrokeRecognizer`: Base class for recognition methods
- `OnlineRecognizer`: Uses MyScript API for online recognition
- `OfflineRecognizer`: Uses local models for offline recognition
- `get_best_available_recognizer()`: Selects the best available method

### `remarkable_integration.py`

Integration with reMarkable extraction:
- `RemarkableHandwritingRecognizer`: Combines stroke extraction with recognition
- Command-line interface for processing reMarkable files

### `generate_test_strokes.py`

Utility for generating test data:
- `generate_stroke_data()`: Creates artificial stroke data for testing
- `visualize_strokes()`: Generates visualization of strokes

## API Keys

For online recognition using MyScript, you need API keys:

1. Register at the [MyScript Developer Portal](https://developer.myscript.com/)
2. Create a new application to get API keys
3. Add them to your environment:
   ```bash
   export MYSCRIPT_APP_KEY="your-app-key"
   export MYSCRIPT_HMAC_KEY="your-hmac-key"
   ```

## Future Work

- Implement full training pipeline with stroke dataset
- Add support for additional languages
- Integrate with more recognition APIs
- Add mathematical expression recognition
- Improve preprocessing for better recognition accuracy
- Add support for diagram recognition

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [MyScript](https://developer.myscript.com/) for online recognition API
- [rmscene](https://github.com/ricklupton/rmscene) for reMarkable file parsing
- [transformers](https://huggingface.co/transformers/) for transformer architecture components