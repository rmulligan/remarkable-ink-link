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
    "RMAPI_PATH": os.environ.get("INKLINK_RMAPI", "./local-rmapi"),
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
    # PDF rendering mode:
    # - "outline": Uses vector outlines via drawj2d (more accurate but may fail with complex PDFs)
    # - "raster": Uses PNG rasterization (more reliable but lower quality)
    # NOTE: Default changed from "outline" to "raster" in v1.2 for better reliability.
    # Set INKLINK_PDF_RENDER_MODE=outline to use the previous default.
    "PDF_RENDER_MODE": os.environ.get("INKLINK_PDF_RENDER_MODE", "raster"),
    # Default PDF page number and scale for outline embedding (only used when PDF_RENDER_MODE="outline")
    "PDF_PAGE": int(os.environ.get("INKLINK_PDF_PAGE", 1)),
    "PDF_SCALE": float(os.environ.get("INKLINK_PDF_SCALE", 1.0)),
    # Claude CLI configuration
    "CLAUDE_COMMAND": os.environ.get("CLAUDE_COMMAND", "claude"),
    "CLAUDE_MODEL": os.environ.get("CLAUDE_MODEL", ""),
    # Handwriting recognition rendering configuration
    "RM_PAGE_WIDTH": int(os.environ.get("RM_PAGE_WIDTH", 1404)),
    "RM_PAGE_HEIGHT": int(os.environ.get("RM_PAGE_HEIGHT", 1872)),
    "RM_RENDER_DPI": int(os.environ.get("RM_RENDER_DPI", 300)),
    # Claude settings
    "CLAUDE_SYSTEM_PROMPT": os.environ.get(
        "INKLINK_CLAUDE_SYSTEM_PROMPT", "You are a helpful assistant."
    ),
    # Neo4j Knowledge Graph settings
    "NEO4J_URI": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
    "NEO4J_USER": os.environ.get("NEO4J_USER", "neo4j"),
    "NEO4J_PASS": os.environ.get("NEO4J_PASS", "password"),
    "NEO4J_DATABASE": os.environ.get("NEO4J_DATABASE", "neo4j"),
    # Cassidy settings
    "CASSIDY_TAG": os.environ.get("CASSIDY_TAG", "Cass"),
    "CASSIDY_POLLING_INTERVAL": int(os.environ.get("CASSIDY_POLLING_INTERVAL", 60)),
    "CASSIDY_CLAUDE_COMMAND": os.environ.get("CASSIDY_CLAUDE_COMMAND", "claude -c"),
    
    # Lilly settings
    "LILLY_ROOT_DIR": os.environ.get("LILLY_ROOT_DIR", os.path.expanduser("~/dev")),
    "LILLY_TAG": os.environ.get("LILLY_TAG", "Lilly"),
    "LILLY_POLLING_INTERVAL": int(os.environ.get("LILLY_POLLING_INTERVAL", 60)),
    "LILLY_SUBJECT_TAG": os.environ.get("LILLY_SUBJECT_TAG", "Subject"),
    "LILLY_DEFAULT_SUBJECT": os.environ.get("LILLY_DEFAULT_SUBJECT", "General"),
    "LILLY_USE_SUBJECT_DIRS": os.environ.get("LILLY_USE_SUBJECT_DIRS", "true").lower() == "true",
    "LILLY_PRE_FILTER_TAG": os.environ.get("LILLY_PRE_FILTER_TAG", "HasLilly"),
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