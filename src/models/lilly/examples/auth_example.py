#!/usr/bin/env python3
"""
Example usage of the Lilly authentication system.

This script demonstrates how to authenticate with Proton Mail, Proton Calendar,
and Google Drive using the Lilly authentication system.
"""

import getpass
import os
import sys

# Add the project root to Python path
sys.path.insert(
    0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

from lilly.auth.authentication import (  # noqa: E402
    SERVICE_GOOGLE_DRIVE,
    SERVICE_PROTON_MAIL,
    AuthenticationError,
    AuthenticationProvider,
)
from lilly.auth.config import load_dotenv  # noqa: E402
from lilly.auth.credential_manager import CredentialManager  # noqa: E402


def main():
    """Run authentication examples."""
    # Load environment variables from .env file
    load_dotenv()

    # Create credential manager and authentication provider
    credential_manager = CredentialManager()
    auth_provider = AuthenticationProvider(credential_manager)

    # Show authenticated services
    print("Checking authenticated services...")
    services = auth_provider.list_authenticated_services()
    if services:
        print(f"Authenticated services: {', '.join(services)}")
    else:
        print("No authenticated services found")

    # Example: Authenticate with Proton Mail
    if SERVICE_PROTON_MAIL not in services:
        print("\nProton Mail Authentication Example:")
        try:
            username = input("Enter Proton Mail username: ")
            password = getpass.getpass("Enter Proton Mail password: ")

            authenticator = auth_provider.get_authenticator(SERVICE_PROTON_MAIL)
            authenticator.authenticate(username=username, password=password)
            print("Successfully authenticated with Proton Mail")
        except AuthenticationError as e:
            print(f"Authentication failed: {e}")
    else:
        print("\nAlready authenticated with Proton Mail")
        proton_mail_auth = auth_provider.get_authenticator(SERVICE_PROTON_MAIL)
        credentials = proton_mail_auth.get_credentials()
        print(f"Authenticated as {credentials['username']}")

    # Example: Authenticate with Google Drive
    if SERVICE_GOOGLE_DRIVE not in services:
        print("\nGoogle Drive Authentication Example:")
        print("Note: This will open a browser window for Google authentication")
        try:
            client_id = input("Enter Google Client ID: ")
            client_secret = input("Enter Google Client Secret: ")

            if not client_id or not client_secret:
                print("Skipping Google Drive authentication (missing credentials)")
            else:
                authenticator = auth_provider.get_authenticator(SERVICE_GOOGLE_DRIVE)
                authenticator.authenticate(
                    client_id=client_id, client_secret=client_secret
                )
                print("Successfully authenticated with Google Drive")
        except AuthenticationError as e:
            print(f"Authentication failed: {e}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("\nAlready authenticated with Google Drive")
        google_drive_auth = auth_provider.get_authenticator(SERVICE_GOOGLE_DRIVE)
        credentials = google_drive_auth.get_credentials()
        print(f"Google Drive authentication is valid")

    # Show final authenticated services
    print("\nUpdated authenticated services list:")
    services = auth_provider.list_authenticated_services()
    if services:
        print(f"Authenticated services: {', '.join(services)}")
    else:
        print("No authenticated services found")


if __name__ == "__main__":
    main()
