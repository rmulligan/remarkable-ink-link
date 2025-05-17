#!/usr/bin/env python
"""
Extended Service Manager for LLM Providers.

This module extends the base ServiceManager to include LLM provider
management and intelligent routing.
"""

import logging
from typing import Any, Dict, Optional

from inklink.config import CONFIG
from inklink.services.service_manager import ServiceManager
from inklink.services.llm_interface import UnifiedLLMInterface
from inklink.providers.claude_code_provider import ClaudeCodeProvider
from inklink.adapters.claude_code_adapter import ClaudeCodeAdapter


class LLMServiceManager(ServiceManager):
    """Extended service manager that includes LLM provider management."""

    def __init__(
        self,
        # Base service dependencies
        qr_service=None,
        pdf_service=None,
        web_scraper=None,
        document_service=None,
        remarkable_service=None,
        # LLM provider dependencies
        claude_code_provider=None,
        local_llm_provider=None,
        llm_interface=None,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the extended service manager.

        Args:
            Base service dependencies...
            claude_code_provider: Optional Claude Code provider instance
            local_llm_provider: Optional local LLM provider instance
            llm_interface: Optional unified LLM interface instance
            config: Optional configuration dictionary
        """
        # Initialize base services
        super().__init__(
            qr_service=qr_service,
            pdf_service=pdf_service,
            web_scraper=web_scraper,
            document_service=document_service,
            remarkable_service=remarkable_service,
        )

        self.logger = logging.getLogger(__name__)
        self.config = config or CONFIG

        # Initialize LLM providers
        self._initialize_llm_providers(
            claude_code_provider=claude_code_provider,
            local_llm_provider=local_llm_provider,
            llm_interface=llm_interface,
        )

    def _initialize_llm_providers(
        self,
        claude_code_provider=None,
        local_llm_provider=None,
        llm_interface=None,
    ):
        """Initialize LLM providers and unified interface."""
        # Initialize Claude Code provider if not provided
        if claude_code_provider:
            self.claude_code_provider = claude_code_provider
        else:
            # Check if Claude Code is configured and available
            if self.config.get("CLAUDE_CODE_COMMAND"):
                try:
                    adapter = ClaudeCodeAdapter(
                        claude_command=self.config.get("CLAUDE_CODE_COMMAND"),
                        model=self.config.get("CLAUDE_CODE_MODEL"),
                        timeout=self.config.get("CLAUDE_CODE_TIMEOUT", 120),
                        max_tokens=self.config.get("CLAUDE_CODE_MAX_TOKENS", 8000),
                        temperature=self.config.get("CLAUDE_CODE_TEMPERATURE", 0.7),
                        cache_dir=self.config.get("CLAUDE_CODE_CACHE_DIR"),
                    )

                    if adapter.is_available():
                        self.claude_code_provider = ClaudeCodeProvider(
                            adapter=adapter,
                            config=self.config,
                        )
                        self.logger.info(
                            "Claude Code provider initialized successfully"
                        )
                    else:
                        self.claude_code_provider = None
                        self.logger.warning("Claude Code CLI not available")
                except Exception as e:
                    self.claude_code_provider = None
                    self.logger.error(f"Failed to initialize Claude Code provider: {e}")
            else:
                self.claude_code_provider = None
                self.logger.info("Claude Code not configured")

        # Initialize local LLM provider if not provided
        self.local_llm_provider = local_llm_provider
        # TODO: Add local LLM provider initialization (e.g., Ollama)

        # Initialize unified LLM interface
        if llm_interface:
            self.llm_interface = llm_interface
        else:
            # Create providers dictionary
            providers = {}

            if self.claude_code_provider:
                providers["claude_code"] = self.claude_code_provider

            if self.local_llm_provider:
                providers["local_llm"] = self.local_llm_provider

            # Configure enhanced task routing with privacy and complexity considerations
            task_routing = {
                # Code-related tasks: prioritize Claude Code
                "code_generation": ["claude_code", "local_llm"],
                "code_review": ["claude_code", "local_llm"],
                "debugging": ["claude_code", "local_llm"],
                "best_practices": ["claude_code", "local_llm"],
                "technical_summary": ["claude_code", "local_llm"],
                # Structured text tasks: local first for performance
                "summary": ["local_llm", "claude_code"],
                "extraction": ["local_llm", "claude_code"],
                "formatting": ["local_llm", "claude_code"],
                # General queries: local first for privacy
                "general": ["local_llm", "claude_code"],
                "chat": ["local_llm", "claude_code"],
                # Research and complex analysis: Claude Code for capabilities
                "research": ["claude_code", "local_llm"],
                "analysis": ["claude_code", "local_llm"],
                "architecture": ["claude_code", "local_llm"],
            }

            # Privacy routing overrides based on content sensitivity
            privacy_routing = {
                "private": [
                    "local_llm"
                ],  # Privacy-sensitive content only goes to local
                "corporate": [
                    "local_llm",
                    "claude_code",
                ],  # Corporate allows cloud with caution
                "public": [
                    "claude_code",
                    "local_llm",
                ],  # Public content prefers cloud capabilities
            }

            # User preference settings
            user_preferences = {
                "prefer_cloud": self.config.get("AI_PREFER_CLOUD", True),
                "fallback_enabled": self.config.get("AI_FALLBACK_ENABLED", True),
                "complexity_threshold": self.config.get(
                    "AI_COMPLEXITY_THRESHOLD", 0.7
                ),  # 0-1 scale for task complexity
                "auto_classify": self.config.get("AI_AUTO_CLASSIFY", True),
            }

            # Create unified interface with enhanced configuration
            self.llm_interface = UnifiedLLMInterface(
                providers=providers,
                default_provider=(
                    "claude_code" if self.claude_code_provider else "local_llm"
                ),
                config={
                    "task_routing": task_routing,
                    "privacy_routing": privacy_routing,
                    "user_preferences": user_preferences,
                    "privacy_mode": self.config.get(
                        "AI_ROUTING_PRIVACY_MODE", "balanced"
                    ),
                    "cloud_enabled": self.config.get("AI_ROUTING_CLOUD_ENABLED", True),
                    "max_retries": self.config.get("AI_MAX_RETRIES", 3),
                    "timeout_seconds": self.config.get("AI_TIMEOUT_SECONDS", 120),
                },
            )

            self.logger.info(
                f"Unified LLM interface initialized with {len(providers)} providers"
            )

    def get_llm_provider(self, name: str):
        """
        Get a specific LLM provider by name.

        Args:
            name: Provider name ("claude_code", "local_llm", etc.)

        Returns:
            Provider instance or None
        """
        if name == "claude_code":
            return self.claude_code_provider
        elif name == "local_llm":
            return self.local_llm_provider
        else:
            return None

    def get_llm_interface(self) -> UnifiedLLMInterface:
        """Get the unified LLM interface."""
        return self.llm_interface

    def get_services(self):
        """
        Get all services including LLM providers.

        Returns:
            Dictionary of all services
        """
        services = super().get_services()

        # Add LLM services
        services.update(
            {
                "claude_code_provider": self.claude_code_provider,
                "local_llm_provider": self.local_llm_provider,
                "llm_interface": self.llm_interface,
            }
        )

        return services

    def get_llm_status(self) -> Dict[str, Any]:
        """
        Get status of all LLM providers.

        Returns:
            Dictionary with provider status information
        """
        if self.llm_interface:
            return self.llm_interface.get_provider_status()
        else:
            return {
                "error": "LLM interface not initialized",
                "providers": {},
            }

    def update_llm_privacy_settings(
        self,
        privacy_mode: str,
        cloud_enabled: bool,
    ):
        """
        Update privacy settings for LLM routing.

        Args:
            privacy_mode: Privacy mode ("strict", "balanced", "relaxed")
            cloud_enabled: Whether cloud providers are enabled
        """
        if self.llm_interface:
            self.llm_interface.update_privacy_settings(privacy_mode, cloud_enabled)
            self.logger.info(
                f"Updated LLM privacy settings: mode={privacy_mode}, cloud={cloud_enabled}"
            )
        else:
            self.logger.warning(
                "Cannot update privacy settings: LLM interface not initialized"
            )

    def route_task(
        self,
        task_type: str,
        content: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Route a task to the appropriate LLM provider based on type and content.

        Args:
            task_type: Type of task (code_generation, debugging, etc.)
            content: Content to process
            **kwargs: Additional arguments for the task

        Returns:
            Dictionary with provider and routing decision
        """
        if not self.llm_interface:
            return {
                "error": "LLM interface not initialized",
                "provider": None,
            }

        # Analyze content for privacy sensitivity if configured
        privacy_level = "public"  # Default
        if self.llm_interface.config.get("user_preferences", {}).get("auto_classify"):
            privacy_level = self._classify_content_privacy(content)

        # Determine complexity for intelligent routing
        complexity = self._assess_task_complexity(task_type, content)

        # Get routing configuration
        task_routing = self.llm_interface.config.get("task_routing", {})
        privacy_routing = self.llm_interface.config.get("privacy_routing", {})

        # Apply privacy routing if it overrides task routing
        if privacy_level in privacy_routing:
            preferred_providers = privacy_routing[privacy_level]
        else:
            preferred_providers = task_routing.get(
                task_type, ["local_llm", "claude_code"]
            )

        # Adjust based on complexity and user preferences
        user_prefs = self.llm_interface.config.get("user_preferences", {})
        prefer_cloud = user_prefs.get("prefer_cloud", True)
        complexity_threshold = user_prefs.get("complexity_threshold", 0.7)

        # If task is complex and cloud is preferred, prioritize Claude Code
        if (
            complexity > complexity_threshold
            and prefer_cloud
            and privacy_level != "private"
        ):
            if "claude_code" in preferred_providers:
                # Move claude_code to front
                preferred_providers = ["claude_code"] + [
                    p for p in preferred_providers if p != "claude_code"
                ]

        # Try providers in order
        selected_provider = None
        for provider_name in preferred_providers:
            provider = self.llm_interface.providers.get(provider_name)
            if provider and provider.is_available():
                selected_provider = provider_name
                break

        # Fallback to any available provider if enabled
        if not selected_provider and user_prefs.get("fallback_enabled", True):
            for name, provider in self.llm_interface.providers.items():
                if provider.is_available():
                    selected_provider = name
                    break

        return {
            "provider": selected_provider,
            "privacy_level": privacy_level,
            "complexity": complexity,
            "routing_path": preferred_providers,
            "reasoning": self._explain_routing_decision(
                task_type, privacy_level, complexity, selected_provider
            ),
        }

    def _classify_content_privacy(self, content: str) -> str:
        """
        Classify content privacy level based on keywords and patterns.

        Args:
            content: Content to classify

        Returns:
            Privacy level: "private", "corporate", or "public"
        """
        # Simple keyword-based classification
        private_keywords = [
            "password",
            "secret",
            "private",
            "confidential",
            "personal",
            "ssn",
            "credit card",
            "api key",
            "token",
        ]
        corporate_keywords = [
            "proprietary",
            "internal",
            "company",
            "corporate",
            "business",
            "client",
            "customer",
        ]

        content_lower = content.lower()

        # Check for private content
        for keyword in private_keywords:
            if keyword in content_lower:
                return "private"

        # Check for corporate content
        for keyword in corporate_keywords:
            if keyword in content_lower:
                return "corporate"

        # Default to public
        return "public"

    def _assess_task_complexity(self, task_type: str, content: str) -> float:
        """
        Assess task complexity on a scale of 0 to 1.

        Args:
            task_type: Type of task
            content: Content to process

        Returns:
            Complexity score between 0 and 1
        """
        # Base complexity by task type
        complexity_scores = {
            "code_generation": 0.8,
            "code_review": 0.7,
            "debugging": 0.9,
            "best_practices": 0.6,
            "research": 0.8,
            "analysis": 0.7,
            "architecture": 0.9,
            "summary": 0.3,
            "extraction": 0.2,
            "formatting": 0.1,
            "general": 0.5,
            "chat": 0.3,
        }

        base_complexity = complexity_scores.get(task_type, 0.5)

        # Adjust based on content length
        content_length = len(content)
        if content_length > 5000:
            base_complexity += 0.1
        elif content_length > 10000:
            base_complexity += 0.2

        # Adjust based on code presence
        if "```" in content or "def " in content or "class " in content:
            base_complexity += 0.1

        # Cap at 1.0
        return min(base_complexity, 1.0)

    def _explain_routing_decision(
        self,
        task_type: str,
        privacy_level: str,
        complexity: float,
        selected_provider: Optional[str],
    ) -> str:
        """
        Explain the routing decision for transparency.

        Args:
            task_type: Type of task
            privacy_level: Content privacy level
            complexity: Task complexity score
            selected_provider: Selected provider name

        Returns:
            Human-readable explanation
        """
        if not selected_provider:
            return "No available provider found for this task."

        explanation = f"Routed {task_type} task to {selected_provider}. "

        if privacy_level == "private":
            explanation += (
                "Content classified as private, restricted to local providers. "
            )
        elif privacy_level == "corporate":
            explanation += (
                "Content classified as corporate, prefer local but allow cloud. "
            )

        if complexity > 0.7:
            explanation += f"High complexity ({complexity:.2f}) task prioritizes capable cloud providers. "
        elif complexity < 0.3:
            explanation += (
                f"Low complexity ({complexity:.2f}) task prioritizes local providers. "
            )

        return explanation

    def reload_providers(self):
        """Reload and reinitialize LLM providers."""
        self.logger.info("Reloading LLM providers...")

        # Re-initialize providers
        self._initialize_llm_providers()

        # Log status
        status = self.get_llm_status()
        available_count = sum(
            1 for p in status.values() if isinstance(p, dict) and p.get("available")
        )
        self.logger.info(f"Reloaded {available_count} available LLM providers")

    def __repr__(self):
        """String representation of the service manager."""
        status = self.get_llm_status()
        available_providers = [
            name
            for name, info in status.items()
            if isinstance(info, dict) and info.get("available")
        ]
        return f"LLMServiceManager(providers={available_providers})"
