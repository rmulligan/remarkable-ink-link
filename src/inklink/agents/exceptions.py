"""Custom exceptions for the agent framework."""


class AgentError(Exception):
    """Base exception for agent framework errors."""


class AgentInitializationError(AgentError):
    """Raised when an agent fails to initialize."""


class AgentCommunicationError(AgentError):
    """Raised when inter-agent communication fails."""


class AgentStateError(AgentError):
    """Raised when an invalid agent state transition is attempted."""


class OllamaError(Exception):
    """Base exception for Ollama-related errors."""


class OllamaConnectionError(OllamaError):
    """Raised when connection to Ollama fails."""


class OllamaQueryError(OllamaError):
    """Raised when an Ollama query fails."""


class OllamaModelError(OllamaError):
    """Raised when model operations fail."""


class LimitlessError(Exception):
    """Base exception for Limitless-related errors."""


class LimitlessConnectionError(LimitlessError):
    """Raised when connection to Limitless fails."""


class LimitlessDataError(LimitlessError):
    """Raised when Limitless data processing fails."""


class ConfigurationError(Exception):
    """Raised when configuration loading or parsing fails."""


class StorageError(Exception):
    """Raised when storage operations fail."""
