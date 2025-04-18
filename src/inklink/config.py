
"""
Configuration management for Pi Share Receiver.

This module provides configuration settings from environment variables
with reasonable defaults.
"""

import os
import logging

# Path configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load configuration from environment variables with defaults
CONFIG = {
    # Server settings
    'HOST': os.environ.get('PI_SHARE_HOST', '0.0.0.0'),
    'PORT': int(os.environ.get('PI_SHARE_PORT', 9999)),

    # File paths
    'TEMP_DIR': os.environ.get('PI_SHARE_TEMP', os.path.join(BASE_DIR, 'temp')),
    'OUTPUT_DIR': os.environ.get('PI_SHARE_OUTPUT', os.path.join(BASE_DIR, 'output')),

    # External tools
    'RMAPI_PATH': os.environ.get('PI_SHARE_RMAPI', '/usr/local/bin/rmapi'),
    'DRAWJ2D_PATH': os.environ.get('PI_SHARE_DRAWJ2D', '/usr/local/bin/drawj2d'),

    # Remarkable settings
    'RM_FOLDER': os.environ.get('PI_SHARE_RM_FOLDER', '/'),

    # Remarkable Pro page dimensions (portrait mode)
    'PAGE_WIDTH': int(os.environ.get('PI_SHARE_PAGE_WIDTH', 1872)),
    'PAGE_HEIGHT': int(os.environ.get('PI_SHARE_PAGE_HEIGHT', 2404)),
    'PAGE_MARGIN': int(os.environ.get('PI_SHARE_PAGE_MARGIN', 100)),

    # Font configuration
    'HEADING_FONT': os.environ.get('PI_SHARE_HEADING_FONT', 'Liberation Sans'),
    'BODY_FONT': os.environ.get('PI_SHARE_BODY_FONT', 'Liberation Sans'),
    'CODE_FONT': os.environ.get('PI_SHARE_CODE_FONT', 'DejaVu Sans Mono'),

    # Retry settings
    'MAX_RETRIES': int(os.environ.get('PI_SHARE_MAX_RETRIES', 3)),
    'RETRY_DELAY': int(os.environ.get('PI_SHARE_RETRY_DELAY', 2)),  # seconds

    # Logging
    'LOG_LEVEL': os.environ.get('PI_SHARE_LOG_LEVEL', 'INFO'),
    'LOG_FILE': os.environ.get('PI_SHARE_LOG_FILE', 'pi_share_receiver.log'),
}

# Ensure required directories exist
os.makedirs(CONFIG['TEMP_DIR'], exist_ok=True)
os.makedirs(CONFIG['OUTPUT_DIR'], exist_ok=True)

# Configure logging
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

def setup_logging():
    """Configure the logging system."""
    log_level_str = CONFIG['LOG_LEVEL'].upper()
    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
    log_file = CONFIG['LOG_FILE']

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )

    # Return the root logger
    return logging.getLogger()

