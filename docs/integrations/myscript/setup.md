# MyScript Integration Setup

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

## Authentication

The integration uses HMAC-SHA512 signatures for API authentication:

1. The request payload is serialized to JSON
2. An HMAC-SHA512 signature is generated using the HMAC key
3. The signature is sent along with the application key in the request headers

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