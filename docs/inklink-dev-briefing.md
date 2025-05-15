# InkLink Round-Trip Functionality: Developer Guide
May 5th, 2025

This guide provides detailed instructions and documentation for developers to continue working on the InkLink round-trip functionality. It covers architecture, setup, implementation details, testing strategies, and future enhancement opportunities.

## 1. Architecture Overview

The round-trip functionality consists of three primary components:

1. **HandwritingRecognitionService**: Responsible for extracting strokes from .rm files and converting handwriting to text via MyScript's iink SDK.

2. **RoundTripService**: Orchestrates the entire workflow, connecting handwriting recognition, AI processing, document creation, and uploading back to reMarkable.

3. **CLI Integration**: Provides a user-friendly command line interface for triggering the round-trip process.

### Component Interactions

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Handwritten    │     │ Handwriting     │     │  AI Processing  │
│  .rm File       │────▶│ Recognition     │────▶│  (Placeholder)  │
│                 │     │ Service         │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  reMarkable     │     │  Document       │     │  Response       │
│  Cloud          │◀────│  Service        │◀────│  Generation     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 2. Development Environment Setup

### Prerequisites

- Python 3.10+
- Poetry for dependency management
- reMarkable Cloud account
- MyScript Developer account with iink SDK access

### Environment Configuration

1. **Clone the repository and install dependencies**:
   ```bash
   git clone https://github.com/rmulligan/remarkable-ink-link.git
   cd remarkable-ink-link
   poetry install
   ```

2. **Set up environment variables**:
   ```bash
   # MyScript API credentials
   export MYSCRIPT_APP_KEY="your_app_key"
   export MYSCRIPT_HMAC_KEY="your_hmac_key"
   
   # Optional: custom paths
   export INKLINK_RMAPI="/path/to/rmapi"
   export INKLINK_TEMP="/path/to/temp/dir"
   export INKLINK_OUTPUT="/path/to/output/dir"
   ```

3. **Configure reMarkable authentication**:
   ```bash
   poetry run inklink auth
   ```
   This will open a web interface at http://127.0.0.1:8000/auth to set up reMarkable Cloud access.

4. **Test installation**:
   ```bash
   poetry run inklink roundtrip --help
   ```

## 3. Implementation Details

### HandwritingRecognitionService

The `HandwritingRecognitionService` in `src/inklink/services/handwriting_recognition_service.py` handles:

- Extracting strokes from `.rm` files using `rmscene`
- Converting strokes to MyScript iink format
- Authentication with MyScript APIs using HMAC signatures
- Submitting ink data for recognition
- Retrieving recognized text

Key methods:
- `extract_strokes(rm_file_path)`: Extracts stroke data from a .rm file
- `convert_to_iink_format(strokes)`: Formats strokes for iink SDK
- `recognize_handwriting(iink_data)`: Submits data to MyScript API
- `export_content(content_id)`: Retrieves recognized text

### RoundTripService

The `RoundTripService` in `src/inklink/services/round_trip_service.py` orchestrates:

- Calling the handwriting recognition service
- Processing the recognized text (currently a placeholder for AI integration)
- Generating a response document
- Converting to reMarkable format
- Uploading to reMarkable Cloud

Key method:
- `process_handwritten_query(rm_file_path)`: Processes a handwritten query and returns the result

### AI Integration Placeholder

The current implementation includes a placeholder for AI processing:

```python
# In a real implementation, this is where you would send the text to an AI service
# and get a response. For testing purposes, we generate a simple response.
response_text = f"Response to: {recognized_text}\n\nThis is a simulated AI response."
```

This is the primary integration point for connecting to LLM providers.

## 4. Testing Strategy

### Unit Tests

Unit tests are located in:
- `tests/test_handwriting_recognition.py`: Tests for the handwriting recognition service
- `tests/test_round_trip.py`: Tests for the round-trip service

These tests use mocks to avoid external dependencies and focus on the logic of each component.

### Manual Testing

For manual testing, you need:
1. A sample `.rm` file containing handwritten text
2. Valid MyScript API credentials
3. Valid reMarkable Cloud credentials

Execute:
```bash
poetry run inklink roundtrip /path/to/sample.rm
```

### Test Data

Create a directory for test data:
```bash
mkdir -p tests/data
```

Sample `.rm` files can be obtained from a reMarkable tablet or created using the `rmscene` library.

## 5. Extension Points

### Integrating with LLM Providers

The primary extension point is AI integration. To integrate with an LLM provider:

