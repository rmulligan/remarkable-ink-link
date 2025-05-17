#!/usr/bin/env python
"""
Claude Code Adapter for code generation and analysis.

This adapter uses Claude Code capabilities through the 'claude' CLI tool
to generate code, perform code reviews, and provide technical assistance.
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from .adapter import Adapter


class ClaudeCodeAdapter(Adapter):
    """
    Adapter for Claude Code capabilities to process coding tasks.

    This adapter uses Claude's CLI tool to generate code, review code,
    provide technical insights, and assist with development tasks.
    """

    def __init__(
        self,
        claude_command: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
        max_tokens: int = 8000,
        temperature: float = 0.7,
        enable_session_management: bool = True,
        cache_outputs: bool = True,
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize the Claude Code adapter.

        Args:
            claude_command: Command to invoke Claude CLI (defaults to 'claude')
            model: Claude model specification (if needed)
            timeout: Maximum time to wait for Claude response in seconds
            max_tokens: Maximum tokens for Claude's response
            temperature: Temperature for text generation (0.0-1.0)
            enable_session_management: Whether to use session management
            cache_outputs: Whether to cache Claude outputs
            cache_dir: Directory for caching outputs
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Get command from arguments or environment
        self.claude_command = claude_command or os.environ.get(
            "CLAUDE_CODE_COMMAND", os.environ.get("CLAUDE_COMMAND", "claude")
        )
        self.model = model or os.environ.get("CLAUDE_CODE_MODEL", "")

        # Model flag for command if specified
        self.model_flag = f"--model {self.model}" if self.model else ""

        # Configuration settings
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.enable_session_management = enable_session_management
        self.cache_outputs = cache_outputs

        # Cache directory
        if cache_dir:
            self.cache_dir = cache_dir
        else:
            temp_dir = os.environ.get("INKLINK_TEMP", "/tmp/inklink")
            self.cache_dir = os.path.join(temp_dir, "claude_code_cache")

        os.makedirs(self.cache_dir, exist_ok=True)

        # Session management
        self.sessions = {}  # Map of session_id to state

        # Check if claude CLI is available
        self._check_claude_availability()

    def _check_claude_availability(self) -> bool:
        """
        Check if the Claude CLI tool is available.

        Returns:
            True if available, False otherwise
        """
        try:
            # Split the command if it contains spaces
            cmd = self.claude_command.replace(" -c", "").replace(" -r", "")
            cmd_parts = cmd.split() if " " in cmd else [cmd]
            result = subprocess.run(
                cmd_parts + ["--version"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                self.logger.info(f"Claude CLI available: {result.stdout.strip()}")
                return True
            self.logger.warning(f"Claude CLI check failed: {result.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to check Claude CLI availability: {e}")
            return False

    def is_available(self) -> bool:
        """
        Check if the Claude Code adapter is available.

        Returns:
            True if the adapter can use the Claude CLI tool
        """
        return self._check_claude_availability()

    def ping(self) -> bool:
        """
        Check if the service is responding.

        Returns:
            True if the service is available, False otherwise
        """
        return self._check_claude_availability()

    def _build_command(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        continue_session: bool = False,
        piped_input: Optional[str] = None,
    ) -> Tuple[List[str], Optional[str]]:
        """
        Build the Claude command with appropriate flags.

        Args:
            prompt: The prompt text
            session_id: Optional session ID for context management
            continue_session: Whether to continue the last session
            piped_input: Optional input to pipe into Claude

        Returns:
            Tuple of (command_parts, stdin_input)
        """
        cmd_parts = self.claude_command.split()

        # Add model flag if specified
        if self.model_flag:
            cmd_parts.extend(self.model_flag.split())

        # Add max tokens flag
        cmd_parts.extend(["--max-tokens", str(self.max_tokens)])

        # Session management flags
        if continue_session:
            cmd_parts.append("-c")  # Continue last conversation
        elif session_id and self.enable_session_management:
            cmd_parts.extend(["-r", session_id])  # Resume specific session

        # Add the prompt
        cmd_parts.extend(["-p", prompt])

        return cmd_parts, piped_input

    def _execute_claude(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        continue_session: bool = False,
        piped_input: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Execute Claude command with the given prompt.

        Args:
            prompt: The prompt to send to Claude
            session_id: Optional session ID for context
            continue_session: Whether to continue last session
            piped_input: Optional input to pipe into Claude

        Returns:
            Tuple of (success, result)
        """
        try:
            cmd_parts, stdin_input = self._build_command(
                prompt, session_id, continue_session, piped_input
            )

            # Execute command
            process = subprocess.Popen(
                cmd_parts,
                stdin=subprocess.PIPE if stdin_input else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Send input if provided
            stdout, stderr = process.communicate(
                input=stdin_input, timeout=self.timeout
            )

            if process.returncode != 0:
                self.logger.error(f"Claude CLI failed: {stderr}")
                return False, f"Claude CLI failed: {stderr}"

            return True, stdout.strip()

        except subprocess.TimeoutExpired:
            process.kill()
            return False, f"Claude command timed out after {self.timeout} seconds"
        except Exception as e:
            self.logger.error(f"Error executing Claude: {e}")
            return False, str(e)

    def generate_code(
        self,
        prompt: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Generate code based on a prompt.

        Args:
            prompt: The code generation prompt
            language: Target programming language
            context: Additional context (e.g., existing code)
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, generated_code_or_error)
        """
        try:
            # Build the prompt
            full_prompt = "You are a code generation assistant. "
            if language:
                full_prompt += f"Generate {language} code. "

            full_prompt += f"\n\n{prompt}"

            if context:
                full_prompt += f"\n\nContext:\n{context}"

            full_prompt += (
                "\n\nProvide only the code without explanations. Use proper formatting."
            )

            # Execute Claude
            success, result = self._execute_claude(
                full_prompt, session_id=session_id, piped_input=context
            )

            if not success:
                return False, result

            # Extract code from response (assuming markdown code blocks)
            code_match = re.search(r"```(?:\w+)?\n(.*?)```", result, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            else:
                # If no code block, assume entire response is code
                code = result.strip()

            # Cache the result if enabled
            if self.cache_outputs:
                self._cache_result("code_generation", prompt, code)

            return True, code

        except Exception as e:
            self.logger.error(f"Code generation failed: {e}")
            return False, str(e)

    def review_code(
        self,
        code: str,
        language: Optional[str] = None,
        instruction: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Review code and provide feedback.

        Args:
            code: The code to review
            language: Programming language of the code
            instruction: Specific review instructions
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, review_feedback_or_error)
        """
        try:
            # Build the prompt
            full_prompt = "You are a code review assistant. "
            if language:
                full_prompt += f"Review this {language} code. "

            if instruction:
                full_prompt += f"{instruction} "
            else:
                full_prompt += (
                    "Identify any bugs, improvements, or best practice violations. "
                )

            full_prompt += "Provide clear, actionable feedback."

            # Execute Claude with code as piped input
            success, result = self._execute_claude(
                full_prompt, session_id=session_id, piped_input=code
            )

            if not success:
                return False, result

            # Parse the review feedback into structured format
            feedback = {
                "summary": "",
                "issues": [],
                "improvements": [],
                "best_practices": [],
                "raw_feedback": result,
            }

            # Simple parsing of sections in the feedback
            sections = re.split(r"\n(?=[A-Z][^:]+:)", result)
            for section in sections:
                if section.lower().startswith("summary"):
                    feedback["summary"] = section.split(":", 1)[1].strip()
                elif "issue" in section.lower() or "bug" in section.lower():
                    feedback["issues"].append(section.strip())
                elif "improvement" in section.lower():
                    feedback["improvements"].append(section.strip())
                elif "best practice" in section.lower():
                    feedback["best_practices"].append(section.strip())

            # Cache the result if enabled
            if self.cache_outputs:
                self._cache_result("code_review", code[:100], feedback)

            return True, feedback

        except Exception as e:
            self.logger.error(f"Code review failed: {e}")
            return False, str(e)

    def debug_code(
        self,
        code: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Debug code and suggest fixes for errors.

        Args:
            code: The code with errors
            error_message: The error message
            stack_trace: Optional stack trace
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, debug_suggestions_or_error)
        """
        try:
            # Build the prompt
            full_prompt = (
                "You are a debugging assistant. The following code is producing an error.\n\n"
                f"Error: {error_message}\n"
            )

            if stack_trace:
                full_prompt += f"\nStack trace:\n{stack_trace}\n"

            full_prompt += (
                "\nAnalyze the code and error. Explain the cause and provide a fix."
            )

            # Execute Claude with code as piped input
            success, result = self._execute_claude(
                full_prompt, session_id=session_id, piped_input=code
            )

            if not success:
                return False, result

            # Parse the debug response
            debug_info = {
                "error_explanation": "",
                "root_cause": "",
                "suggested_fix": "",
                "fixed_code": "",
                "raw_response": result,
            }

            # Extract fixed code if present
            code_match = re.search(r"```(?:\w+)?\n(.*?)```", result, re.DOTALL)
            if code_match:
                debug_info["fixed_code"] = code_match.group(1).strip()

            # Simple parsing for explanations
            if "cause" in result.lower():
                cause_match = re.search(
                    r"cause[:\s]+(.+?)(?:\n|$)", result, re.IGNORECASE
                )
                if cause_match:
                    debug_info["root_cause"] = cause_match.group(1).strip()

            return True, debug_info

        except Exception as e:
            self.logger.error(f"Code debugging failed: {e}")
            return False, str(e)

    def ask_best_practices(
        self,
        query: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Ask for best practices or technical guidance.

        Args:
            query: The technical question
            language: Optional programming language context
            context: Additional context
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, best_practices_advice)
        """
        try:
            # Build the prompt
            full_prompt = "You are a technical advisor providing best practices. "
            if language:
                full_prompt += f"Focus on {language} development. "

            full_prompt += f"\n\nQuestion: {query}"

            if context:
                full_prompt += f"\n\nContext: {context}"

            full_prompt += (
                "\n\nProvide clear, actionable best practices and recommendations."
            )

            # Execute Claude
            success, result = self._execute_claude(full_prompt, session_id=session_id)

            if not success:
                return False, result

            # Cache the result if enabled
            if self.cache_outputs:
                self._cache_result("best_practices", query, result)

            return True, result

        except Exception as e:
            self.logger.error(f"Best practices query failed: {e}")
            return False, str(e)

    def summarize_text(
        self,
        text: str,
        focus: Optional[str] = None,
        max_length: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Summarize technical text or documentation.

        Args:
            text: The text to summarize
            focus: Optional focus area for summarization
            max_length: Optional maximum length for summary
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, summary)
        """
        try:
            # Build the prompt
            full_prompt = "Summarize the following technical content. "
            if focus:
                full_prompt += f"Focus on {focus}. "
            if max_length:
                full_prompt += f"Keep the summary under {max_length} words. "

            full_prompt += "Highlight key decisions and technical details."

            # Execute Claude with text as piped input
            success, result = self._execute_claude(
                full_prompt, session_id=session_id, piped_input=text
            )

            if not success:
                return False, result

            # Cache the result if enabled
            if self.cache_outputs:
                self._cache_result("summarization", text[:100], result)

            return True, result

        except Exception as e:
            self.logger.error(f"Text summarization failed: {e}")
            return False, str(e)

    def explain_code(
        self,
        code: str,
        language: Optional[str] = None,
        detail_level: str = "medium",
        session_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Explain what a piece of code does.

        Args:
            code: The code to explain
            language: Programming language
            detail_level: Level of detail ("simple", "medium", "detailed")
            session_id: Optional session ID for context

        Returns:
            Tuple of (success, explanation)
        """
        try:
            # Build the prompt based on detail level
            if detail_level == "simple":
                prompt = "Explain what this code does in simple terms for beginners."
            elif detail_level == "detailed":
                prompt = "Provide a detailed explanation of this code, including implementation details."
            else:  # medium
                prompt = "Explain what this code does and how it works."

            if language:
                prompt = f"{prompt} This is {language} code."

            # Execute Claude with code as piped input
            success, result = self._execute_claude(
                prompt, session_id=session_id, piped_input=code
            )

            return success, result if success else f"Explanation failed: {result}"

        except Exception as e:
            self.logger.error(f"Code explanation failed: {e}")
            return False, str(e)

    def _cache_result(self, operation: str, key: str, result: Any):
        """
        Cache a result for future reference.

        Args:
            operation: Type of operation (e.g., "code_generation")
            key: Cache key (e.g., prompt or code snippet)
            result: The result to cache
        """
        try:
            # Create a safe filename from the key
            safe_key = re.sub(r"[^\w\-_]", "_", key[:50])
            timestamp = int(time.time())
            filename = f"{operation}_{safe_key}_{timestamp}.json"
            filepath = os.path.join(self.cache_dir, filename)

            cache_data = {
                "operation": operation,
                "key": key,
                "result": result,
                "timestamp": timestamp,
            }

            with open(filepath, "w") as f:
                json.dump(cache_data, f, indent=2)

            self.logger.debug(f"Cached result to {filepath}")

        except Exception as e:
            self.logger.warning(f"Failed to cache result: {e}")

    def get_cached_result(
        self, operation: str, key: str, max_age: int = 3600
    ) -> Optional[Any]:
        """
        Retrieve a cached result if available and not too old.

        Args:
            operation: Type of operation
            key: Cache key
            max_age: Maximum age in seconds

        Returns:
            Cached result or None
        """
        try:
            safe_key = re.sub(r"[^\w\-_]", "_", key[:50])
            pattern = f"{operation}_{safe_key}_*.json"

            # Find matching cache files
            import glob

            cache_files = glob.glob(os.path.join(self.cache_dir, pattern))

            if not cache_files:
                return None

            # Get the most recent cache file
            latest_file = max(cache_files, key=os.path.getctime)

            with open(latest_file, "r") as f:
                cache_data = json.load(f)

            # Check age
            age = time.time() - cache_data["timestamp"]
            if age > max_age:
                return None

            return cache_data["result"]

        except Exception as e:
            self.logger.warning(f"Failed to retrieve cached result: {e}")
            return None

    def manage_session(self, session_id: str, action: str = "create") -> bool:
        """
        Manage Claude sessions for multi-turn conversations.

        Args:
            session_id: Session identifier
            action: Action to perform ("create", "resume", "end")

        Returns:
            Success status
        """
        try:
            if action == "create":
                self.sessions[session_id] = {
                    "created": time.time(),
                    "last_used": time.time(),
                    "turn_count": 0,
                }
                return True

            elif action == "resume":
                if session_id in self.sessions:
                    self.sessions[session_id]["last_used"] = time.time()
                    self.sessions[session_id]["turn_count"] += 1
                    return True
                return False

            elif action == "end":
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    return True
                return False

            else:
                self.logger.warning(f"Unknown session action: {action}")
                return False

        except Exception as e:
            self.logger.error(f"Session management failed: {e}")
            return False

    def continue_conversation(
        self, prompt: str, session_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Continue a conversation with Claude using session management.

        Args:
            prompt: The continuation prompt
            session_id: Optional session ID (uses last session if None)

        Returns:
            Tuple of (success, response)
        """
        try:
            # If session_id provided, ensure it exists and is active
            if session_id:
                if session_id not in self.sessions:
                    return False, f"Session {session_id} not found"
                self.manage_session(session_id, "resume")

            # Execute with continuation flag
            success, result = self._execute_claude(
                prompt, session_id=session_id, continue_session=(session_id is None)
            )

            return success, result

        except Exception as e:
            self.logger.error(f"Conversation continuation failed: {e}")
            return False, str(e)

    async def async_execute(self, operation: str, *args, **kwargs) -> Tuple[bool, Any]:
        """
        Execute an operation asynchronously.

        Args:
            operation: Operation name (e.g., "generate_code")
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Tuple of (success, result)
        """
        loop = asyncio.get_event_loop()

        # Map operation names to methods
        operations = {
            "generate_code": self.generate_code,
            "review_code": self.review_code,
            "debug_code": self.debug_code,
            "ask_best_practices": self.ask_best_practices,
            "summarize_text": self.summarize_text,
            "explain_code": self.explain_code,
        }

        if operation not in operations:
            return False, f"Unknown operation: {operation}"

        # Run in executor to avoid blocking
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor, operations[operation], *args, **kwargs
                )
            return result
        except Exception as e:
            self.logger.error(f"Async execution failed: {e}")
            return False, str(e)

    def create_coding_prompt(
        self,
        task_type: str,
        details: Dict[str, Any],
        style_guide: Optional[str] = None,
    ) -> str:
        """
        Create an optimized prompt for a coding task.

        Args:
            task_type: Type of task (e.g., "refactor", "implement", "fix")
            details: Task-specific details
            style_guide: Optional coding style guide

        Returns:
            Formatted prompt string
        """
        prompts = {
            "refactor": "Refactor the following code to improve {quality}. {constraints}",
            "implement": "Implement {feature} with the following requirements: {requirements}",
            "fix": "Fix the {issue_type} in the code. Error: {error_message}",
            "optimize": "Optimize the code for {optimization_target}. Current issue: {issue}",
            "document": "Add comprehensive documentation to the code. Include {doc_types}.",
        }

        base_prompt = prompts.get(
            task_type, "Complete the following coding task: {description}"
        )

        # Format the prompt with details
        formatted_prompt = base_prompt
        for key, value in details.items():
            placeholder = f"{{{key}}}"
            if placeholder in formatted_prompt:
                formatted_prompt = formatted_prompt.replace(placeholder, str(value))

        # Add style guide if provided
        if style_guide:
            formatted_prompt += f"\n\nFollow this style guide:\n{style_guide}"

        return formatted_prompt
