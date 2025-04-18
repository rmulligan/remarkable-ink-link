"""Utility functions for Pi Share Receiver."""

import time
import logging
from typing import Any, Callable, TypeVar, Optional

# Import configuration with proper relative import
try:
    from .config import CONFIG
    MAX_RETRIES = CONFIG.get('MAX_RETRIES', 3)
    RETRY_DELAY = CONFIG.get('RETRY_DELAY', 2)
except ImportError:
    # Fallback to defaults if import fails
    MAX_RETRIES = 3
    RETRY_DELAY = 2

# Set up logger
logger = logging.getLogger(__name__)

# Generic type for function return
T = TypeVar('T')

def retry_operation(operation: Callable[..., T], 
                   *args, 
                   max_retries: Optional[int] = None,
                   retry_delay: Optional[int] = None,
                   operation_name: str = "Operation",
                   **kwargs) -> T:
    """Retry an operation with exponential backoff.
    
    Args:
        operation: Function to retry
        args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts (default: from config)
        retry_delay: Base delay between retries in seconds (default: from config)
        operation_name: Name of the operation for logging
        kwargs: Keyword arguments to pass to the function
            
    Returns:
        The result of the operation if successful
    
    Raises:
        Exception: If the operation fails after all retries
    """
    retries = 0
    last_error = None
    
    # Use provided values or defaults from config
    max_retries = max_retries if max_retries is not None else MAX_RETRIES
    retry_delay = retry_delay if retry_delay is not None else RETRY_DELAY
    
    while retries <= max_retries:
        try:
            if retries > 0:
                logger.info(f"{operation_name}: Retry attempt {retries}/{max_retries}...")
            return operation(*args, **kwargs)
        except Exception as e:
            last_error = e
            retries += 1
            if retries <= max_retries:
                sleep_time = retry_delay * (2 ** (retries - 1))  # Exponential backoff
                logger.warning(f"{operation_name} failed: {str(e)}. Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error(f"{operation_name} failed after {max_retries} retries: {str(e)}")
                raise last_error

def format_error(error_type: str, message: str, details: Any = None) -> str:
    """Format error messages consistently.
    
    Args:
        error_type: Type of error (e.g., "network", "conversion")
        message: Error message
        details: Additional error details (optional)
        
    Returns:
        Formatted error message
    """
    error_msg = f"{error_type.upper()} ERROR: {message}"
    
    if details:
        if isinstance(details, Exception):
            error_msg += f" ({type(details).__name__}: {str(details)})"
        else:
            error_msg += f" ({details})"
            
    return error_msg
