# Round-Trip Workflow: Handwriting to AI and Back

This document describes the round-trip workflow that enables handwritten questions to be answered by AI and returned to the reMarkable in native ink format.

## Overview

The round-trip process involves:

1. Handwritten note (.rm file) from the reMarkable
2. Stroke extraction and recognition via MyScript iink SDK
3. Text processing (potentially with AI)
4. Converting response to reMarkable-compatible ink format
5. Uploading the response to the reMarkable cloud

## Components

### HandwritingRecognitionService

This service handles the conversion from handwritten strokes to text:

- Extracts strokes from .rm files using rmscene
- Formats them for the MyScript iink SDK
- Handles authentication and API communication
- Retrieves the recognized text

### RoundTripService

Orchestrates the complete process:

- Connects the HandwritingRecognitionService with AI processing
- Prepares responses in markdown format
- Leverages DocumentService to create .rm files
- Uploads responses to reMarkable cloud

## Usage

### From CLI

```bash
# Process a handwritten query
inklink roundtrip /path/to/query.rm

# Process a query and save text response to file
inklink roundtrip /path/to/query.rm -o response.txt
```

### Programmatic Use

```python
from inklink.services.round_trip_service import RoundTripService

# Initialize the service
service = RoundTripService()

# Process a handwritten query
success, result = service.process_handwritten_query("/path/to/query.rm")

if success:
    print(f"Recognized text: {result['recognized_text']}")
    print(f"AI response: {result['response_text']}")
```

## Configuration

The round-trip functionality requires:

1. MyScript iink SDK API credentials:
   - Set environment variables `MYSCRIPT_APP_KEY` and `MYSCRIPT_HMAC_KEY`
   - Or provide directly to the HandwritingRecognitionService constructor

2. reMarkable cloud authentication:
   - Configure using `inklink auth` command
   - Stores credentials for rmapi

## Future Extensions

The current implementation provides a foundation that can be extended to support:

1. **AI Integration**:
   - Connect to OpenAI, Anthropic, or other LLM providers
   - Add document/knowledge base context for responses
   - Support for different AI personas or styles

2. **Enhanced Recognition**:
   - Support for diagrams and mathematical expressions
   - Multiple language support
   - Combined vision model verification for improved accuracy

3. **Advanced UI**:
   - Web interface for managing the round-trip workflow
   - Status tracking for processed documents
   - Templates for different types of questions

## Troubleshooting

### Missing MyScript Credentials

If the handwriting recognition fails with authorization errors, ensure:
- MyScript credentials are set as environment variables
- Your MyScript account is active and has API access enabled
- The API calls are not exceeding usage limits

### Recognition Issues

If text recognition is inaccurate:
- Check that the handwriting is clear and well-separated
- Consider adjusting the stroke capture resolution
- Test with different handwriting styles

### Upload Problems

If uploads to reMarkable cloud fail:
- Verify reMarkable cloud authentication is set up correctly
- Check that rmapi is properly installed and in the PATH
- Ensure the target folder exists in your reMarkable account
