"""InkLink Local AI Agent Framework.

Provides a system of always-on local AI assistant agents
with MCP protocol support and Ollama integration.
"""

from .base.agent import LocalAgent
from .base.lifecycle import AgentLifecycle
from .base.registry import AgentRegistry

__all__ = [
    "LocalAgent",
    "AgentRegistry",
    "AgentLifecycle",
]
