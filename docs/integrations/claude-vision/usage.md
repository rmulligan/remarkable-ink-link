# Using Lilly with Claude Vision

This guide explains how to use the Claude Vision integration for handwriting recognition with the Lilly persona.

## Overview

Lilly is a personified AI assistant that uses Claude Vision to analyze and respond to handwritten notes from a reMarkable tablet. The system:

1. Renders reMarkable notebook pages as images
2. Sends the images to Claude using the Claude CLI
3. Processes Claude's response according to the Lilly persona guidelines
4. Returns structured results based on the content and tags in the handwritten notes

## Setup Requirements

1. Claude CLI installed and configured (see [Claude CLI documentation](https://github.com/anthropics/claude-cli))
2. Claude model with vision capabilities (claude-3-opus, claude-3-sonnet, or claude-3-haiku)
3. Properly configured Lilly persona files

## Configuration

### Environment Variables

Add the following to your `.env` file:

```
CLAUDE_COMMAND=claude  # Path to Claude CLI executable if not in PATH
CLAUDE_MODEL=claude-3-opus-20240229  # Preferred Claude model
```

### Persona Configuration

Lilly's persona is defined in the following files:

1. `/lilly/config/lilly_persona.md` - Core personality and behavior definition
2. `/lilly/config/lilly_prompt_template.md` - Template for structuring prompts to Claude
3. `/lilly/memories/workflow_examples.md` - Example workflows and responses for different scenarios

## Usage

### Command Line

Process a single reMarkable notebook page:

```bash
python -m inklink.main process <path_to_rm_file>
```

Process an entire notebook:

```bash
python -m inklink.main process-notebook <notebook_directory>
```

### Programmatic Usage

```python
from inklink.services.handwriting_recognition_service import HandwritingRecognitionService
from inklink.di.container import Container

# Get service from container
container = Container()
recognition_service = container.get(HandwritingRecognitionService)

# Process a single page
result = recognition_service.recognize_from_ink("/path/to/page.rm")

# Process multiple pages
results = recognition_service.recognize_multi_page_ink(["/path/to/page1.rm", "/path/to/page2.rm"])

# Process an entire notebook
results = recognition_service.extract_content_from_notebook("/path/to/notebook/directory")
```

## Special Tags

Lilly recognizes special tags in handwritten content that trigger specific behaviors:

| Tag | Description |
|-----|-------------|
| `#summarize` | Generates a concise summary of the notes |
| `#task` | Extracts action items and creates a task list |
| `#question` | Treats the content as a question to be answered |
| `#code` | Attempts to extract and format code blocks |
| `#entity` | Extracts key entities for knowledge graph integration |
| `#math` | Interprets mathematical expressions or equations |

## Response Structure

Lilly's responses typically include:

1. **Acknowledgment** - Confirmation of what was in the handwritten content
2. **Structured Response** - Formatted output based on content type and tags
3. **Follow-up** - Suggestions for next steps when appropriate

## Example Workflows

### Summarizing Meeting Notes

1. Take handwritten meeting notes on reMarkable
2. Add `#summarize` tag to the notes
3. Upload/sync the notebook
4. Process with Lilly
5. Receive a concise summary of key points

### Creating Task Lists

1. Write project thoughts or plans on reMarkable
2. Add `#task` tag to indicate action items are present
3. Process with Lilly
4. Receive a structured task list extracted from your notes

### Knowledge Graph Integration

1. Write research notes or information on reMarkable
2. Add `#entity` tag to indicate important entities
3. Process with Lilly
4. Entities are extracted and added to knowledge graph
5. Relationships between entities are identified and mapped

## Troubleshooting

### Image Processing Issues

If handwritten content isn't recognized correctly:
- Ensure handwriting is clear and legible
- Check that pages are properly rendered as images
- Verify Claude CLI is working correctly with `claude --version`

### Persona Configuration Issues

If Lilly's responses don't match expected behavior:
- Check that persona files exist in the correct locations
- Verify content of persona files for any formatting issues
- Ensure Claude model specified has vision capabilities

### Connection Issues

If Claude CLI fails to connect:
- Check internet connection
- Verify Claude CLI authentication
- Ensure model specified is available to your account