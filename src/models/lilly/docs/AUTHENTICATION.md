# Lilly Authentication System

This document provides instructions for setting up and using the Lilly authentication system for accessing Proton Mail, Proton Calendar, and Google Drive services.

## Overview

The Lilly authentication system allows secure storage and management of credentials for various services. It provides:

- Encrypted credential storage with a master password
- Command-line interfaces for authentication
- Environment variable support for automated setup
- Integration with the Lilly adapter classes

## Prerequisites

### Proton Bridge

To use Proton Mail and Proton Calendar, you need to install and configure Proton Bridge:

1. Download Proton Bridge from [proton.me/mail/bridge](https://proton.me/mail/bridge)
2. Install and log in with your Proton account
3. Configure Bridge to run in the background
4. Note the IMAP, SMTP, and CalDAV ports (typically 1143, 1025, and 8443)

### Google API Credentials

To use Google Drive, you need to create OAuth credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials (Desktop application type)
5. Note your Client ID and Client Secret

## Configuration

### Environment Variables

The authentication system can be configured using environment variables:

```bash
# Master password for credential encryption
export LILLY_MASTER_PASSWORD="your-secure-password"

# Credential storage location (optional)
export LILLY_CREDENTIAL_STORAGE_DIR="/path/to/credentials"

# Proton Bridge settings
export LILLY_PROTON_BRIDGE_HOST="127.0.0.1"
export LILLY_PROTON_BRIDGE_IMAP_PORT=1143
export LILLY_PROTON_BRIDGE_SMTP_PORT=1025
export LILLY_PROTON_BRIDGE_CALDAV_PORT=8443

# Proton Mail credentials (optional)
export LILLY_PROTON_MAIL_USERNAME="your-email@proton.me"
export LILLY_PROTON_MAIL_PASSWORD="your-password"

# Proton Calendar credentials (optional)
export LILLY_PROTON_CALENDAR_USERNAME="your-email@proton.me"
export LILLY_PROTON_CALENDAR_PASSWORD="your-password"

# Google OAuth settings
export LILLY_GOOGLE_CLIENT_ID="your-client-id"
export LILLY_GOOGLE_CLIENT_SECRET="your-client-secret"
export LILLY_GOOGLE_REDIRECT_URI="http://localhost:8080/oauth2callback"
```

### .env File

Alternatively, you can create a `.env` file in the project root or at `~/lilly/.env`:

```
LILLY_MASTER_PASSWORD=your-secure-password
LILLY_PROTON_MAIL_USERNAME=your-email@proton.me
LILLY_PROTON_MAIL_PASSWORD=your-password
LILLY_GOOGLE_CLIENT_ID=your-client-id
LILLY_GOOGLE_CLIENT_SECRET=your-client-secret
```

## Command-Line Interface

### Set Master Password

Before authenticating with any service, set a master password to encrypt your credentials:

```bash
./lilly_auth.py set-master-password
```

### Authenticate with Proton Mail

```bash
# With command-line arguments
./lilly_auth.py proton mail --username your-email@proton.me --password your-password

# With environment variables or interactive prompts
./lilly_auth.py proton mail
```

### Authenticate with Proton Calendar

```bash
# With command-line arguments
./lilly_auth.py proton calendar --username your-email@proton.me --password your-password

# With environment variables or interactive prompts
./lilly_auth.py proton calendar
```

### Authenticate with Google Drive

```bash
# With command-line arguments
./lilly_auth.py google-drive --client-id your-client-id --client-secret your-client-secret

# With environment variables or interactive prompts
./lilly_auth.py google-drive
```

This will open a browser window for Google authentication. After granting access, the browser will redirect to localhost and the credentials will be saved.

### List Authenticated Services

```bash
./lilly_auth.py list
```

### Logout from a Service

```bash
./lilly_auth.py logout proton_mail
./lilly_auth.py logout proton_calendar
./lilly_auth.py logout google_drive
```

## Security Considerations

- The master password is used to derive an encryption key for storing credentials
- Credentials are stored in encrypted files in `~/.lilly/credentials` by default
- Never share your master password or credential files
- Set appropriate file permissions on the credential directory
- Consider using a password manager for generating and storing your master password

## Programmatic Usage

To use the authentication system in your code:

```python
from lilly.auth.credential_manager import CredentialManager
from lilly.auth.authentication import AuthenticationProvider, SERVICE_PROTON_MAIL

# Create credential manager and authentication provider
credential_manager = CredentialManager()
auth_provider = AuthenticationProvider(credential_manager)

# Get credentials for a service
proton_mail_auth = auth_provider.get_authenticator(SERVICE_PROTON_MAIL)
credentials = proton_mail_auth.get_credentials()

if credentials:
    print(f"Authenticated as {credentials['username']}")
else:
    print("Not authenticated with Proton Mail")
```

## Troubleshooting

### Proton Bridge Connection Issues

If you encounter connection issues with Proton Bridge:

1. Ensure Proton Bridge is running
2. Verify the IMAP, SMTP, and CalDAV ports in Proton Bridge settings
3. Try restarting Proton Bridge
4. Ensure your username and password are correct

### Google Authentication Issues

If you encounter issues with Google authentication:

1. Verify your OAuth credentials are correct
2. Ensure redirect URI matches the one in your Google Cloud Console
3. Check that you have enabled the Google Drive API
4. Try clearing your browser cookies and cache

### Credential Encryption Issues

If you encounter issues with credential encryption:

1. Ensure you're using the correct master password
2. Check file permissions on the credential directory
3. Try setting a new master password with `set-master-password`