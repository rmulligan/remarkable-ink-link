"""
Credential Manager for securely storing and retrieving service credentials.

This module provides a secure mechanism for storing credentials like API keys,
passwords, and tokens for various services used by Lilly.
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class CredentialManager:
    """Securely manage credentials for various services."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        master_password: Optional[str] = None,
        salt: Optional[bytes] = None,
    ):
        """
        Initialize the credential manager.

        Args:
            storage_dir: Directory to store encrypted credentials
            master_password: Password for encrypting credentials
            salt: Salt for key derivation
        """
        # Set storage directory with fallback to ~/.lilly/credentials
        self.storage_dir = (
            Path(storage_dir) if storage_dir else Path.home() / ".lilly" / "credentials"
        )
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Use either provided master password or from env var
        self._master_password = master_password or os.environ.get(
            "LILLY_MASTER_PASSWORD", None
        )
        if not self._master_password:
            logger.warning(
                "No master password provided. Falling back to default (INSECURE)."
            )
            self._master_password = "lilly_default_password_change_me"

        # Use either provided salt or from env var, or generate a new one
        salt_env = os.environ.get("LILLY_CREDENTIAL_SALT", None)
        if salt:
            self._salt = salt
        elif salt_env:
            self._salt = base64.b64decode(salt_env)
        else:
            # Create a default salt
            self._salt = b"lilly_secure_salt_change_me"
            logger.warning(
                "Using default salt. Consider setting LILLY_CREDENTIAL_SALT env var."
            )

        # Initialize encryption key
        self._init_key()

    def _init_key(self) -> None:
        """Initialize the encryption key from the master password."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._master_password.encode()))
        self._fernet = Fernet(key)

    def save_credentials(self, service_name: str, credentials: Dict[str, Any]) -> bool:
        """
        Save credentials for a service.

        Args:
            service_name: Name of the service (proton_mail, proton_calendar, google_drive)
            credentials: Dictionary of credentials to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert to JSON and encrypt
            data = json.dumps(credentials).encode()
            encrypted_data = self._fernet.encrypt(data)

            # Save to file
            file_path = self.storage_dir / f"{service_name}.enc"
            with open(file_path, "wb") as f:
                f.write(encrypted_data)

            logger.info(f"Credentials saved for {service_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving credentials for {service_name}: {e}")
            return False

    def get_credentials(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve credentials for a service.

        Args:
            service_name: Name of the service

        Returns:
            Dict or None: Credentials dictionary or None if not found/error
        """
        file_path = self.storage_dir / f"{service_name}.enc"
        if not file_path.exists():
            logger.warning(f"No credentials found for {service_name}")
            return None

        try:
            # Read encrypted data
            with open(file_path, "rb") as f:
                encrypted_data = f.read()

            # Decrypt and parse JSON
            decrypted_data = self._fernet.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())

            return credentials
        except Exception as e:
            logger.error(f"Error retrieving credentials for {service_name}: {e}")
            return None

    def delete_credentials(self, service_name: str) -> bool:
        """
        Delete credentials for a service.

        Args:
            service_name: Name of the service

        Returns:
            bool: True if successful, False otherwise
        """
        file_path = self.storage_dir / f"{service_name}.enc"
        if not file_path.exists():
            logger.warning(f"No credentials found for {service_name}")
            return False

        try:
            os.remove(file_path)
            logger.info(f"Credentials deleted for {service_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting credentials for {service_name}: {e}")
            return False

    def list_services(self) -> list:
        """
        List all services with stored credentials.

        Returns:
            list: List of service names
        """
        return [f.stem for f in self.storage_dir.glob("*.enc")]

    def rotate_master_password(self, new_password: str) -> bool:
        """
        Change the master password and re-encrypt all credentials.

        Args:
            new_password: New master password

        Returns:
            bool: True if successful, False otherwise
        """
        # Store all existing credentials
        all_services = self.list_services()
        all_credentials = {}

        for service in all_services:
            creds = self.get_credentials(service)
            if creds:
                all_credentials[service] = creds

        # Update master password and regenerate key
        self._master_password = new_password
        self._init_key()

        # Re-encrypt all credentials
        success = True
        for service, creds in all_credentials.items():
            if not self.save_credentials(service, creds):
                success = False
                logger.error(f"Failed to re-encrypt credentials for {service}")

        return success
