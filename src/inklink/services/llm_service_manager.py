#!/usr/bin/env python
"""
Extended Service Manager for LLM Providers.

This module extends the base ServiceManager to include LLM provider
management and intelligent routing.
"""

import logging
from typing import Any, Dict, Optional

from inklink.adapters.claude_code_adapter import ClaudeCodeAdapter
from inklink.config import CONFIG
from inklink.providers.claude_code_provider import ClaudeCodeProvider
from inklink.services.llm_interface import UnifiedLLMInterface
from inklink.services.service_manager import ServiceManager


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

            # Configure task routing
            task_routing = {
                "code_generation": ["claude_code", "local_llm"],
                "code_review": ["claude_code", "local_llm"],
                "debugging": ["claude_code", "local_llm"],
                "best_practices": ["claude_code", "local_llm"],
                "summarization": ["claude_code", "local_llm"],
                "general": ["local_llm", "claude_code"],
            }

            # Create unified interface
            self.llm_interface = UnifiedLLMInterface(
                providers=providers,
                default_provider=(
                    "claude_code" if self.claude_code_provider else "local_llm"
                ),
                config={
                    "task_routing": task_routing,
                    "privacy_mode": self.config.get(
                        "AI_ROUTING_PRIVACY_MODE", "balanced"
                    ),
                    "cloud_enabled": self.config.get("AI_ROUTING_CLOUD_ENABLED", True),
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
