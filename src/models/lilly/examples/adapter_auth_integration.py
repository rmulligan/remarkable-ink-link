#!/usr/bin/env python3
"""
Example integration of authentication system with service adapters.

This script demonstrates how to integrate the Lilly authentication system
with the Proton Mail, Proton Calendar, and Google Drive adapters.
"""

import os
import sys
import logging

# Add the project root to Python path
sys.path.insert(
    0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

from lilly.auth.credential_manager import CredentialManager  # noqa: E402
from lilly.auth.authentication import (  # noqa: E402
    AuthenticationProvider,
    SERVICE_PROTON_MAIL,
    SERVICE_PROTON_CALENDAR,
    SERVICE_GOOGLE_DRIVE,
)
from lilly.auth.config import load_dotenv  # noqa: E402

# Import adapters
from lilly.adapters.proton_mail_adapter import ProtonMailAdapter  # noqa: E402
from lilly.adapters.proton_calendar_adapter import ProtonCalendarAdapter  # noqa: E402
from lilly.adapters.google_drive_adapter import GoogleDriveAdapter  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_authenticated_adapters():
    """Create authenticated service adapters."""
    # Load environment variables
    load_dotenv()

    # Create credential manager and authentication provider
    credential_manager = CredentialManager()
    auth_provider = AuthenticationProvider(credential_manager)

    # Check which services are authenticated
    authenticated_services = auth_provider.list_authenticated_services()
    logger.info(f"Authenticated services: {authenticated_services}")

    adapters = {}

    # Create Proton Mail adapter if authenticated
    if SERVICE_PROTON_MAIL in authenticated_services:
        proton_mail_auth = auth_provider.get_authenticator(SERVICE_PROTON_MAIL)
        credentials = proton_mail_auth.get_credentials()

        if credentials:
            logger.info(f"Creating Proton Mail adapter for {credentials['username']}")
            adapters["proton_mail"] = ProtonMailAdapter(
                username=credentials["username"],
                password=credentials["password"],
                bridge_host=credentials.get("bridge_host", "127.0.0.1"),
                imap_port=credentials.get("imap_port", 1143),
                smtp_port=credentials.get("smtp_port", 1025),
            )

    # Create Proton Calendar adapter if authenticated
    if SERVICE_PROTON_CALENDAR in authenticated_services:
        proton_calendar_auth = auth_provider.get_authenticator(SERVICE_PROTON_CALENDAR)
        credentials = proton_calendar_auth.get_credentials()

        if credentials:
            logger.info(
                f"Creating Proton Calendar adapter for {credentials['username']}"
            )
            adapters["proton_calendar"] = ProtonCalendarAdapter(
                username=credentials["username"],
                password=credentials["password"],
                bridge_host=credentials.get("bridge_host", "127.0.0.1"),
                caldav_port=credentials.get("caldav_port", 8443),
            )

    # Create Google Drive adapter if authenticated
    if SERVICE_GOOGLE_DRIVE in authenticated_services:
        google_drive_auth = auth_provider.get_authenticator(SERVICE_GOOGLE_DRIVE)
        credentials = google_drive_auth.get_credentials()

        if credentials:
            logger.info("Creating Google Drive adapter")
            adapters["google_drive"] = GoogleDriveAdapter(credentials=credentials)

    return adapters


def main():
    """Main function to demonstrate adapter authentication integration."""
    print("Creating authenticated service adapters...")
    adapters = create_authenticated_adapters()

    if not adapters:
        print("No authenticated services found.")
        print("Please authenticate first using the lilly_auth.py script.")
        return

    print(f"Successfully created {len(adapters)} authenticated adapters:")
    for service_name in adapters:
        print(f"  - {service_name}")

    # Example: List emails with Proton Mail adapter
    if "proton_mail" in adapters:
        print("\nProton Mail Example:")
        try:
            print("Connecting to Proton Mail...")
            adapters["proton_mail"].connect()

            print("Listing mailboxes...")
            mailboxes = adapters["proton_mail"].list_mailboxes()
            print(f"Available mailboxes: {', '.join(mailboxes)}")

            inbox = adapters["proton_mail"].get_mailbox("INBOX")
            print(
                f"Inbox has {inbox.total_messages} messages, {inbox.unread_messages} unread"
            )

            print("Disconnecting...")
            adapters["proton_mail"].disconnect()
        except Exception as e:
            print(f"Error: {e}")

    # Example: List events with Proton Calendar adapter
    if "proton_calendar" in adapters:
        print("\nProton Calendar Example:")
        try:
            print("Connecting to Proton Calendar...")
            adapters["proton_calendar"].connect()

            print("Listing calendars...")
            calendars = adapters["proton_calendar"].list_calendars()
            print(f"Found {len(calendars)} calendars")

            if calendars:
                calendar_id = calendars[0].id
                print(f"Listing events from calendar: {calendars[0].name}")
                events = adapters["proton_calendar"].get_events(
                    calendar_id,
                    start_date=datetime.date.today(),
                    end_date=datetime.date.today() + datetime.timedelta(days=7),
                )
                print(f"Found {len(events)} events in the next 7 days")

            print("Disconnecting...")
            adapters["proton_calendar"].disconnect()
        except Exception as e:
            print(f"Error: {e}")

    # Example: List files with Google Drive adapter
    if "google_drive" in adapters:
        print("\nGoogle Drive Example:")
        try:
            print("Listing files in Google Drive...")
            files = adapters["google_drive"].list_files(max_results=10)
            print(f"Found {len(files)} files")

            if files:
                print("Recent files:")
                for file in files[:5]:
                    print(f"  - {file.name} ({file.id})")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
