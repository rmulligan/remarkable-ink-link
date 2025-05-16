"""Agent configuration management."""

import os
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional

import yaml


class ConfigLoader:
    """Loads and manages agent configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the configuration loader."""
        self.config_path = config_path or Path(__file__).parent / "agent_config.yaml"
        self._config: Optional[Dict[str, Any]] = None
        self._env_template = Template

    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file with environment variable substitution."""
        if self._config is not None:
            return self._config

        with open(self.config_path, "r") as f:
            config_str = f.read()

        # Substitute environment variables
        config_str = self._substitute_env_vars(config_str)

        # Parse YAML
        self._config = yaml.safe_load(config_str)
        return self._config

    @staticmethod
    def _substitute_env_vars(config_str: str) -> str:
        """Substitute environment variables in the format ${VAR} or ${VAR:default}."""
        import re

        # Pattern for ${VAR} or ${VAR:default}
        pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) or ""
            return os.environ.get(var_name, default_value)

        return re.sub(pattern, replacer, config_str)

    def get_framework_config(self) -> Dict[str, Any]:
        """Get framework-wide configuration."""
        config = self.load()
        return config.get("framework", {})

    def get_adapter_config(self, adapter_name: str) -> Dict[str, Any]:
        """Get configuration for a specific adapter."""
        config = self.load()
        return config.get("adapters", {}).get(adapter_name, {})

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent."""
        config = self.load()
        return config.get("agents", {}).get(agent_name, {})

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration."""
        config = self.load()
        return config.get("monitoring", {})

    def get_all_enabled_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all enabled agents and their configurations."""
        config = self.load()
        agents = config.get("agents", {})
        return {
            name: agent_config
            for name, agent_config in agents.items()
            if agent_config.get("enabled", False)
        }


# Global config instance
config_loader = ConfigLoader()


def get_config() -> ConfigLoader:
    """Get the global configuration loader instance."""
    return config_loader


def load_agent_config(agent_name: str) -> Dict[str, Any]:
    """Convenience function to load a specific agent's configuration."""
    return config_loader.get_agent_config(agent_name)
