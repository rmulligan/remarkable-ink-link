# MyScript API Reference

## HandwritingRecognitionService

The main service class for handwriting recognition.

```python
service = HandwritingRecognitionService(
    application_key=None,  # Optional: Override app key
    hmac_key=None,         # Optional: Override HMAC key
)
```

### Key Methods

- `recognize_from_ink(ink_data=None, file_path=None, content_type=None, language="en_US")` - Process ink data or a file
- `recognize_multi_page_ink(page_files, language="en_US")` - Process multiple pages with cross-page context
- `extract_strokes(rm_file_path)` - Extract strokes from a .rm file
- `convert_to_iink_format(strokes)` - Convert strokes to the format needed for recognition
- `recognize_handwriting(iink_data, content_type="Text", language="en_US")` - Perform recognition on formatted data

## Input Format

The API accepts handwriting data in the form of stroke points, with the following structure:

```json
{
  "contentType": "Text",
  "xDpi": 96,
  "yDpi": 96,
  "width": 1872,
  "height": 2404,
  "strokeGroups": [
    {
      "strokes": [
        {
          "id": "1",
          "x": [100, 200, 300],
          "y": [100, 150, 100],
          "p": [0.5, 0.7, 0.5],
          "t": [1614556800000, 1614556800100, 1614556800200]
        }
      ]
    }
  ],
  "lang": "en_US"
}
```

The adapter handles the conversion from reMarkable `.rm` files to this format.

## HandwritingWebAdapter

The core adapter that communicates with the MyScript Cloud API.

### Methods

- `authenticate()` - Prepares authentication headers for API requests
- `recognize_handwriting(data, content_type, language)` - Sends recognition request to the API
- `process_response(response)` - Processes and extracts the recognized text from API response

## Error Handling

The adapter includes robust error handling for:

- Network connectivity issues
- API authentication errors
- Rate limiting and timeouts
- Malformed input data

All errors are logged through the standard logging system and returned as error objects.

## Usage Example

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