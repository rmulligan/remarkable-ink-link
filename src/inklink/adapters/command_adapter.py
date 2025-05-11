"""Command-line tool adapter for InkLink.

This module provides an adapter for running external command-line tools with
consistent error handling, retries, and output processing.
"""

import os
import logging
import subprocess
import shlex
from typing import Dict, Any, Optional, List, Tuple, Union

from inklink.adapters.adapter import Adapter
from inklink.utils import retry_operation

logger = logging.getLogger(__name__)


class CommandAdapter(Adapter):
    """Adapter for running external command-line tools."""

    def __init__(self, executable_path: str, working_directory: str = None):
        """
        Initialize with executable path and working directory.

        Args:
            executable_path: Path to executable
            working_directory: Working directory for command execution
        """
        self.executable_path = executable_path
        self.working_directory = working_directory or os.getcwd()

    def ping(self) -> bool:
        """
        Check if the executable is available.

        Returns:
            True if executable exists and is executable, False otherwise
        """
        if not self.executable_path:
            return False

        return os.path.exists(self.executable_path) and os.access(
            self.executable_path, os.X_OK
        )

    def run_command(
        self,
        args: List[str],
        capture_output: bool = True,
        check: bool = False,
        timeout: int = 60,
        env: Dict[str, str] = None,
        cwd: str = None,
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Run a command with the executable.

        Args:
            args: Command arguments
            capture_output: Whether to capture command output
            check: Whether to raise an exception on non-zero exit code
            timeout: Command timeout in seconds
            env: Environment variables
            cwd: Working directory (overrides default)

        Returns:
            Tuple of (success, output_or_error)
        """
        try:
            # Check if executable exists
            if not self.ping():
                return (
                    False,
                    f"Executable not found or not executable: {self.executable_path}",
                )

            # Build command
            cmd = [self.executable_path] + args

            # Set working directory
            cwd = cwd or self.working_directory

            # Run command
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=check,
                timeout=timeout,
                env=env,
                cwd=cwd,
            )

            # Process result
            if result.returncode == 0:
                # Success
                output = result.stdout if capture_output else ""
                return True, output
            else:
                # Error
                error = (
                    result.stderr
                    if capture_output
                    else f"Command failed with exit code {result.returncode}"
                )
                return False, error

        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"

        except subprocess.CalledProcessError as e:
            return False, f"Command failed with exit code {e.returncode}: {e.stderr}"

        except Exception as e:
            logger.error(f"Error running command: {str(e)}")
            return False, str(e)

    def run_with_retry(
        self, args: List[str], max_retries: int = 3, retry_delay: int = 2, **kwargs
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Run a command with retries.

        Args:
            args: Command arguments
            max_retries: Maximum number of retries
            retry_delay: Initial delay between retries in seconds
            **kwargs: Additional arguments for run_command

        Returns:
            Tuple of (success, output_or_error)
        """
        try:
            # Define retry function
            def run_command_wrapper():
                success, result = self.run_command(args, **kwargs)
                if not success:
                    raise RuntimeError(result)
                return success, result

            # Run with retry
            return retry_operation(
                run_command_wrapper,
                operation_name=f"Command {self.executable_path}",
                max_retries=max_retries,
                retry_delay=retry_delay,
            )

        except Exception as e:
            logger.error(f"Command failed after retries: {str(e)}")
            return False, str(e)

    def parse_json_output(self, output: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Parse JSON output from a command.

        Args:
            output: Command output

        Returns:
            Tuple of (success, parsed_json_or_error)
        """
        try:
            import json

            return True, json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON output: {str(e)}")
            return False, str(e)

    def parse_key_value_output(
        self, output: str, delimiter: str = ":"
    ) -> Dict[str, str]:
        """
        Parse key-value output from a command.

        Args:
            output: Command output
            delimiter: Key-value delimiter

        Returns:
            Dictionary of key-value pairs
        """
        result = {}

        try:
            for line in output.splitlines():
                line = line.strip()
                if not line or delimiter not in line:
                    continue

                key, value = line.split(delimiter, 1)
                result[key.strip()] = value.strip()

            return result

        except Exception as e:
            logger.error(f"Failed to parse key-value output: {str(e)}")
            return {}
