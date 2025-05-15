"""
Configuration module for Lilly authentication.

This module provides configuration settings for the authentication system,
with support for environment variables for easy configuration in different environments.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

# Base configuration dictionary
AUTH_CONFIG = {
    # Credential storage
    "CREDENTIAL_STORAGE_DIR": os.environ.get(
        "LILLY_CREDENTIAL_STORAGE_DIR", str(Path.home() / ".lilly" / "credentials")
    ),
    "MASTER_PASSWORD": os.environ.get("LILLY_MASTER_PASSWORD", None),
    "CREDENTIAL_SALT": os.environ.get("LILLY_CREDENTIAL_SALT", None),
    # Proton Bridge settings
    "PROTON_BRIDGE_HOST": os.environ.get("LILLY_PROTON_BRIDGE_HOST", "127.0.0.1"),
    "PROTON_BRIDGE_IMAP_PORT": int(
        os.environ.get("LILLY_PROTON_BRIDGE_IMAP_PORT", 1143)
    ),
    "PROTON_BRIDGE_SMTP_PORT": int(
        os.environ.get("LILLY_PROTON_BRIDGE_SMTP_PORT", 1025)
    ),
    "PROTON_BRIDGE_CALDAV_PORT": int(
        os.environ.get("LILLY_PROTON_BRIDGE_CALDAV_PORT", 8443)
    ),
    # Proton Mail settings (can be set in .env file)
    "PROTON_MAIL_USERNAME": os.environ.get("LILLY_PROTON_MAIL_USERNAME", None),
    "PROTON_MAIL_PASSWORD": os.environ.get("LILLY_PROTON_MAIL_PASSWORD", None),
    # Proton Calendar settings (can be set in .env file)
    "PROTON_CALENDAR_USERNAME": os.environ.get("LILLY_PROTON_CALENDAR_USERNAME", None),
    "PROTON_CALENDAR_PASSWORD": os.environ.get("LILLY_PROTON_CALENDAR_PASSWORD", None),
    # Google OAuth settings (can be set in .env file)
    "GOOGLE_CLIENT_ID": os.environ.get("LILLY_GOOGLE_CLIENT_ID", None),
    "GOOGLE_CLIENT_SECRET": os.environ.get("LILLY_GOOGLE_CLIENT_SECRET", None),
    "GOOGLE_REDIRECT_URI": os.environ.get(
        "LILLY_GOOGLE_REDIRECT_URI", "http://localhost:8080/oauth2callback"
    ),
    # OAuth server settings
    "OAUTH_SERVER_HOST": os.environ.get("LILLY_OAUTH_SERVER_HOST", "localhost"),
    "OAUTH_SERVER_PORT": int(os.environ.get("LILLY_OAUTH_SERVER_PORT", 8080)),
    # Google API scopes
    "GOOGLE_DRIVE_SCOPES": [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/drive.appdata",
        "https://www.googleapis.com/auth/drive.activity.readonly",
    ],
}


def load_dotenv(dotenv_path: Optional[str] = None) -> None:
    """
    Load environment variables from .env file.

    Args:
        dotenv_path: Path to .env file
    """
    try:
        from dotenv import load_dotenv as _load_dotenv

        if dotenv_path:
            _load_dotenv(dotenv_path)
        else:
            # Try to find .env file in current directory or ~/lilly/.env
            local_env = Path(".env")
            lilly_env = Path.home() / "lilly" / ".env"

            if local_env.exists():
                _load_dotenv(local_env)
            elif lilly_env.exists():
                _load_dotenv(lilly_env)

        # Reload configuration from environment variables
        _reload_config_from_env()

    except ImportError:
        print(
            "Warning: python-dotenv not installed. Environment variables will not be loaded from .env file."
        )


def _reload_config_from_env() -> None:
    """Reload configuration values from environment variables."""
    # Update all config values from environment variables
    for key in AUTH_CONFIG:
        env_var = f"LILLY_{key}"
        if env_var in os.environ:
            # Convert to appropriate type based on default value
            if isinstance(AUTH_CONFIG[key], int):
                AUTH_CONFIG[key] = int(os.environ[env_var])
            elif isinstance(AUTH_CONFIG[key], bool):
                AUTH_CONFIG[key] = os.environ[env_var].lower() in (
                    "true",
                    "yes",
                    "1",
                    "t",
                    "y",
                )
            elif isinstance(AUTH_CONFIG[key], list):
                # Assume comma-separated list for list values
                AUTH_CONFIG[key] = os.environ[env_var].split(",")
            else:
                AUTH_CONFIG[key] = os.environ[env_var]


def get_config(key: str, default: Any = None) -> Any:
    """
    Get configuration value.

    Args:
        key: Configuration key
        default: Default value if not found

    Returns:
        Any: Configuration value
    """
    return AUTH_CONFIG.get(key, default)


def set_config(key: str, value: Any) -> None:
    """
    Set configuration value.

    Args:
        key: Configuration key
        value: Configuration value
    """
    AUTH_CONFIG[key] = value


# Try to load .env file if python-dotenv is installed
load_dotenv()
