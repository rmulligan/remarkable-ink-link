#!/usr/bin/env python3
"""
Proton Mail Adapter for Lilly

This adapter provides an interface to access and interact with Proton Mail
through the Proton Bridge IMAP/SMTP service.
"""

import os
import email
import imaplib
import smtplib
import logging
import re
import json
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Email message data structure."""

    message_id: str
    uid: int
    subject: str
    sender: str
    recipients: List[str]
    date: datetime.datetime
    body_text: str
    body_html: Optional[str] = None
    cc: List[str] = None
    bcc: List[str] = None
    attachments: List[Dict[str, Any]] = None
    folder: Optional[str] = None
    flags: List[str] = None
    labels: List[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailMessage":
        """Create an EmailMessage from a dictionary."""
        return cls(
            message_id=data.get("message_id", ""),
            uid=data.get("uid", 0),
            subject=data.get("subject", ""),
            sender=data.get("sender", ""),
            recipients=data.get("recipients", []),
            date=data.get("date", datetime.datetime.now()),
            body_text=data.get("body_text", ""),
            body_html=data.get("body_html"),
            cc=data.get("cc", []),
            bcc=data.get("bcc", []),
            attachments=data.get("attachments", []),
            folder=data.get("folder"),
            flags=data.get("flags", []),
            labels=data.get("labels", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "uid": self.uid,
            "subject": self.subject,
            "sender": self.sender,
            "recipients": self.recipients,
            "date": self.date.isoformat() if self.date else None,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "cc": self.cc,
            "bcc": self.bcc,
            "attachments": self.attachments,
            "folder": self.folder,
            "flags": self.flags,
            "labels": self.labels,
        }

    def __str__(self) -> str:
        """String representation of email."""
        return f"Subject: {self.subject}\nFrom: {self.sender}\nDate: {self.date}\n\n{self.body_text[:100]}..."


class ProtonMailAdapter:
    """
    Adapter for interacting with Proton Mail via Proton Bridge.

    This adapter uses IMAP/SMTP to communicate with Proton Mail through the local
    Proton Bridge service, which must be installed and configured.
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        imap_host: str = "127.0.0.1",
        imap_port: int = 1143,
        smtp_host: str = "127.0.0.1",
        smtp_port: int = 1025,
        use_ssl: bool = False,
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize the Proton Mail adapter.

        Args:
            username: Email username (default: from PROTON_MAIL_USERNAME env var)
            password: Email password (default: from PROTON_MAIL_PASSWORD env var)
            imap_host: IMAP server host (default: localhost for Proton Bridge)
            imap_port: IMAP server port (default: 1143 for Proton Bridge)
            smtp_host: SMTP server host (default: localhost for Proton Bridge)
            smtp_port: SMTP server port (default: 1025 for Proton Bridge)
            use_ssl: Whether to use SSL for connections
            cache_dir: Directory to cache email data
        """
        # Get credentials from environment variables if not provided
        self.username = username or os.environ.get("PROTON_MAIL_USERNAME")
        self.password = password or os.environ.get("PROTON_MAIL_PASSWORD")

        if not self.username or not self.password:
            logger.warning(
                "Proton Mail credentials not provided. Some functionality may be limited."
            )

        # Configure connection settings
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.use_ssl = use_ssl

        # Caching settings
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

        # Initialize connections as None (lazy initialization)
        self.imap = None
        self.smtp = None

        logger.info(
            f"Initialized ProtonMailAdapter for {self.username} using Proton Bridge"
        )

    def _connect_imap(self) -> bool:
        """
        Connect to the IMAP server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.use_ssl:
                self.imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                self.imap = imaplib.IMAP4(self.imap_host, self.imap_port)

            self.imap.login(self.username, self.password)
            logger.info(f"Successfully connected to IMAP server for {self.username}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {str(e)}")
            self.imap = None
            return False

    def _connect_smtp(self) -> bool:
        """
        Connect to the SMTP server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.use_ssl:
                self.smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                self.smtp = smtplib.SMTP(self.smtp_host, self.smtp_port)

            self.smtp.login(self.username, self.password)
            logger.info(f"Successfully connected to SMTP server for {self.username}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            self.smtp = None
            return False

    def _ensure_imap_connected(self) -> bool:
        """
        Ensure IMAP connection is established.

        Returns:
            True if connected, False otherwise
        """
        if self.imap is None:
            return self._connect_imap()

        try:
            # Check connection by sending a NOOP command
            status, response = self.imap.noop()
            if status != "OK":
                logger.info("IMAP connection lost. Reconnecting...")
                self.imap = None
                return self._connect_imap()
            return True
        except Exception:
            logger.info("IMAP connection error. Reconnecting...")
            self.imap = None
            return self._connect_imap()

    def _ensure_smtp_connected(self) -> bool:
        """
        Ensure SMTP connection is established.

        Returns:
            True if connected, False otherwise
        """
        if self.smtp is None:
            return self._connect_smtp()

        try:
            # Check connection by sending a NOOP command
            status = self.smtp.noop()[0]
            if status != 250:
                logger.info("SMTP connection lost. Reconnecting...")
                self.smtp = None
                return self._connect_smtp()
            return True
        except Exception:
            logger.info("SMTP connection error. Reconnecting...")
            self.smtp = None
            return self._connect_smtp()

    def list_folders(self) -> Tuple[bool, Union[List[str], str]]:
        """
        List all mail folders.

        Returns:
            Tuple of (success, folders/error_message)
        """
        if not self._ensure_imap_connected():
            return False, "Failed to connect to IMAP server"

        try:
            status, folder_list = self.imap.list()

            if status != "OK":
                return False, f"Failed to list folders: {folder_list}"

            folders = []
            for folder_data in folder_list:
                # Parse the folder name from the response
                folder_name = folder_data.decode().split('"/" ')[-1].strip('"')
                folders.append(folder_name)

            return True, folders
        except Exception as e:
            logger.error(f"Error listing folders: {str(e)}")
            return False, f"Error listing folders: {str(e)}"

    def select_folder(self, folder: str) -> Tuple[bool, Union[int, str]]:
        """
        Select a mail folder.

        Args:
            folder: Folder name to select

        Returns:
            Tuple of (success, message_count/error_message)
        """
        if not self._ensure_imap_connected():
            return False, "Failed to connect to IMAP server"

        try:
            status, data = self.imap.select(folder)

            if status != "OK":
                return False, f"Failed to select folder {folder}: {data}"

            # Return the message count
            return True, int(data[0])
        except Exception as e:
            logger.error(f"Error selecting folder {folder}: {str(e)}")
            return False, f"Error selecting folder {folder}: {str(e)}"

    def search_emails(
        self, criteria: str = "ALL", folder: str = "INBOX", limit: int = 50
    ) -> Tuple[bool, Union[List[int], str]]:
        """
        Search for emails matching criteria.

        Args:
            criteria: IMAP search criteria (default: "ALL")
            folder: Folder to search in (default: "INBOX")
            limit: Maximum number of results to return

        Returns:
            Tuple of (success, message_uids/error_message)
        """
        if not self._ensure_imap_connected():
            return False, "Failed to connect to IMAP server"

        try:
            # Select the folder
            status, _ = self.select_folder(folder)
            if not status:
                return False, f"Failed to select folder {folder}"

            # Search for messages
            status, data = self.imap.search(None, criteria)

            if status != "OK":
                return False, f"Failed to search folder {folder}: {data}"

            # Get message numbers from the response
            message_nums = data[0].split()

            # Limit the number of results
            if limit and len(message_nums) > limit:
                message_nums = message_nums[-limit:]

            # Convert to integers
            message_uids = [int(num) for num in message_nums]

            return True, message_uids
        except Exception as e:
            logger.error(f"Error searching folder {folder}: {str(e)}")
            return False, f"Error searching folder {folder}: {str(e)}"

    def fetch_email(
        self, uid: int, folder: str = "INBOX"
    ) -> Tuple[bool, Union[EmailMessage, str]]:
        """
        Fetch a specific email by UID.

        Args:
            uid: Email UID to fetch
            folder: Folder containing the email (default: "INBOX")

        Returns:
            Tuple of (success, email_message/error_message)
        """
        if not self._ensure_imap_connected():
            return False, "Failed to connect to IMAP server"

        try:
            # Select the folder
            status, _ = self.select_folder(folder)
            if not status:
                return False, f"Failed to select folder {folder}"

            # Fetch the email
            status, data = self.imap.fetch(str(uid), "(RFC822)")

            if status != "OK":
                return False, f"Failed to fetch email {uid}: {data}"

            # Parse the email
            raw_email = data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # Extract email details
            parsed_email = self._parse_email(email_message, uid, folder)

            return True, parsed_email
        except Exception as e:
            logger.error(f"Error fetching email {uid} from {folder}: {str(e)}")
            return False, f"Error fetching email {uid}: {str(e)}"

    def _parse_email(
        self, email_message: email.message.Message, uid: int, folder: str
    ) -> EmailMessage:
        """
        Parse an email message into a structured format.

        Args:
            email_message: Raw email message
            uid: Email UID
            folder: Folder containing the email

        Returns:
            Structured EmailMessage object
        """
        # Extract message ID
        message_id = email_message.get("Message-ID", "")

        # Decode subject
        subject = ""
        subject_header = email_message.get("Subject", "")
        if subject_header:
            subject_parts = decode_header(subject_header)
            subject = "".join(
                [
                    part.decode(charset or "utf-8") if isinstance(part, bytes) else part
                    for part, charset in subject_parts
                ]
            )

        # Extract sender
        sender = email_message.get("From", "")

        # Extract recipients
        recipients = self._parse_address_list(email_message.get("To", ""))
        cc = self._parse_address_list(email_message.get("Cc", ""))
        bcc = self._parse_address_list(email_message.get("Bcc", ""))

        # Parse date
        date_str = email_message.get("Date", "")
        date = None
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except Exception:
                date = datetime.datetime.now()

        # Extract body content
        body_text = ""
        body_html = None
        attachments = []

        # Process each part of the email
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip multipart container
                if content_type == "multipart/alternative":
                    continue

                # Handle attachments
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        attachments.append(
                            {
                                "filename": filename,
                                "content_type": content_type,
                                "size": len(part.get_payload(decode=True)),
                                "data": None,  # Don't include the data by default to save memory
                            }
                        )
                    continue

                # Handle text content
                if content_type == "text/plain":
                    body_text += self._decode_part(part)
                elif content_type == "text/html":
                    body_html = self._decode_part(part)
        else:
            # Handle single part email
            content_type = email_message.get_content_type()
            if content_type == "text/plain":
                body_text = self._decode_part(email_message)
            elif content_type == "text/html":
                body_html = self._decode_part(email_message)

        # Create structured email object
        return EmailMessage(
            message_id=message_id,
            uid=uid,
            subject=subject,
            sender=sender,
            recipients=recipients,
            date=date,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
            folder=folder,
            flags=[],  # Would need a separate fetch to get flags
            labels=[],  # Proton-specific labels would need API access
        )

    def _decode_part(self, part: email.message.Message) -> str:
        """
        Decode an email part.

        Args:
            part: Email message part

        Returns:
            Decoded text content
        """
        content = part.get_payload(decode=True)
        charset = part.get_content_charset() or "utf-8"

        try:
            return content.decode(charset)
        except UnicodeDecodeError:
            # Fall back to 'latin-1' if decoding fails
            return content.decode("latin-1", errors="replace")

    def _parse_address_list(self, address_header: str) -> List[str]:
        """
        Parse a list of email addresses from a header.

        Args:
            address_header: Email address header

        Returns:
            List of email addresses
        """
        if not address_header:
            return []

        # Simple regex-based parser, could be replaced with email.utils.getaddresses for more complex cases
        email_pattern = r"[\w\.-]+@[\w\.-]+"
        return re.findall(email_pattern, address_header)

    def send_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        cc: Union[str, List[str]] = None,
        bcc: Union[str, List[str]] = None,
        html: bool = False,
    ) -> Tuple[bool, str]:
        """
        Send an email.

        Args:
            to: Recipient(s)
            subject: Email subject
            body: Email body content
            cc: CC recipient(s)
            bcc: BCC recipient(s)
            html: Whether body is HTML

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_smtp_connected():
            return False, "Failed to connect to SMTP server"

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.username
            msg["Subject"] = subject

            # Handle recipients
            if isinstance(to, list):
                msg["To"] = ", ".join(to)
                recipients = to
            else:
                msg["To"] = to
                recipients = [to]

            # Handle CC
            if cc:
                if isinstance(cc, list):
                    msg["Cc"] = ", ".join(cc)
                    recipients.extend(cc)
                else:
                    msg["Cc"] = cc
                    recipients.append(cc)

            # Handle BCC
            if bcc:
                if isinstance(bcc, list):
                    recipients.extend(bcc)
                else:
                    recipients.append(bcc)

            # Attach body
            if html:
                # Include both plain and HTML versions
                msg.attach(MIMEText(self._html_to_plain(body), "plain"))
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Send email
            self.smtp.sendmail(self.username, recipients, msg.as_string())

            return True, f"Email sent to {', '.join(recipients)}"
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False, f"Error sending email: {str(e)}"

    def _html_to_plain(self, html_content: str) -> str:
        """
        Convert HTML to plain text (very basic conversion).

        Args:
            html_content: HTML content

        Returns:
            Plain text version
        """
        # Remove HTML tags
        text = re.sub(r"<.*?>", "", html_content)
        # Replace multiple whitespace with single space
        text = re.sub(r"\s+", " ", text)
        # Replace HTML entities
        text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
        return text.strip()

    def get_recent_emails(
        self, folder: str = "INBOX", limit: int = 10
    ) -> Tuple[bool, Union[List[EmailMessage], str]]:
        """
        Get recent emails from a folder.

        Args:
            folder: Folder to check (default: "INBOX")
            limit: Maximum number of emails to fetch

        Returns:
            Tuple of (success, emails/error_message)
        """
        # Search for recent emails
        status, message_uids = self.search_emails("ALL", folder, limit)
        if not status:
            return False, message_uids

        # Fetch the emails
        emails = []
        for uid in message_uids:
            status, email_data = self.fetch_email(uid, folder)
            if status:
                emails.append(email_data)

        return True, emails

    def search_by_keyword(
        self, keyword: str, folder: str = "INBOX", limit: int = 10
    ) -> Tuple[bool, Union[List[EmailMessage], str]]:
        """
        Search for emails containing a keyword.

        Args:
            keyword: Keyword to search for
            folder: Folder to search in (default: "INBOX")
            limit: Maximum number of emails to fetch

        Returns:
            Tuple of (success, emails/error_message)
        """
        # Build the search criteria for subjects and body
        criteria = f'OR SUBJECT "{keyword}" BODY "{keyword}"'

        # Search for emails matching the keyword
        status, message_uids = self.search_emails(criteria, folder, limit)
        if not status:
            return False, message_uids

        # Fetch the emails
        emails = []
        for uid in message_uids:
            status, email_data = self.fetch_email(uid, folder)
            if status:
                emails.append(email_data)

        return True, emails

    def get_unread_emails(
        self, folder: str = "INBOX", limit: int = 10
    ) -> Tuple[bool, Union[List[EmailMessage], str]]:
        """
        Get unread emails from a folder.

        Args:
            folder: Folder to check (default: "INBOX")
            limit: Maximum number of emails to fetch

        Returns:
            Tuple of (success, emails/error_message)
        """
        # Search for unread emails
        status, message_uids = self.search_emails("UNSEEN", folder, limit)
        if not status:
            return False, message_uids

        # Fetch the emails
        emails = []
        for uid in message_uids:
            status, email_data = self.fetch_email(uid, folder)
            if status:
                emails.append(email_data)

        return True, emails

    def mark_as_read(self, uid: int, folder: str = "INBOX") -> Tuple[bool, str]:
        """
        Mark an email as read.

        Args:
            uid: Email UID
            folder: Folder containing the email

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_imap_connected():
            return False, "Failed to connect to IMAP server"

        try:
            # Select the folder
            status, _ = self.select_folder(folder)
            if not status:
                return False, f"Failed to select folder {folder}"

            # Set the Seen flag
            status, data = self.imap.store(str(uid), "+FLAGS", "\\Seen")

            if status != "OK":
                return False, f"Failed to mark email {uid} as read: {data}"

            return True, f"Email {uid} marked as read"
        except Exception as e:
            logger.error(f"Error marking email {uid} as read: {str(e)}")
            return False, f"Error marking email {uid} as read: {str(e)}"

    def mark_as_unread(self, uid: int, folder: str = "INBOX") -> Tuple[bool, str]:
        """
        Mark an email as unread.

        Args:
            uid: Email UID
            folder: Folder containing the email

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_imap_connected():
            return False, "Failed to connect to IMAP server"

        try:
            # Select the folder
            status, _ = self.select_folder(folder)
            if not status:
                return False, f"Failed to select folder {folder}"

            # Remove the Seen flag
            status, data = self.imap.store(str(uid), "-FLAGS", "\\Seen")

            if status != "OK":
                return False, f"Failed to mark email {uid} as unread: {data}"

            return True, f"Email {uid} marked as unread"
        except Exception as e:
            logger.error(f"Error marking email {uid} as unread: {str(e)}")
            return False, f"Error marking email {uid} as unread: {str(e)}"

    def move_email(
        self, uid: int, source_folder: str, destination_folder: str
    ) -> Tuple[bool, str]:
        """
        Move an email from one folder to another.

        Args:
            uid: Email UID
            source_folder: Source folder
            destination_folder: Destination folder

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_imap_connected():
            return False, "Failed to connect to IMAP server"

        try:
            # Select the source folder
            status, _ = self.select_folder(source_folder)
            if not status:
                return False, f"Failed to select folder {source_folder}"

            # Copy the email to the destination folder
            status, data = self.imap.copy(str(uid), destination_folder)

            if status != "OK":
                return (
                    False,
                    f"Failed to copy email {uid} to {destination_folder}: {data}",
                )

            # Delete the email from the source folder
            status, data = self.imap.store(str(uid), "+FLAGS", "\\Deleted")

            if status != "OK":
                return False, f"Failed to mark email {uid} for deletion: {data}"

            # Expunge the deleted email
            self.imap.expunge()

            return (
                True,
                f"Email {uid} moved from {source_folder} to {destination_folder}",
            )
        except Exception as e:
            logger.error(f"Error moving email {uid}: {str(e)}")
            return False, f"Error moving email {uid}: {str(e)}"

    def delete_email(self, uid: int, folder: str = "INBOX") -> Tuple[bool, str]:
        """
        Delete an email.

        Args:
            uid: Email UID
            folder: Folder containing the email

        Returns:
            Tuple of (success, message)
        """
        if not self._ensure_imap_connected():
            return False, "Failed to connect to IMAP server"

        try:
            # Select the folder
            status, _ = self.select_folder(folder)
            if not status:
                return False, f"Failed to select folder {folder}"

            # Mark the email for deletion
            status, data = self.imap.store(str(uid), "+FLAGS", "\\Deleted")

            if status != "OK":
                return False, f"Failed to mark email {uid} for deletion: {data}"

            # Expunge the deleted email
            self.imap.expunge()

            return True, f"Email {uid} deleted from {folder}"
        except Exception as e:
            logger.error(f"Error deleting email {uid}: {str(e)}")
            return False, f"Error deleting email {uid}: {str(e)}"

    def close(self):
        """Close connections to IMAP and SMTP servers."""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
            except Exception:
                pass
            finally:
                self.imap = None

        if self.smtp:
            try:
                self.smtp.quit()
            except Exception:
                pass
            finally:
                self.smtp = None

        logger.info("Closed connections to IMAP and SMTP servers")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic connection closure."""
        self.close()

    def get_email_count(self, folder: str = "INBOX") -> Tuple[bool, Union[int, str]]:
        """
        Get the number of emails in a folder.

        Args:
            folder: Folder to check

        Returns:
            Tuple of (success, count/error_message)
        """
        status, result = self.select_folder(folder)
        return status, result

    def extract_entities_from_email(
        self, email_message: EmailMessage
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from an email.

        Args:
            email_message: Email message to extract entities from

        Returns:
            List of entities with name, type, and context
        """
        entities = []

        # Extract sender as a Contact entity
        if email_message.sender:
            sender_name, sender_email = self._parse_sender(email_message.sender)
            entities.append(
                {
                    "name": sender_name or sender_email,
                    "entityType": "Contact",
                    "email": sender_email,
                    "context": f"Sender of email: {email_message.subject}",
                }
            )

        # Extract recipients as Contact entities
        for recipient in email_message.recipients:
            entities.append(
                {
                    "name": recipient,
                    "entityType": "Contact",
                    "email": recipient,
                    "context": f"Recipient of email: {email_message.subject}",
                }
            )

        # Extract CC recipients
        if email_message.cc:
            for cc_recipient in email_message.cc:
                entities.append(
                    {
                        "name": cc_recipient,
                        "entityType": "Contact",
                        "email": cc_recipient,
                        "context": f"CC recipient of email: {email_message.subject}",
                    }
                )

        # Create Email entity
        entities.append(
            {
                "name": email_message.subject,
                "entityType": "Email",
                "message_id": email_message.message_id,
                "date": email_message.date.isoformat() if email_message.date else None,
                "folder": email_message.folder,
                "context": f"Email from {email_message.sender} dated {email_message.date}",
            }
        )

        # TODO: Add more sophisticated entity extraction from email body

        return entities

    def _parse_sender(self, sender: str) -> Tuple[Optional[str], str]:
        """
        Parse sender name and email from sender string.

        Args:
            sender: Sender string (e.g., "John Doe <john@example.com>")

        Returns:
            Tuple of (name, email)
        """
        name_pattern = r"([^<]+)"
        email_pattern = r"<([^>]+)>"

        # Try to match pattern with name and email
        name_match = re.search(name_pattern, sender)
        email_match = re.search(email_pattern, sender)

        if email_match:
            email = email_match.group(1)
            name = name_match.group(1).strip() if name_match else None
            return name, email
        else:
            # If no email found in angle brackets, the whole string might be an email
            email_simple_pattern = r"[\w\.-]+@[\w\.-]+"
            email_simple_match = re.search(email_simple_pattern, sender)

            if email_simple_match:
                return None, email_simple_match.group(0)
            else:
                return None, sender


# Command-line functionality for testing
if __name__ == "__main__":
    import argparse

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Proton Mail Adapter CLI")
    parser.add_argument(
        "--action",
        choices=["list-folders", "list-emails", "search", "read", "send"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--folder", default="INBOX", help="Mail folder to use")
    parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of emails to retrieve"
    )
    parser.add_argument("--query", help="Search query for search action")
    parser.add_argument("--uid", type=int, help="Email UID for read action")
    parser.add_argument("--to", help="Recipient for send action")
    parser.add_argument("--subject", help="Subject for send action")
    parser.add_argument("--body", help="Body content for send action")
    args = parser.parse_args()

    # Create adapter instance
    adapter = ProtonMailAdapter()

    try:
        if args.action == "list-folders":
            status, folders = adapter.list_folders()
            if status:
                print(f"Found {len(folders)} folders:")
                for folder in folders:
                    print(f"- {folder}")
            else:
                print(f"Error: {folders}")

        elif args.action == "list-emails":
            status, emails = adapter.get_recent_emails(args.folder, args.limit)
            if status:
                print(f"Found {len(emails)} emails in {args.folder}:")
                for email in emails:
                    print(
                        f"- {email.uid}: {email.subject} (from: {email.sender}, date: {email.date})"
                    )
            else:
                print(f"Error: {emails}")

        elif args.action == "search":
            if not args.query:
                print("Error: --query is required for search action")
                exit(1)

            status, emails = adapter.search_by_keyword(
                args.query, args.folder, args.limit
            )
            if status:
                print(
                    f"Found {len(emails)} emails matching '{args.query}' in {args.folder}:"
                )
                for email in emails:
                    print(
                        f"- {email.uid}: {email.subject} (from: {email.sender}, date: {email.date})"
                    )
            else:
                print(f"Error: {emails}")

        elif args.action == "read":
            if not args.uid:
                print("Error: --uid is required for read action")
                exit(1)

            status, email = adapter.fetch_email(args.uid, args.folder)
            if status:
                print(f"Subject: {email.subject}")
                print(f"From: {email.sender}")
                print(f"To: {', '.join(email.recipients)}")
                print(f"Date: {email.date}")
                print("\n" + email.body_text)
            else:
                print(f"Error: {email}")

        elif args.action == "send":
            if not args.to or not args.subject or not args.body:
                print("Error: --to, --subject, and --body are required for send action")
                exit(1)

            status, message = adapter.send_email(args.to, args.subject, args.body)
            print(message)

    finally:
        # Close connections
        adapter.close()
