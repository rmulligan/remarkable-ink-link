# Claude Vision Implementation Details

This document provides technical details about the implementation of Claude Vision integration for handwriting recognition in InkLink.

## ClaudeVisionAdapter

The `ClaudeVisionAdapter` class in `/src/inklink/adapters/claude_vision_adapter.py` is responsible for interacting with the Claude CLI to process handwritten content. 

### Core Methods

- `process_image(image_path)`: Processes a single image through Claude CLI
- `process_multiple_images(image_paths)`: Processes multiple images in a single Claude request
- `_get_persona_content()`: Loads Lilly's persona from config files
- `_get_workflow_examples()`: Loads workflow examples from memory files
- `_build_prompt(image_paths)`: Constructs the prompt for Claude with persona information

### Implementation Notes

- Uses `subprocess.run()` to execute Claude CLI commands
- Constructs JSON input that includes both images and text instructions
- Parses the JSON output from Claude CLI
- Loads persona and workflow files to customize Claude's behavior

## HandwritingAdapter

The `HandwritingAdapter` class in `/src/inklink/adapters/handwriting_adapter.py` provides an interface between the service layer and the underlying handwriting recognition implementation.

### Core Methods

- `render_rm_file(file_path)`: Converts a reMarkable file to a PNG image
- `process_rm_file(file_path)`: Processes a single reMarkable file
- `recognize_multi_page_handwriting(file_paths)`: Processes multiple reMarkable files
- `recognize_handwriting(file_paths)`: Primary method called by services

### Implementation Notes

- No longer uses MyScript web API
- Utilizes Claude Vision adapter for all recognition
- Handles both single and multi-page processing
- Maintains compatibility with existing service interface

## HandwritingRecognitionService

The `HandwritingRecognitionService` in `/src/inklink/services/handwriting_recognition_service.py` provides high-level methods for handwriting recognition.

### Core Methods

- `recognize_from_ink(ink_file)`: Processes a single ink file
- `recognize_multi_page_ink(ink_files)`: Processes multiple ink files
- `extract_content_from_notebook(notebook_dir)`: Processes an entire notebook directory

### Implementation Notes

- Services expose methods that are used by controllers and other services
- Handles file management and directories
- Delegates actual recognition to the HandwritingAdapter

## Claude CLI Integration

The implementation uses the Claude CLI to interact with Claude's API.

### Command Structure

The basic structure of a Claude CLI command is:

```bash
claude --model MODEL_NAME --file IMAGE_PATH --prompt "Prompt text" --json
```

For multiple images:

```bash
claude --model MODEL_NAME --file IMAGE_PATH1 --file IMAGE_PATH2 --prompt "Prompt text" --json
```

### JSON Response Format

The Claude CLI returns a JSON response with the following structure:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Claude's response text..."
    }
  ]
}
```

## Lilly Persona Implementation

Lilly's persona is defined in configuration files that are loaded by the `ClaudeVisionAdapter`.

### Persona Structure

The persona implementation consists of:

1. **Core Definition** (`lilly_persona.md`):
   - Defines Lilly's role and responsibilities
   - Establishes voice and tone
   - Provides guidelines for different content types

2. **Workflow Examples** (`workflow_examples.md`):
   - Contains example interactions for different scenarios
   - Shows how to handle specific tags like `#summarize` or `#task`
   - Demonstrates knowledge graph integration

3. **Prompt Template** (`lilly_prompt_template.md`):
   - Provides a structured template for all Claude prompts
   - Ensures consistent instruction format

### Prompt Construction

The prompts sent to Claude are constructed by combining:
1. The persona definition
2. Workflow examples relevant to the current context
3. Specific instructions for the current task
4. The actual handwritten content (as images)

## Error Handling

The implementation includes robust error handling:

1. **Claude CLI Errors**: Catches and logs subprocess execution errors
2. **File I/O Errors**: Handles missing or invalid files
3. **Configuration Errors**: Validates environment variables and defaults
4. **JSON Parsing Errors**: Handles malformed responses from Claude CLI

## Performance Considerations

1. **Image Optimization**: Images are optimized before sending to Claude
2. **Batching**: Multiple pages are sent in a single request when possible
3. **Caching**: Common responses and rendered images are cached
4. **Parallel Processing**: Large notebooks can be processed in parallel chunks

## Future Improvements

1. **Streaming Responses**: Implement streaming for large responses
2. **Fine-tuning**: Add support for fine-tuned Claude models
3. **Advanced Tag Processing**: Expand the set of recognized tags
4. **Knowledge Graph Integration**: Deepen integration with the knowledge graph
5. **Multi-modal Response**: Support returning both text and generated images
EOF < /dev/null