#!/usr/bin/env python
"""
Unified LLM Interface for InkLink.

This module provides a unified interface for interacting with various LLM providers,
including local models and cloud-based services like Claude Code.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union


class ILLMProvider(ABC):
    """Base interface for language model providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM provider is available."""
        pass

    @abstractmethod
    def ask(self, prompt: str, context: Optional[str] = None) -> Tuple[bool, str]:
        """
        Ask a general question to the LLM.

        Args:
            prompt: The question or prompt
            context: Optional context for the question

        Returns:
            Tuple of (success, response)
        """
        pass


class ICodeLLMProvider(ILLMProvider):
    """Extended interface for LLMs that support code operations."""

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass


class ITechnicalLLMProvider(ICodeLLMProvider):
    """Interface for LLMs that support technical documentation and research."""

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass


class UnifiedLLMInterface:
    """
    Unified interface for managing multiple LLM providers.

    This class provides intelligent routing and fallback mechanisms
    for different types of LLM queries.
    """

    def __init__(
        self,
        providers: Optional[Dict[str, ILLMProvider]] = None,
        default_provider: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the unified LLM interface.

        Args:
            providers: Dictionary of provider_name -> provider_instance
            default_provider: Name of the default provider
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.providers = providers or {}
        self.default_provider = default_provider
        self.config = config or {}

        # Task routing configuration
        self.task_routing = self.config.get(
            "task_routing",
            {
                "code_generation": ["claude_code", "local_llm"],
                "code_review": ["claude_code", "local_llm"],
                "debugging": ["claude_code", "local_llm"],
                "best_practices": ["claude_code", "local_llm"],
                "summarization": ["claude_code", "local_llm"],
                "general": ["local_llm", "claude_code"],
            },
        )

        # Privacy settings
        self.privacy_mode = self.config.get("privacy_mode", "balanced")
        self.cloud_enabled = self.config.get("cloud_enabled", True)

    def add_provider(self, name: str, provider: ILLMProvider):
        """Add a new LLM provider."""
        self.providers[name] = provider
        self.logger.info(f"Added LLM provider: {name}")

    def _get_provider_for_task(
        self, task_type: str, prefer_cloud: bool = False
    ) -> Optional[ILLMProvider]:
        """
        Get the appropriate provider for a given task type.

        Args:
            task_type: Type of task (e.g., "code_generation")
            prefer_cloud: Whether to prefer cloud providers

        Returns:
            Provider instance or None
        """
        # Check privacy settings
        if self.privacy_mode == "strict" and prefer_cloud:
            self.logger.info("Privacy mode is strict; using local providers only")
            prefer_cloud = False

        if not self.cloud_enabled and prefer_cloud:
            self.logger.info("Cloud providers disabled; using local providers only")
            prefer_cloud = False

        # Get provider preference order for the task
        provider_order = self.task_routing.get(task_type, ["local_llm"])

        # Reorder based on cloud preference
        if prefer_cloud:
            # Move cloud providers to the front
            cloud_providers = [
                p for p in provider_order if "cloud" in p or "claude" in p
            ]
            local_providers = [p for p in provider_order if p not in cloud_providers]
            provider_order = cloud_providers + local_providers

        # Find first available provider
        for provider_name in provider_order:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if provider.is_available():
                    self.logger.info(
                        f"Using provider '{provider_name}' for task '{task_type}'"
                    )
                    return provider

        # Fallback to default provider
        if self.default_provider and self.default_provider in self.providers:
            provider = self.providers[self.default_provider]
            if provider.is_available():
                self.logger.info(
                    f"Using default provider '{self.default_provider}' for task '{task_type}'"
                )
                return provider

        self.logger.error(f"No available provider found for task '{task_type}'")
        return None

    def _should_use_cloud(
        self, task_type: str, content_sensitivity: str = "normal"
    ) -> bool:
        """
        Determine whether to use cloud providers based on task and content.

        Args:
            task_type: Type of task
            content_sensitivity: Sensitivity level ("low", "normal", "high")

        Returns:
            True if cloud should be used
        """
        # High sensitivity content should always stay local
        if content_sensitivity == "high":
            return False

        # Strict privacy mode always uses local
        if self.privacy_mode == "strict":
            return False

        # For complex tasks, prefer cloud if enabled
        complex_tasks = [
            "code_generation",
            "code_review",
            "debugging",
            "best_practices",
        ]
        if task_type in complex_tasks and self.cloud_enabled:
            return True

        # Default to local for normal sensitivity
        return content_sensitivity == "low" and self.cloud_enabled

    def ask(
        self,
        prompt: str,
        context: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Ask a general question to an LLM.

        Args:
            prompt: The question or prompt
            context: Optional context
            provider_name: Optional specific provider to use

        Returns:
            Tuple of (success, response)
        """
        try:
            # Use specified provider or find appropriate one
            if provider_name and provider_name in self.providers:
                provider = self.providers[provider_name]
            else:
                provider = self._get_provider_for_task("general")

            if not provider:
                return False, "No available LLM provider found"

            return provider.ask(prompt, context)

        except Exception as e:
            self.logger.error(f"Error in ask: {e}")
            return False, str(e)

    def generate_code(
        self,
        prompt: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        prefer_cloud: Optional[bool] = None,
        content_sensitivity: str = "normal",
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Generate code with intelligent provider selection.

        Args:
            prompt: The code generation prompt
            language: Target programming language
            context: Additional context
            session_id: Optional session ID
            prefer_cloud: Override for cloud preference
            content_sensitivity: Sensitivity level of content

        Returns:
            Tuple of (success, generated_code_or_error)
        """
        try:
            # Determine cloud usage
            use_cloud = (
                prefer_cloud
                if prefer_cloud is not None
                else self._should_use_cloud("code_generation", content_sensitivity)
            )

            # Get appropriate provider
            provider = self._get_provider_for_task("code_generation", use_cloud)

            if not provider or not isinstance(provider, ICodeLLMProvider):
                return False, "No suitable code generation provider available"

            return provider.generate_code(prompt, language, context, session_id)

        except Exception as e:
            self.logger.error(f"Error in generate_code: {e}")
            return False, str(e)

    def review_code(
        self,
        code: str,
        language: Optional[str] = None,
        instruction: Optional[str] = None,
        session_id: Optional[str] = None,
        prefer_cloud: Optional[bool] = None,
        content_sensitivity: str = "normal",
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Review code with intelligent provider selection.

        Args:
            code: The code to review
            language: Programming language
            instruction: Specific review instructions
            session_id: Optional session ID
            prefer_cloud: Override for cloud preference
            content_sensitivity: Sensitivity level of content

        Returns:
            Tuple of (success, review_feedback_or_error)
        """
        try:
            # Determine cloud usage
            use_cloud = (
                prefer_cloud
                if prefer_cloud is not None
                else self._should_use_cloud("code_review", content_sensitivity)
            )

            # Get appropriate provider
            provider = self._get_provider_for_task("code_review", use_cloud)

            if not provider or not isinstance(provider, ICodeLLMProvider):
                return False, "No suitable code review provider available"

            return provider.review_code(code, language, instruction, session_id)

        except Exception as e:
            self.logger.error(f"Error in review_code: {e}")
            return False, str(e)

    def debug_code(
        self,
        code: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        session_id: Optional[str] = None,
        prefer_cloud: Optional[bool] = None,
    ) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Debug code with intelligent provider selection.

        Args:
            code: The code with errors
            error_message: The error message
            stack_trace: Optional stack trace
            session_id: Optional session ID
            prefer_cloud: Override for cloud preference

        Returns:
            Tuple of (success, debug_suggestions_or_error)
        """
        try:
            # Debugging often benefits from cloud resources
            use_cloud = (
                prefer_cloud
                if prefer_cloud is not None
                else self._should_use_cloud("debugging", "normal")
            )

            # Get appropriate provider
            provider = self._get_provider_for_task("debugging", use_cloud)

            if not provider or not isinstance(provider, ICodeLLMProvider):
                return False, "No suitable debugging provider available"

            return provider.debug_code(code, error_message, stack_trace, session_id)

        except Exception as e:
            self.logger.error(f"Error in debug_code: {e}")
            return False, str(e)

    def ask_best_practices(
        self,
        query: str,
        language: Optional[str] = None,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        prefer_cloud: Optional[bool] = None,
    ) -> Tuple[bool, str]:
        """
        Ask for best practices with intelligent provider selection.

        Args:
            query: The technical question
            language: Optional programming language context
            context: Additional context
            session_id: Optional session ID
            prefer_cloud: Override for cloud preference

        Returns:
            Tuple of (success, best_practices_advice)
        """
        try:
            # Best practices benefit from comprehensive knowledge
            use_cloud = (
                prefer_cloud
                if prefer_cloud is not None
                else self._should_use_cloud("best_practices", "low")
            )

            # Get appropriate provider
            provider = self._get_provider_for_task("best_practices", use_cloud)

            if not provider or not isinstance(provider, ITechnicalLLMProvider):
                return False, "No suitable technical guidance provider available"

            return provider.ask_best_practices(query, language, context, session_id)

        except Exception as e:
            self.logger.error(f"Error in ask_best_practices: {e}")
            return False, str(e)

    def summarize_text(
        self,
        text: str,
        focus: Optional[str] = None,
        max_length: Optional[int] = None,
        session_id: Optional[str] = None,
        prefer_cloud: Optional[bool] = None,
        content_sensitivity: str = "normal",
    ) -> Tuple[bool, str]:
        """
        Summarize text with intelligent provider selection.

        Args:
            text: The text to summarize
            focus: Optional focus area
            max_length: Optional maximum length
            session_id: Optional session ID
            prefer_cloud: Override for cloud preference
            content_sensitivity: Sensitivity level of content

        Returns:
            Tuple of (success, summary)
        """
        try:
            # Determine cloud usage based on content sensitivity
            use_cloud = (
                prefer_cloud
                if prefer_cloud is not None
                else self._should_use_cloud("summarization", content_sensitivity)
            )

            # Get appropriate provider
            provider = self._get_provider_for_task("summarization", use_cloud)

            if not provider or not isinstance(provider, ITechnicalLLMProvider):
                return False, "No suitable summarization provider available"

            return provider.summarize_text(text, focus, max_length, session_id)

        except Exception as e:
            self.logger.error(f"Error in summarize_text: {e}")
            return False, str(e)

    def update_privacy_settings(
        self,
        privacy_mode: str,
        cloud_enabled: bool,
    ):
        """
        Update privacy settings for the interface.

        Args:
            privacy_mode: Privacy mode ("strict", "balanced", "relaxed")
            cloud_enabled: Whether cloud providers are enabled
        """
        self.privacy_mode = privacy_mode
        self.cloud_enabled = cloud_enabled
        self.logger.info(
            f"Updated privacy settings: mode={privacy_mode}, cloud={cloud_enabled}"
        )

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all configured providers."""
        status = {}

        for name, provider in self.providers.items():
            try:
                is_available = provider.is_available()
                is_cloud = "cloud" in name.lower() or "claude" in name.lower()
                supports_code = isinstance(provider, ICodeLLMProvider)
                supports_technical = isinstance(provider, ITechnicalLLMProvider)

                status[name] = {
                    "available": is_available,
                    "is_cloud": is_cloud,
                    "supports_code": supports_code,
                    "supports_technical": supports_technical,
                    "class": provider.__class__.__name__,
                }
            except Exception as e:
                status[name] = {
                    "available": False,
                    "error": str(e),
                }

        return status
