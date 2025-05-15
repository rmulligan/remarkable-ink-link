"""CLI-based AI Adapter for InkLink.

This module provides adapters for CLI-based AI tools (Claude, GitHub Copilot CLI, OpenAI Codex).
"""

import os
import logging
import subprocess
import tempfile
from typing import Dict, Any, List, Optional, Union, Tuple

from inklink.adapters.adapter import Adapter

logger = logging.getLogger(__name__)


class CLIAIAdapter(Adapter):
    """Adapter for CLI-based AI tools like Claude Code, Copilot CLI, and Codex."""

    SUPPORTED_CLI_TYPES = ["claude", "copilot", "codex"]

    def __init__(
        self,
        cli_type: str = "claude",
        cli_path: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        timeout: int = 30,
    ):
        """
        Initialize CLIAIAdapter.

        Args:
            cli_type: Type of CLI tool ("claude", "copilot", "codex")
            cli_path: Path to the CLI executable (optional, will search in PATH if not provided)
            model: Model name if supported by the CLI tool
            system_prompt: Default system prompt
            temperature: Temperature for sampling (0.0-1.0)
            timeout: Command timeout in seconds
        """
        # Validate CLI type
        self.cli_type = cli_type.lower()
        if self.cli_type not in self.SUPPORTED_CLI_TYPES:
            raise ValueError(
                f"Unsupported CLI type: {cli_type}. "
                f"Supported types: {', '.join(self.SUPPORTED_CLI_TYPES)}"
            )

        # Set CLI path
        self.cli_path = cli_path or self._find_cli_path()
        if not self.cli_path:
            logger.warning(
                f"CLI executable for {self.cli_type} not found. "
                f"Functionality may be limited."
            )

        # Other parameters
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.timeout = timeout

    def _find_cli_path(self) -> Optional[str]:
        """
        Find the path to the CLI executable based on cli_type.

        Returns:
            Path to the CLI executable or None if not found
        """
        cli_command_map = {
            "claude": "claude",
            "copilot": "gh",  # GitHub CLI with copilot extension
            "codex": "codex",
        }

        base_command = cli_command_map.get(self.cli_type)
        if not base_command:
            return None

        try:
            # Use 'which' to find the command in PATH
            result = subprocess.run(
                ["which", base_command],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"Error finding CLI path: {e}")
            return None

    def ping(self) -> bool:
        """
        Check if the CLI tool is available.

        Returns:
            True if CLI is accessible, False otherwise
        """
        if not self.cli_path:
            return False

        try:
            # Check CLI availability with a simple command
            if self.cli_type == "claude":
                # Claude CLI version check
                cmd = [self.cli_path, "--version"]
            elif self.cli_type == "copilot":
                # GitHub Copilot CLI extension check
                cmd = [self.cli_path, "copilot", "--version"]
            elif self.cli_type == "codex":
                # Codex CLI version check
                cmd = [self.cli_path, "--version"]
            else:
                return False

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"CLI tool not available: {e}")
            return False

    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Generate completion using the CLI tool.

        Args:
            prompt: User prompt text
            system_prompt: System prompt to override default
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0.0-1.0)

        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        if not self.cli_path:
            return False, f"CLI executable for {self.cli_type} not found"

        try:
            if self.cli_type == "claude":
                return self._generate_claude_completion(
                    prompt, system_prompt, max_tokens, temperature
                )
            elif self.cli_type == "copilot":
                return self._generate_copilot_completion(
                    prompt, system_prompt, max_tokens, temperature
                )
            elif self.cli_type == "codex":
                return self._generate_codex_completion(
                    prompt, system_prompt, max_tokens, temperature
                )
            else:
                return False, f"Unsupported CLI type: {self.cli_type}"

        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return False, str(e)

    def _generate_claude_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Generate completion using Claude CLI.

        Args:
            prompt: User prompt text
            system_prompt: System prompt to override default
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0.0-1.0)

        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        # Build Claude CLI command
        cmd = [self.cli_path]

        # Add flags
        if system_prompt or self.system_prompt:
            actual_system_prompt = system_prompt or self.system_prompt
            cmd.extend(["--system", actual_system_prompt])

        if max_tokens:
            cmd.extend(["--max-tokens", str(max_tokens)])

        if temperature is not None:
            cmd.extend(["--temperature", str(temperature)])
        elif self.temperature is not None:
            cmd.extend(["--temperature", str(self.temperature)])

        if self.model:
            cmd.extend(["--model", self.model])

        # Add the prompt (as a positional argument)
        cmd.append(prompt)

        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            output_file = temp_file.name

        try:
            # Run Claude CLI with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout,
            )

            # Check for errors
            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip()
                    or f"Claude CLI exited with code {result.returncode}"
                )
                return False, error_msg

            # Return the output
            output = result.stdout.strip()
            return True, output

        except subprocess.TimeoutExpired:
            return False, f"Claude CLI command timed out after {self.timeout} seconds"
        except Exception as e:
            return False, f"Error running Claude CLI: {str(e)}"
        finally:
            # Clean up temp file
            if os.path.exists(output_file):
                os.unlink(output_file)

    def _generate_copilot_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Generate completion using GitHub Copilot CLI.

        Args:
            prompt: User prompt text
            system_prompt: System prompt to override default
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0.0-1.0)

        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        # GitHub Copilot CLI doesn't directly support system prompts or max tokens
        # We'll use 'gh copilot suggest' command

        cmd = [self.cli_path, "copilot", "suggest", prompt]

        try:
            # Run Copilot CLI with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout,
            )

            # Check for errors
            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip()
                    or f"Copilot CLI exited with code {result.returncode}"
                )
                return False, error_msg

            # Return the output
            output = result.stdout.strip()
            return True, output

        except subprocess.TimeoutExpired:
            return False, f"Copilot CLI command timed out after {self.timeout} seconds"
        except Exception as e:
            return False, f"Error running Copilot CLI: {str(e)}"

    def _generate_codex_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Generate completion using OpenAI Codex CLI.

        Args:
            prompt: User prompt text
            system_prompt: System prompt to override default
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0.0-1.0)

        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        # Build Codex CLI command
        cmd = [self.cli_path]

        # Add flags
        temp_value = temperature if temperature is not None else self.temperature
        if temp_value is not None:
            cmd.extend(["--temperature", str(temp_value)])

        # Add the prompt (usually as a positional argument)
        cmd.append(prompt)

        try:
            # Run Codex CLI with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout,
            )

            # Check for errors
            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip()
                    or f"Codex CLI exited with code {result.returncode}"
                )
                return False, error_msg

            # Return the output
            output = result.stdout.strip()
            return True, output

        except subprocess.TimeoutExpired:
            return False, f"Codex CLI command timed out after {self.timeout} seconds"
        except Exception as e:
            return False, f"Error running Codex CLI: {str(e)}"

    def generate_structured_completion(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None,
        structured_content: Optional[
            Union[List[Dict[str, Any]], Dict[str, Any]]
        ] = None,
        context_window: Optional[int] = None,
        selected_pages: Optional[List[Union[int, str]]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> Tuple[bool, str]:
        """
        Process a text query with document context using CLI tools.

        For CLI tools, we'll need to format the context into the prompt
        since CLI tools don't have built-in structured modes.

        Args:
            query_text: The user's query
            context: Additional context as a dictionary
            structured_content: Structured document content
            context_window: Number of most recent pages to include
            selected_pages: Specific pages to include as context
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0.0-1.0)

        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        # Build enhanced prompt with context
        enhanced_prompt = self._build_prompt_with_context(
            query_text,
            context,
            structured_content,
            context_window,
            selected_pages,
        )

        # Generate completion with the enhanced prompt
        return self.generate_completion(
            prompt=enhanced_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _build_prompt_with_context(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None,
        structured_content: Optional[
            Union[List[Dict[str, Any]], Dict[str, Any]]
        ] = None,
        context_window: Optional[int] = None,
        selected_pages: Optional[List[Union[int, str]]] = None,
    ) -> str:
        """
        Build a prompt that includes document context.

        Args:
            query_text: User query
            context: Dictionary of context variables
            structured_content: Document content as structured data
            context_window: Number of recent pages to include
            selected_pages: Specific pages to include

        Returns:
            Enhanced prompt with context
        """
        prompt_parts = []

        # Add context if available
        if structured_content:
            context_snippets = []
            pages = []

            # Extract pages from structured_content
            if isinstance(structured_content, dict):
                pages = structured_content.get("pages", [])
            elif isinstance(structured_content, list):
                pages = structured_content

            # Filter pages based on selection criteria
            if selected_pages:
                filtered = [
                    p
                    for p in pages
                    if (
                        p.get("id") in selected_pages
                        or p.get("number") in selected_pages
                    )
                ]
            elif context_window:
                filtered = pages[-context_window:]
            else:
                filtered = pages

            # Format each page's content
            for page in filtered:
                title = page.get("title", f"Page {page.get('number', '')}")
                content = page.get("content", "")
                links = page.get("links", [])

                # Format links if present
                link_str = ""
                if links:
                    link_str = "Links: " + ", ".join(
                        [
                            f"{link.get('label', link.get('target', ''))} (to page {link.get('target', '')})"
                            for link in links
                        ]
                    )

                context_snippets.append(f"{title}:\n{content}\n{link_str}".strip())

            # Add document context
            prompt_parts.append(
                "Relevant document context:\n" + "\n\n".join(context_snippets)
            )

        elif context:
            # Format context dictionary
            context_str = ", ".join([f"{k}: {v}" for k, v in context.items() if v])
            prompt_parts.append(f"Document context: {context_str}")

        # Add the user query
        prompt_parts.append(f"Query: {query_text}")

        # Combine all parts
        return "\n\n".join(prompt_parts)
