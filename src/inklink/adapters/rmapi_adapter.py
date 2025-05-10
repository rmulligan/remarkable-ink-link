"""Remarkable API adapter for InkLink.

This module provides an adapter for interacting with the reMarkable Cloud API
via the rmapi tool, including authentication handling.
"""

import os
import subprocess
import tempfile
import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class RMAPIAdapter:
    """Adapter for interacting with reMarkable Cloud via rmapi tool."""

    def __init__(self, rmapi_path: Optional[str] = None):
        """
        Initialize the rmapi adapter.

        Args:
            rmapi_path: Path to the rmapi executable
        """
        self.rmapi_path = rmapi_path
        self._validate_executable()

    def _validate_executable(self) -> bool:
        """
        Validate that the rmapi executable exists and is executable.

        Returns:
            True if valid, False otherwise
        """
        if not self.rmapi_path or not os.path.exists(self.rmapi_path):
            logger.warning("rmapi path not available. RMAPI operations will fail.")
            return False

        if not os.access(self.rmapi_path, os.X_OK):
            logger.warning(f"rmapi at {self.rmapi_path} is not executable")
            return False

        return True

    def authenticate_with_code(self, code: str) -> Tuple[bool, str]:
        """
        Authenticate with reMarkable Cloud using the provided one-time code.

        Args:
            code: One-time authentication code

        Returns:
            Tuple containing success status and message
        """
        if not self._validate_executable():
            return False, "rmapi path not valid"

        logger.info("Starting rmapi authentication with one-time code")

        # First try expect script approach
        try:
            result = self._authenticate_with_expect(code)
            if result[0]:
                return result
            logger.warning(f"Expect script authentication failed: {result[1]}")
        except Exception as e:
            logger.warning(f"Expect script approach failed: {str(e)}")

        # Fallback to named pipe approach
        try:
            return self._authenticate_with_pipe(code)
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, str(e)

    def _authenticate_with_expect(self, code: str) -> Tuple[bool, str]:
        """
        Authenticate using an expect script.

        Args:
            code: One-time authentication code

        Returns:
            Tuple containing success status and message
        """
        # Create a temporary expect script file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".exp", delete=False
        ) as expect_file:
            expect_path = expect_file.name
            expect_file.write(
                f"""#!/usr/bin/expect -f
                set timeout 30
                set code "{code}"

                spawn {self.rmapi_path} ls
                expect {{
                    "Enter one-time code:" {{
                        send "$code\\r"
                        exp_continue
                    }}
                    "Permanent token stored" {{
                        exit 0
                    }}
                    eof {{
                        exit 1
                    }}
                    timeout {{
                        exit 2
                    }}
                }}
                """
            )

        try:
            # Make the script executable
            os.chmod(expect_path, 0o755)

            # Run the expect script
            process = subprocess.run(
                [expect_path], capture_output=True, text=True, timeout=45
            )

            # Check if authentication was successful
            if process.returncode == 0:
                logger.info("Authentication successful using expect script")
                return True, "Authentication successful"

            # If expect script failed, log the details
            return (
                False,
                f"Expect script failed with code {process.returncode}, output: {process.stdout}",
            )

        finally:
            # Remove the temporary script
            try:
                os.unlink(expect_path)
            except Exception:
                pass

    def _authenticate_with_pipe(self, code: str) -> Tuple[bool, str]:
        """
        Authenticate using a named pipe.

        Args:
            code: One-time authentication code

        Returns:
            Tuple containing success status and message
        """
        # Create a named pipe (FIFO)
        pipe_path = os.path.join(
            tempfile.gettempdir(), f"rmapi_auth_{int(time.time())}.pipe"
        )
        try:
            os.mkfifo(pipe_path)
        except Exception as e:
            logger.error(f"Failed to create named pipe: {str(e)}")
            return False, f"Failed to create pipe: {str(e)}"

        try:
            # Start a process that will write the code to the pipe
            with open(pipe_path, "w") as fifo:
                # Write the code with a newline
                fifo.write(f"{code}\n")
                fifo.flush()

                # Run rmapi with stdin from the pipe
                process = subprocess.run(
                    [self.rmapi_path, "ls"],
                    stdin=open(pipe_path, "r"),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            # Check the result
            if process.returncode == 0:
                logger.info("Authentication successful using named pipe")
                return True, "Authentication successful"
            else:
                logger.error(f"Authentication failed: {process.stderr}")
                return False, process.stderr

        finally:
            # Remove the pipe
            try:
                os.unlink(pipe_path)
            except Exception:
                pass

    def run_command(self, command: str, *args) -> Tuple[bool, str, str]:
        """
        Run an rmapi command.

        Args:
            command: The rmapi command to run
            *args: Additional arguments for the command

        Returns:
            Tuple containing (success status, stdout, stderr)
        """
        if not self._validate_executable():
            return False, "", "rmapi path not valid"

        try:
            cmd = [self.rmapi_path, command] + list(args)
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if process.returncode == 0:
                return True, process.stdout, process.stderr
            else:
                logger.error(f"rmapi command failed: {process.stderr}")
                return False, process.stdout, process.stderr

        except Exception as e:
            logger.error(f"Error running rmapi command: {str(e)}")
            return False, "", str(e)
