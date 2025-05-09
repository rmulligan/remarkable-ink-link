"""Base adapter interfaces for InkLink.

This module provides base adapter interfaces for external services.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union, Tuple


class Adapter(ABC):
    """Base interface for all adapters."""

    @abstractmethod
    def ping(self) -> bool:
        """
        Check if the external service is available.

        Returns:
            True if available, False otherwise
        """
        pass