1. Create a new service in `src/inklink/services/ai_service.py`:
   ```python
   class AIService:
       """Service for AI text processing."""
       
       def __init__(self, api_key=None):
           self.api_key = api_key or os.environ.get("AI_API_KEY")
           
       def process_query(self, query_text):
           """Process a text query and return an AI response."""
           # Implement API calls to your preferred LLM provider
           # Example with a hypothetical API
           response = requests.post(
               "https://api.example-ai.com/v1/completions",
               headers={"Authorization": f"Bearer {self.api_key}"},
               json={"prompt": query_text, "max_tokens": 1000}
           )
           
           return response.json()["text"]
   ```

2. Update `RoundTripService` to use the AI service:
   ```python
   def __init__(self, 
               handwriting_service=None,
               document_service=None,
               remarkable_service=None,
               ai_service=None):
       # Add AI service
       self.ai_service = ai_service or AIService()
       
   def process_handwritten_query(self, rm_file_path):
       # ...existing code...
       
       # Replace placeholder with actual AI service call
       response_text = self.ai_service.process_query(recognized_text)
       
       # ...rest of the method...
   ```

### Supporting Additional Content Types

To support math expressions, diagrams, or other content types:

1. Extend recognition parameters in `HandwritingRecognitionService.recognize_handwriting()`:
   ```python
   def recognize_handwriting(self, iink_data, content_type="Text", language="en_US"):
       # Allow content_type to be "Text", "Math", "Diagram", etc.
       request_data = {
           "configuration": {
               "lang": language,
               "contentType": content_type,
               # Content-specific configuration
               content_type.lower(): {
                   # Content-specific parameters
               }
           },
           **iink_data
       }
       # ...rest of the method...
   ```

2. Add content-specific export formats in `export_content()`:
   ```python
   def export_content(self, content_id, format_type="text"):
       # For math, you might want LaTex or MathML
       # For diagrams, you might want SVG
       request_data = {
           "format": format_type
       }
       # ...rest of the method...
   ```

## 6. Known Limitations

1. **Handwriting Recognition Quality**: Recognition accuracy depends on handwriting clarity and the capabilities of MyScript's API.

2. **AI Processing**: Currently implemented as a placeholder without actual AI connection.

3. **Content Types**: Currently optimized for text content. Math, diagrams, and drawings require further implementation.

4. **Error Handling**: While basic error handling is implemented, complex error recovery might need enhancement.

5. **Performance**: Large `.rm` files with many strokes may cause performance issues.

## 7. Future Development Roadmap

### Short-term Tasks

1. **AI Integration**: Connect to a production LLM API (OpenAI, Anthropic, etc.)
2. **Content Context**: Add support for including document context in AI queries
3. **Response Formatting**: Enhance response formatting with markdown support
4. **User Interface**: Add a simple web UI for managing the round-trip process

### Medium-term Tasks

1. **Math and Diagram Support**: Add support for mathematical expressions and diagrams
2. **Multi-page Processing**: Process multi-page documents and maintain context
3. **Template System**: Create templates for different types of queries/responses
4. **Local Models**: Support local LLMs for privacy-focused deployments

### Long-term Vision

1. **Bidirectional Synchronization**: Real-time sync between edits on tablet and AI processing
2. **Knowledge Graph Integration**: Connect document content to a knowledge graph
3. **Multi-modal Processing**: Combine text, images, and diagrams in processing
4. **Collaborative Workflows**: Support multi-user collaboration with shared AI context

## 8. Troubleshooting Common Issues

### MyScript API Authentication

If you encounter authentication errors with MyScript:

1. Verify API key environment variables are correctly set
2. Check that HMAC signatures are correctly generated
3. Ensure your MyScript account has API access enabled
4. Check for usage limits or quotas

### reMarkable Cloud Access

If uploads to reMarkable cloud fail:

1. Verify authentication via `inklink auth` was successful
2. Check that the `rmapi` tool is properly installed
3. Ensure target folders exist in your reMarkable account
4. Check for space limitations on your reMarkable account

### Stroke Extraction

If stroke extraction fails:

1. Verify the `.rm` file is valid and not corrupted
2. Check that `rmscene` library is correctly installed
3. Test with a simple file containing minimal strokes

## 9. Development Best Practices

1. **Version Control**:
   - Create feature branches for new functionality
   - Write meaningful commit messages
   - Create pull requests for code review

2. **Testing**:
   - Write tests for new functionality
   - Update existing tests when modifying code
   - Ensure CI passes before merging

3. **Documentation**:
   - Update docstrings for new methods
   - Keep the developer documentation up-to-date
   - Document integration points with external services

4. **Error Handling**:
   - Use consistent error handling patterns
   - Log errors with appropriate level and context
   - Return meaningful error messages to users

5. **Configuration**:
   - Use environment variables for sensitive data
   - Add new configuration options to `config.py`
   - Document configuration requirements

By following this guide, developers should be able to understand, maintain, and extend the round-trip functionality within the InkLink project.