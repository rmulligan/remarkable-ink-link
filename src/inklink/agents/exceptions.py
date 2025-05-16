"""Custom exceptions for the agent framework."""


class AgentError(Exception):
    """Base exception for agent framework errors."""

    pass


class AgentInitializationError(AgentError):
    """Raised when an agent fails to initialize."""

    pass


class AgentCommunicationError(AgentError):
    """Raised when inter-agent communication fails."""

    pass


class AgentStateError(AgentError):
    """Raised when an invalid agent state transition is attempted."""

    pass


class OllamaError(Exception):
    """Base exception for Ollama-related errors."""

    pass


class OllamaConnectionError(OllamaError):
    """Raised when connection to Ollama fails."""

    pass


class OllamaQueryError(OllamaError):
    """Raised when an Ollama query fails."""

    pass


class OllamaModelError(OllamaError):
    """Raised when model operations fail."""

    pass


class LimitlessError(Exception):
    """Base exception for Limitless-related errors."""

    pass


class LimitlessConnectionError(LimitlessError):
    """Raised when connection to Limitless fails."""

    pass


class LimitlessDataError(LimitlessError):
    """Raised when Limitless data processing fails."""

    pass


class ConfigurationError(Exception):
    """Raised when configuration loading or parsing fails."""

    pass


class StorageError(Exception):
    """Raised when storage operations fail."""

    pass
