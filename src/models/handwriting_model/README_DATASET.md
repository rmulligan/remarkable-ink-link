# Creating Handwriting Recognition Training Datasets

This guide explains how to create training datasets for the handwriting recognition model using reMarkable notebooks and transcriptions.

## Overview

We provide two main approaches for creating datasets:

1. **Automated Processing** (`process_training_notebook.py`): For notebooks with alternating handwritten pages and transcriptions.
2. **Manual Dataset Builder** (`manual_dataset_builder.py`): For interactive, manual labeling of strokes.

## Preparing Transcriptions

### Option 1: Alternating Pages Method

Create a notebook on your reMarkable with:
- Even-numbered pages: Your handwriting samples
- Odd-numbered pages: Typed transcriptions of the previous page

### Option 2: Separate Transcription File

Create a single file with transcriptions for each page, separated by page markers:

```
This is the transcription for page 1.
---PAGE---
This is the transcription for page 2.
---PAGE---
This is the transcription for page 3.
```

## JSON Structure

The dataset consists of JSON files with the following structure:

### Stroke File (e.g., `char_a_12345678.json`):
```json
{
  "id": "char_a_12345678",
  "x": [100, 110, 120, ...],
  "y": [150, 145, 140, ...],
  "p": [0.5, 0.6, 0.7, ...]
}
```

### Labels File (`labels.json`):
```json
{
  "char_a_12345678": "a",
  "char_b_87654321": "b",
  "word_hello_abcdef12": "hello"
}
```

## Using the Tools

### Method 1: Automated Processing

For a notebook with alternating handwritten pages and transcriptions:

```bash
# Create character-level dataset
./process_training_notebook.py /path/to/notebook.rmdoc --output-dir data/characters --dataset-type characters

# Create word-level dataset
./process_training_notebook.py /path/to/notebook.rmdoc --output-dir data/words --dataset-type words

# Using a separate transcriptions file
./process_training_notebook.py /path/to/notebook.rmdoc --output-dir data/dataset --transcriptions-file transcriptions.txt
```

### Method 2: Manual Dataset Builder

For interactive, manual labeling of strokes:

```bash
# Process a single .rm file with its transcription
./manual_dataset_builder.py --rm-file /path/to/page.rm --text-file /path/to/transcription.txt --output-dir data/manual --type characters

# Process a notebook with a separate transcriptions file
./manual_dataset_builder.py --notebook /path/to/notebook.rmdoc --transcriptions /path/to/transcriptions.txt --output-dir data/manual --type words
```

## Recommended Dataset Structure

For optimal training, organize your dataset as follows:

```
handwriting_model/
└── data/
    ├── characters/
    │   ├── char_a_12345678.json
    │   ├── char_b_87654321.json
    │   ├── ...
    │   └── labels.json
    ├── words/
    │   ├── word_hello_abcdef12.json
    │   ├── word_world_12345678.json
    │   ├── ...
    │   └── labels.json
    └── combined/
        ├── all_strokes.json
        └── labels.json
```

## Best Practices for Training Data

1. **Character Distribution**: Include at least 20-30 examples of each letter (uppercase and lowercase), number, and common punctuation.

2. **Variety**: Include different writing styles and sizes for the same character.

3. **Complete Words**: For word-level recognition, include common words written naturally.

4. **Consistent Labeling**: Ensure labels are accurate and consistently applied.

5. **Data Splitting**: After collection, split your data into training (70%), validation (15%), and test (15%) sets.

## Training the Model

Once your dataset is prepared, you can train the model:

```bash
# Train on character dataset
python deep_scribe/train.py --data-dir data/characters --epochs 50 --bidirectional --model-dir checkpoints

# Train on word dataset
python deep_scribe/train.py --data-dir data/words --epochs 50 --bidirectional --model-dir checkpoints
```

## Testing the Model

After training, test the model using:

```bash
# Test with synthetic data
python deep_scribe/demo.py --synthetic --model checkpoints/best_model.pt

# Test with a specific .rm file
python deep_scribe/demo.py --file /path/to/test.rm --model checkpoints/best_model.pt
```