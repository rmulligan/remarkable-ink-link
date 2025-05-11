"""Content processor for InkLink.

This module provides the base classes for content processing.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

# Type variable for pipeline input and output
T = TypeVar("T")
U = TypeVar("U")


class PipelineContext:
    """Context for pipeline execution."""

    def __init__(
        self,
        content: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
        url: str = "",
        **kwargs
    ):
        """
        Initialize with content, metadata, and additional context.

        Args:
            content: Content to process
            metadata: Additional metadata
            url: Source URL
            **kwargs: Additional context parameters
        """
        self.content = content or {}
        self.metadata = metadata or {}
        self.url = url
        self.artifacts = {}  # Intermediate artifacts
        self.errors = []  # Errors during processing

        # Add additional context parameters
        for key, value in kwargs.items():
            setattr(self, key, value)

    def add_artifact(self, name: str, artifact: Any) -> None:
        """
        Add an artifact to the context.

        Args:
            name: Artifact name
            artifact: The artifact
        """
        self.artifacts[name] = artifact

    def get_artifact(self, name: str, default: Any = None) -> Any:
        """
        Get an artifact from the context.

        Args:
            name: Artifact name
            default: Default value if artifact doesn't exist

        Returns:
            The artifact or default value
        """
        return self.artifacts.get(name, default)

    def add_error(self, error: str, processor: str = None) -> None:
        """
        Add an error to the context.

        Args:
            error: Error message
            processor: Name of the processor that caused the error
        """
        self.errors.append({"message": error, "processor": processor})

    def has_errors(self) -> bool:
        """
        Check if the context has errors.

        Returns:
            True if there are errors, False otherwise
        """
        return len(self.errors) > 0


class Processor(Generic[T, U], ABC):
    """Base class for content processors."""

    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context.

        Args:
            context: Pipeline context

        Returns:
            Updated pipeline context
        """
        pass

    def __str__(self) -> str:
        """
        Get string representation.

        Returns:
            Class name
        """
        return self.__class__.__name__
