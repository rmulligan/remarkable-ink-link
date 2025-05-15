# MyScript Integration Guide

This document provides a comprehensive guide to using the MyScript handwriting recognition integration in InkLink.

## Introduction

InkLink supports handwriting recognition using MyScript's advanced recognition technology through their Web API. This enables converting handwritten notes from your reMarkable tablet to text, facilitating search, processing, and integration with other services.

## API Credentials

To use MyScript's handwriting recognition, you need the following credentials:

- **Application Key**: Used to identify your application
- **HMAC Key**: Used to sign API requests for security

You can obtain these credentials from the [MyScript Developer Portal](https://developer.myscript.com/).

## Configuration

### Environment Variables

Add your MyScript credentials to your `.env` file:

```bash
# MyScript API credentials
MYSCRIPT_APP_KEY=your-application-key-here
MYSCRIPT_HMAC_KEY=your-hmac-key-here
```

## Usage

The handwriting recognition is integrated into the core InkLink architecture and can be used through the HandwritingRecognitionService.

### Basic Usage Example

```python
from inklink.services.handwriting_recognition_service import HandwritingRecognitionService

# Create a service with your API credentials
service = HandwritingRecognitionService()

# Process a reMarkable file
result = service.recognize_from_ink(file_path="/path/to/file.rm")
print(f"Recognized text: {result}")

# Process multiple pages
result = service.recognize_multi_page_ink([
    "/path/to/page1.rm",
    "/path/to/page2.rm"
])
```

## Testing the Integration

Two test scripts are provided to verify the integration:

1. `test_myscript_web_api.py` - A basic connectivity test
2. `test_handwriting_web_adapter.py` - A comprehensive test for the adapter and service

To run the tests:

```bash
# Basic API connectivity test
python test_myscript_web_api.py

# Full adapter test
python test_handwriting_web_adapter.py

# Skip file tests if rmscene is not installed
python test_handwriting_web_adapter.py --skip-file-test
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify your API credentials in the `.env` file
   - Check that the credentials have been loaded correctly

2. **Network Connectivity**:
   - The Web API requires internet access
   - Check your network connectivity and firewall settings

3. **Recognition Quality**:
   - Ensure stroke data is properly formatted
   - Try different content types (Text, Math, Diagram) if appropriate
   - Check that language settings match your handwriting

### Logging

To enable detailed logging for debugging:

```bash
# Add to your .env file
LOG_LEVEL=DEBUG
```

## API Reference

### HandwritingRecognitionService

The main service class for handwriting recognition.

```python
service = HandwritingRecognitionService(
    application_key=None,  # Optional: Override app key
    hmac_key=None,         # Optional: Override HMAC key
)
```

#### Key Methods

- `recognize_from_ink(ink_data=None, file_path=None, content_type=None, language="en_US")` - Process ink data or a file
- `recognize_multi_page_ink(page_files, language="en_US")` - Process multiple pages with cross-page context
- `extract_strokes(rm_file_path)` - Extract strokes from a .rm file
- `convert_to_iink_format(strokes)` - Convert strokes to the format needed for recognition
- `recognize_handwriting(iink_data, content_type="Text", language="en_US")` - Perform recognition on formatted data

## Further Reading

- [MyScript Developer Documentation](https://developer.myscript.com/docs)
- [Detailed Web API Integration Guide](./docs/myscript_web_api_integration.md)
- [InkLink Documentation](./README.md)