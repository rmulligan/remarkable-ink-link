"""Claude CLI Adapter for InkLink.

This module provides an adapter for interacting with Claude AI assistant
through the local Claude CLI command.
"""

import logging
import os
import re
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from inklink.adapters.adapter import Adapter
from inklink.utils import format_error, retry_operation

logger = logging.getLogger(__name__)


class ClaudeCliAdapter(Adapter):
    """Adapter for Claude CLI interactions."""

    def __init__(
        self,
        claude_command: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize ClaudeCliAdapter.

        Args:
            claude_command: Command to invoke Claude CLI (e.g., 'claude')
            model: Claude model to use (e.g., 'claude-3-opus-20240229')
            system_prompt: Default system prompt to use
        """
        # Set the Claude CLI command
        self.claude_command = claude_command or os.environ.get(
            "CLAUDE_COMMAND", "/home/ryan/.claude/local/claude"
        )

        # Set the Claude model if provided
        self.model = model or os.environ.get("CLAUDE_MODEL", "")
        self.model_flag = f"--model {self.model}" if self.model else ""

        # Set the system prompt
        self.system_prompt = system_prompt or os.environ.get(
            "CLAUDE_SYSTEM_PROMPT", "You are a helpful assistant."
        )

        # Temporary directory for input/output files
        self.temp_dir = os.environ.get(
            "INKLINK_TEMP",
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp"
            ),
        )
        os.makedirs(self.temp_dir, exist_ok=True)

        # Track conversation IDs for context
        self.conversation_ids = {}

    def ping(self) -> bool:
        """
        Check if the Claude CLI is available.

        Returns:
            True if Claude CLI is accessible, False otherwise
        """
        try:
            # Remove -c flag if it's part of the command when checking version
            cmd = self.claude_command.replace(" -c", "").replace(" -r", "")
            cmd_parts = cmd.split() if " " in cmd else [cmd]

            # Run version check
            process = subprocess.run(
                cmd_parts + ["--version"], capture_output=True, text=True, timeout=5
            )
            if process.returncode == 0:
                logger.info(f"Claude CLI available: {process.stdout.strip()}")
                return True
            logger.error(f"Claude CLI check failed: {process.stderr}")
            return False
        except Exception as e:
            logger.error(f"Claude CLI not available: {e}")
            return False

    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        conversation_id: Optional[str] = None,
        use_context: bool = False,
    ) -> Tuple[bool, str]:
        """
        Generate completion from Claude using the CLI.

        Args:
            prompt: User prompt text
            system_prompt: System prompt to override default
            max_tokens: Maximum tokens to generate (not directly used with CLI)
            temperature: Temperature for sampling (not directly used with CLI)
            conversation_id: Optional conversation ID for continuity
            use_context: Whether to use -c flag for continuous conversation

        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        try:
            # Create temporary files for input and output
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".txt", delete=False
            ) as input_file:
                input_path = input_file.name

                # Add system prompt if provided (Claude CLI doesn't have direct system prompt support)
                if system_prompt:
                    input_file.write(f"System: {system_prompt}\n\n")

                # Write user prompt
                input_file.write(prompt)
                input_file.flush()

            output_path = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name
            stderr_path = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name

            # Build the Claude CLI command
            cmd = f"{self.claude_command}"

            # Add model flag if specified
            if self.model_flag:
                cmd += f" {self.model_flag}"

            # Add conversation context flag if needed
            if use_context:
                cmd += " -c"

            # Add conversation ID if provided
            if conversation_id:
                cmd += f" -r {conversation_id}"

            # Add input/output redirection
            cmd += f" < {input_path} > {output_path} 2> {stderr_path}"

            # Execute command
            logger.info(f"Executing Claude command: {cmd}")
            subprocess.run(cmd, shell=True, check=True)

            # If using a conversation ID, try to capture it from stderr
            if not conversation_id and (use_context or conversation_id == ""):
                try:
                    # Read stderr which might contain the conversation ID
                    if os.path.exists(stderr_path):
                        with open(stderr_path, "r") as stderr_file:
                            stderr_content = stderr_file.read()
                            # Look for conversation ID, usually printed like "Conversation: abc123"
                            id_match = re.search(
                                r"Conversation:\s+([a-zA-Z0-9]+)", stderr_content
                            )
                            if id_match:
                                new_conversation_id = id_match.group(1)
                                logger.info(
                                    f"Captured conversation ID: {new_conversation_id}"
                                )
                                return True, new_conversation_id
                except Exception as e:
                    logger.error(f"Failed to capture conversation ID: {e}")

            # Read response
            with open(output_path, "r") as f:
                response = f.read().strip()

            # Clean up temp files
            os.unlink(input_path)
            os.unlink(output_path)
            os.unlink(stderr_path)

            return True, response

        except Exception as e:
            logger.error(f"Error generating completion with Claude CLI: {e}")
            return False, str(e)

    def process_with_context(
        self,
        prompt: str,
        context_id: str = "default",
        new_conversation: bool = False,
        system_prompt: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Process a query with Claude while maintaining conversation context.

        Args:
            prompt: User prompt text
            context_id: Identifier for the conversation context
            new_conversation: Whether to start a new conversation
            system_prompt: Optional system prompt

        Returns:
            Tuple of (success: bool, response: str, conversation_id: Optional[str])
        """
        try:
            # Determine which context mode to use
            use_context = not new_conversation and context_id in self.conversation_ids
            conversation_id = (
                None if new_conversation else self.conversation_ids.get(context_id)
            )

            # Generate completion
            success, result = self.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                conversation_id=conversation_id,
                use_context=use_context,
            )

            if not success:
                return False, f"Error: {result}", None

            # If this is a new conversation and we got back a conversation ID instead of content
            if new_conversation or conversation_id is None:
                # Check if the result might be a conversation ID (short alphanumeric string)
                if re.match(r"^[a-zA-Z0-9]{5,20}$", result):
                    # Store the conversation ID
                    self.conversation_ids[context_id] = result

                    # Make a second call with the new conversation ID
                    success, response = self.generate_completion(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        conversation_id=result,
                        use_context=False,
                    )

                    if success:
                        return True, response, result
                    return False, f"Error in follow-up: {response}", result

            # Normal response case
            return True, result, conversation_id

        except Exception as e:
            logger.error(f"Error in process_with_context: {e}")
            return False, str(e), None

    def generate_structured_completion(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None,
        structured_content: Optional[
            Union[List[Dict[str, Any]], Dict[str, Any]]
        ] = None,
        context_window: Optional[int] = None,
        selected_pages: Optional[List[Union[int, str]]] = None,
    ) -> Tuple[bool, str]:
        """
        Process a text query with document context and return an AI response.

        Args:
            query_text: The user's query
            context: Additional context as a dictionary
            structured_content: Structured document content
            context_window: Number of most recent pages to include
            selected_pages: Specific pages to include as context

        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        # Build system prompt with context
        system_prompt = self._build_system_prompt_with_context(
            context=context,
            structured_content=structured_content,
            context_window=context_window,
            selected_pages=selected_pages,
        )

        # Generate completion with the enhanced system prompt
        success, result, _ = self.process_with_context(
            prompt=query_text,
            system_prompt=system_prompt,
            new_conversation=True,  # Use a new conversation for each structured query
        )

        return success, result

    def _build_system_prompt_with_context(
        self,
        context: Optional[Dict[str, Any]] = None,
        structured_content: Optional[
            Union[List[Dict[str, Any]], Dict[str, Any]]
        ] = None,
        context_window: Optional[int] = None,
        selected_pages: Optional[List[Union[int, str]]] = None,
    ) -> str:
        """
        Build a system prompt that includes document context.

        Args:
            context: Dictionary of context variables
            structured_content: Document content as structured data
            context_window: Number of recent pages to include
            selected_pages: Specific pages to include

        Returns:
            Enhanced system prompt with context
        """
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

            # Create system prompt with document context
            return "Relevant document context:\n" + "\n\n".join(context_snippets)

        if context:
            # Format context dictionary
            context_str = ", ".join([f"{k}: {v}" for k, v in context.items() if v])
            return f"Document context: {context_str}"
        # Use default system prompt
        return self.system_prompt
