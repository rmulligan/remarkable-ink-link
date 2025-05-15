# Claude Vision Integration Overview

This document provides an overview of the Claude Vision integration for handwriting recognition in InkLink.

## Introduction

The Claude Vision integration replaces the previous MyScript-based handwriting recognition system with Claude's powerful vision capabilities. This approach offers several advantages:

1. **No separate API service required** - Uses Claude's vision capabilities directly
2. **Improved accuracy** - Leverages Claude's advanced AI models for better recognition
3. **Contextual understanding** - Recognizes not just text but meaning and intent
4. **Special tag processing** - Handles tags like `#summarize`, `#task`, and `#entity`
5. **Personified assistant** - Implements "Lilly" personality for interactions

## Architecture

The Claude Vision integration consists of these primary components:

1. **ClaudeVisionAdapter** (`/src/inklink/adapters/claude_vision_adapter.py`)
   - Interfaces with Claude CLI to process images
   - Loads and applies Lilly's persona
   - Handles single and multi-page recognition

2. **HandwritingAdapter** (`/src/inklink/adapters/handwriting_adapter.py`)
   - Acts as intermediary between service layer and vision adapter
   - Renders `.rm` files to images for processing
   - Manages recognition workflow

3. **HandwritingRecognitionService** (`/src/inklink/services/handwriting_recognition_service.py`)
   - Provides high-level service methods for recognition
   - Handles notebook processing
   - Exposes API for other services to use

4. **Lilly Persona** (`/lilly/config/lilly_persona.md`)
   - Defines personality, voice, and behavior
   - Provides guidance for handling different content types
   - Outlines response structures and workflows

## Workflow

The typical workflow for handwriting recognition:

1. User writes notes on reMarkable tablet
2. Notes sync to reMarkable Cloud
3. InkLink downloads the notebook or page
4. `.rm` files are rendered to PNG images
5. Images are sent to Claude with personalized prompt
6. Claude processes the images and returns structured response
7. Response is parsed and returned to the user
8. Optional: Entity extraction for knowledge graph

For tag-based processing:
1. User adds tags like `#summarize`, `#task`, or `#entity` to notes
2. During processing, these tags trigger specific behaviors
3. Processed results reflect the requested action

## Configuration

The Claude Vision integration is configured through environment variables:

```bash
# Path to Claude CLI executable (if not in PATH)
CLAUDE_COMMAND=claude

# Preferred Claude model (must have vision capabilities)
CLAUDE_MODEL=claude-3-opus-20240229
```

## File Structure

```
/src/inklink/adapters/
  - claude_vision_adapter.py  # Claude CLI integration
  - handwriting_adapter.py    # Handwriting adapter

/src/inklink/services/
  - handwriting_recognition_service.py  # Service layer

/lilly/
  /config/
    - lilly_persona.md          # Persona definition
    - lilly_prompt_template.md  # Prompt template
  /memories/
    - workflow_examples.md      # Example workflows
```

## Getting Started

To set up the Claude Vision integration:

1. Install Claude CLI and authenticate
2. Configure environment variables in `.env` file
3. Ensure Lilly persona files are in place
4. Test with a sample `.rm` file:
   ```bash
   python -m inklink.main process path/to/file.rm
   ```

For complete setup and usage instructions, see [Usage](usage.md).

## Developer Notes

When extending the Claude Vision integration:

1. **Prompt Engineering** - Improvements to prompting can be made in the `ClaudeVisionAdapter` class
2. **Persona Updates** - Enhance Lilly's capabilities by updating the persona files
3. **Performance Optimization** - Consider batch processing for multi-page documents
4. **Error Handling** - Graceful degradation if Claude CLI is unavailable

## Integration with Other Components

The Claude Vision integration works closely with:

1. **Knowledge Graph** - Entity extraction from handwritten notes
2. **Round-trip Service** - Full workflow from handwriting to AI response
3. **reMarkable Service** - Access to notebooks and pages

## Testing

Tests for the Claude Vision integration are in:

- `/tests/adapters/test_claude_vision_adapter.py`
- `/tests/services/test_handwriting_recognition_service.py`
- `/tests/test_lilly_integration.py`

Run the tests with:

```bash
poetry run pytest tests/adapters/test_claude_vision_adapter.py
```
EOF < /dev/null