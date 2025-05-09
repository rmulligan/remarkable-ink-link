from pydantic import BaseModel, Field
import os
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class HCLResourceConfig(BaseModel):
    resource_type: str = Field(..., description="Type of the HCL resource")
    resource_name: str = Field(..., description="Name of the HCL resource")
    attributes: dict = Field(default_factory=dict, description="Resource attributes")


# Default configuration dictionary for InkLink


CONFIG = {
    # Server settings
    "HOST": os.environ.get("INKLINK_HOST", "0.0.0.0"),
    "PORT": int(os.environ.get("INKLINK_PORT", 9999)),
    # File paths
    "TEMP_DIR": os.environ.get("INKLINK_TEMP", os.path.join(BASE_DIR, "temp")),
    "OUTPUT_DIR": os.environ.get("INKLINK_OUTPUT", os.path.join(BASE_DIR, "output")),
    # External tools
    "RMAPI_PATH": os.environ.get("INKLINK_RMAPI", "/usr/local/bin/rmapi"),
    "DRAWJ2D_PATH": os.environ.get("INKLINK_DRAWJ2D", "/usr/local/bin/drawj2d"),
    # Remarkable settings
    # Default remote folder on reMarkable device
    "RM_FOLDER": os.environ.get("INKLINK_RM_FOLDER", "InkLink"),
    # Device model: "pro" for reMarkable Pro, "rm2" for reMarkable 2
    # Can be overridden via INKLINK_RM_MODEL env var
    "REMARKABLE_MODEL": os.environ.get("INKLINK_RM_MODEL", "pro").lower(),
    # Remarkable Pro page dimensions (portrait mode)
    "PAGE_WIDTH": int(os.environ.get("INKLINK_PAGE_WIDTH", 1872)),
    "PAGE_HEIGHT": int(os.environ.get("INKLINK_PAGE_HEIGHT", 2404)),
    "PAGE_MARGIN": int(os.environ.get("INKLINK_PAGE_MARGIN", 100)),
    # Font configuration
    "HEADING_FONT": os.environ.get("INKLINK_HEADING_FONT", "Liberation Sans"),
    "BODY_FONT": os.environ.get("INKLINK_BODY_FONT", "Liberation Sans"),
    "CODE_FONT": os.environ.get("INKLINK_CODE_FONT", "DejaVu Sans Mono"),
    # Retry settings
    "MAX_RETRIES": int(os.environ.get("INKLINK_MAX_RETRIES", 3)),
    "RETRY_DELAY": int(os.environ.get("INKLINK_RETRY_DELAY", 2)),  # seconds
    # Logging
    "LOG_LEVEL": os.environ.get("INKLINK_LOG_LEVEL", "INFO"),
    "LOG_FILE": os.environ.get("INKLINK_LOG_FILE", "inklink.log"),
    # PDF rendering mode: "outline" for vector outlines via drawj2d or "raster" for PNG rasterization
    "PDF_RENDER_MODE": os.environ.get("INKLINK_PDF_RENDER_MODE", "outline"),
    # MyScript iink SDK configuration
    "MYSCRIPT_APP_KEY": os.environ.get("MYSCRIPT_APP_KEY", ""),
    "MYSCRIPT_HMAC_KEY": os.environ.get("MYSCRIPT_HMAC_KEY", ""),
    # OpenAI settings
    "OPENAI_MODEL": os.environ.get("INKLINK_OPENAI_MODEL", "gpt-3.5-turbo"),
    "OPENAI_SYSTEM_PROMPT": os.environ.get(
        "INKLINK_OPENAI_SYSTEM_PROMPT", "You are a helpful assistant."
    ),
}

# Ensure required directories exist
os.makedirs(CONFIG["TEMP_DIR"], exist_ok=True)
os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)

# Auto-detect local ddvk rmapi fork if present
try:
    from shutil import which
except ImportError:
    which = None
# Auto-detect local ddvk rmapi fork if present
ddvk_candidate = os.path.expanduser("~/Projects/rmapi/rmapi")
if os.path.exists(ddvk_candidate) and os.access(ddvk_candidate, os.X_OK):
    CONFIG["RMAPI_PATH"] = ddvk_candidate
# Fallback: detect rmapi in PATH if default path not found or not executable
try:
    from shutil import which

    if not os.path.exists(CONFIG.get("RMAPI_PATH", "")) or not os.access(
        CONFIG.get("RMAPI_PATH", ""), os.X_OK
    ):
        path_rmapi = which("rmapi")
        if path_rmapi:
            CONFIG["RMAPI_PATH"] = path_rmapi
except ImportError:
    pass
# Detect drawj2d in PATH
if which:
    drawj2d_path = which("drawj2d")
    if drawj2d_path:
        CONFIG["DRAWJ2D_PATH"] = drawj2d_path

# Configure logging
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging():
    """Configure the logging system."""
    log_level_str = CONFIG["LOG_LEVEL"].upper()
    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
    log_file = CONFIG["LOG_FILE"]

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
    )

    # Return the root logger
    return logging.getLogger()
