"""
CLI commands for Lilly authentication.

This module provides command-line interfaces for authenticating with various services
used by Lilly, including Proton Mail, Proton Calendar, and Google Drive.
"""

import os
import click
import getpass
from typing import Optional

from lilly.auth.credential_manager import CredentialManager
from lilly.auth.authentication import (
    AuthenticationProvider, 
    SERVICE_PROTON_MAIL,
    SERVICE_PROTON_CALENDAR,
    SERVICE_GOOGLE_DRIVE,
    AuthenticationError
)
from lilly.auth.config import get_config, load_dotenv

# Create authentication provider
credential_manager = CredentialManager()
auth_provider = AuthenticationProvider(credential_manager)

@click.group()
def auth():
    """Authentication commands for Lilly services."""
    # Try to load environment variables from .env file
    load_dotenv()

@auth.command('list')
def list_services():
    """List all authenticated services."""
    services = auth_provider.list_authenticated_services()
    
    if not services:
        click.echo("No authenticated services found.")
        return
    
    click.echo("Authenticated services:")
    for service in services:
        click.echo(f"  - {service}")

@auth.command('logout')
@click.argument('service')
def logout(service):
    """
    Remove credentials for a service.
    
    SERVICE can be one of: proton_mail, proton_calendar, google_drive
    """
    try:
        authenticator = auth_provider.get_authenticator(service)
        if authenticator.logout():
            click.echo(f"Successfully logged out from {service}")
        else:
            click.echo(f"No credentials found for {service}")
    except ValueError as e:
        click.echo(f"Error: {str(e)}")
        click.echo("Valid services: proton_mail, proton_calendar, google_drive")

@auth.group('proton')
def proton():
    """Proton service authentication commands."""
    pass

@proton.command('mail')
@click.option('--username', '-u', help='Proton Mail username/email')
@click.option('--password', '-p', help='Proton Mail password')
@click.option('--host', help='Proton Bridge host', default=None)
@click.option('--imap-port', type=int, help='Proton Bridge IMAP port', default=None)
@click.option('--smtp-port', type=int, help='Proton Bridge SMTP port', default=None)
def proton_mail(username, password, host, imap_port, smtp_port):
    """Authenticate with Proton Mail via Proton Bridge."""
    # Use environment variables if not provided
    username = username or get_config('PROTON_MAIL_USERNAME')
    password = password or get_config('PROTON_MAIL_PASSWORD')
    host = host or get_config('PROTON_BRIDGE_HOST')
    imap_port = imap_port or get_config('PROTON_BRIDGE_IMAP_PORT')
    smtp_port = smtp_port or get_config('PROTON_BRIDGE_SMTP_PORT')
    
    # Prompt for missing credentials
    if not username:
        username = click.prompt('Enter Proton Mail username/email')
    
    if not password:
        password = getpass.getpass('Enter Proton Mail password: ')
    
    try:
        authenticator = auth_provider.get_authenticator(SERVICE_PROTON_MAIL)
        authenticator.authenticate(
            username=username,
            password=password,
            bridge_host=host,
            imap_port=imap_port,
            smtp_port=smtp_port
        )
        click.echo(f"Successfully authenticated with Proton Mail")
    except AuthenticationError as e:
        click.echo(f"Authentication failed: {str(e)}")

@proton.command('calendar')
@click.option('--username', '-u', help='Proton Calendar username/email')
@click.option('--password', '-p', help='Proton Calendar password')
@click.option('--host', help='Proton Bridge host', default=None)
@click.option('--caldav-port', type=int, help='Proton Bridge CalDAV port', default=None)
def proton_calendar(username, password, host, caldav_port):
    """Authenticate with Proton Calendar via Proton Bridge."""
    # Use environment variables if not provided
    username = username or get_config('PROTON_CALENDAR_USERNAME')
    password = password or get_config('PROTON_CALENDAR_PASSWORD')
    host = host or get_config('PROTON_BRIDGE_HOST')
    caldav_port = caldav_port or get_config('PROTON_BRIDGE_CALDAV_PORT')
    
    # Prompt for missing credentials
    if not username:
        username = click.prompt('Enter Proton Calendar username/email')
    
    if not password:
        password = getpass.getpass('Enter Proton Calendar password: ')
    
    try:
        authenticator = auth_provider.get_authenticator(SERVICE_PROTON_CALENDAR)
        authenticator.authenticate(
            username=username,
            password=password,
            bridge_host=host,
            caldav_port=caldav_port
        )
        click.echo(f"Successfully authenticated with Proton Calendar")
    except AuthenticationError as e:
        click.echo(f"Authentication failed: {str(e)}")

@auth.command('google-drive')
@click.option('--client-id', help='Google API client ID')
@click.option('--client-secret', help='Google API client secret')
@click.option('--redirect-uri', help='OAuth redirect URI')
def google_drive(client_id, client_secret, redirect_uri):
    """Authenticate with Google Drive."""
    # Use environment variables if not provided
    client_id = client_id or get_config('GOOGLE_CLIENT_ID')
    client_secret = client_secret or get_config('GOOGLE_CLIENT_SECRET')
    redirect_uri = redirect_uri or get_config('GOOGLE_REDIRECT_URI')
    
    # Prompt for missing credentials
    if not client_id:
        client_id = click.prompt('Enter Google API client ID')
    
    if not client_secret:
        client_secret = click.prompt('Enter Google API client secret')
    
    try:
        authenticator = auth_provider.get_authenticator(SERVICE_GOOGLE_DRIVE)
        authenticator.authenticate(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=get_config('GOOGLE_DRIVE_SCOPES')
        )
        click.echo(f"Successfully authenticated with Google Drive")
    except AuthenticationError as e:
        click.echo(f"Authentication failed: {str(e)}")
    except Exception as e:
        click.echo(f"Error: {str(e)}")

@auth.command('set-master-password')
def set_master_password():
    """Set or change the master password for credential encryption."""
    try:
        # Get current services and credentials
        services = credential_manager.list_services()
        if services:
            click.echo("Warning: Changing the master password will re-encrypt all existing credentials.")
            if not click.confirm("Continue?"):
                return
        
        # Get and confirm new password
        new_password = getpass.getpass('Enter new master password: ')
        confirm_password = getpass.getpass('Confirm new master password: ')
        
        if new_password != confirm_password:
            click.echo("Error: Passwords do not match")
            return
        
        if not new_password:
            click.echo("Error: Password cannot be empty")
            return
        
        # Update password
        if services:
            # Re-encrypt all credentials
            if credential_manager.rotate_master_password(new_password):
                click.echo("Master password updated successfully")
            else:
                click.echo("Failed to update master password")
        else:
            # No existing credentials, just set the new password and save it
            credential_manager._master_password = new_password
            credential_manager._init_key()
            click.echo("Master password set successfully")
        
        # Advise on environment variable
        click.echo("\nConsider setting the LILLY_MASTER_PASSWORD environment variable:")
        click.echo(f"  export LILLY_MASTER_PASSWORD='{new_password}'")
        click.echo("Or add it to your .env file")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}")

if __name__ == '__main__':
    auth()