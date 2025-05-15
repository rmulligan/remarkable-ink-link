# MyScript Web API Integration

This document explains the integration of MyScript's Cloud API for handwriting recognition in the InkLink project.

## Overview

InkLink uses MyScript's Web API to provide handwriting recognition for reMarkable tablet notes. The implementation allows you to convert handwritten notes to text, enabling search, editing, and further AI processing.

## API Credentials

To use the MyScript Cloud API, you need the following credentials:

- **Application Key** - Used to identify your application
- **HMAC Key** - Used to sign requests for security

You can obtain these credentials from the [MyScript Developer Portal](https://developer.myscript.com/).

## Configuration

The integration can be configured using environment variables in your `.env` file:

```
# MyScript API credentials
MYSCRIPT_APP_KEY=your-application-key
MYSCRIPT_HMAC_KEY=your-hmac-key
```

## Architecture

The integration uses the following components:

1. `HandwritingWebAdapter` - Core adapter that communicates with the MyScript Cloud API
2. `HandwritingAdapter` - Wrapper that provides a consistent interface for the application
3. `HandwritingRecognitionService` - Service layer that orchestrates the recognition process

## API Details

The integration uses the following MyScript Cloud API endpoints:

- Main endpoint: `https://cloud.myscript.com/api/v4.0/iink/`
- Recognition endpoint: `recognize`

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

## Authentication

The integration uses HMAC-SHA512 signatures for API authentication:

1. The request payload is serialized to JSON
2. An HMAC-SHA512 signature is generated using the HMAC key
3. The signature is sent along with the application key in the request headers

## Content Types

The API supports various content types for recognition:

- **Text** - General handwritten text
- **Math** - Mathematical expressions and equations
- **Diagram** - Drawings, diagrams, and charts

## Testing

A test script is provided to verify the Web API integration:

```bash
# Run the test script
python test_handwriting_web_adapter.py

# Skip file processing test if rmscene is not installed
python test_handwriting_web_adapter.py --skip-file-test
```

## Error Handling

The adapter includes robust error handling for:

- Network connectivity issues
- API authentication errors
- Rate limiting and timeouts
- Malformed input data

All errors are logged through the standard logging system and returned as error objects.

## References

- [MyScript Cloud API Documentation](https://cloud.myscript.com/api/v4.0/iink/batch/api-docs)
- [MyScript Developer Portal](https://developer.myscript.com/)