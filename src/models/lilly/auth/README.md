# Lilly Authentication System

This directory contains the authentication system for Lilly service adapters. The system provides secure storage and management of credentials for accessing Proton Mail, Proton Calendar, and Google Drive.

## Components

- `credential_manager.py`: Secure storage and retrieval of service credentials
- `authentication.py`: Unified authentication flows for different services
- `config.py`: Configuration system with environment variable support
- `cli.py`: Command-line interface for authentication

## Usage

See the full documentation in `/lilly/docs/AUTHENTICATION.md` for detailed setup and usage instructions.

### Quick Start

```bash
# Set master password for credential encryption
./lilly_auth.py set-master-password

# Authenticate with Proton Mail
./lilly_auth.py proton mail

# Authenticate with Proton Calendar
./lilly_auth.py proton calendar

# Authenticate with Google Drive
./lilly_auth.py google-drive

# List authenticated services
./lilly_auth.py list

# Logout from a service
./lilly_auth.py logout proton_mail
```

## Security

Credentials are encrypted using Fernet symmetric encryption with a key derived from the master password using PBKDF2. The encrypted credentials are stored in `~/.lilly/credentials` by default.

## Environment Variables

The authentication system can be configured using environment variables or a `.env` file. See the documentation for details.