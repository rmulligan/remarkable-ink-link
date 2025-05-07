from pydantic import BaseModel, Field
import os

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
    "RM_FOLDER": os.environ.get("INKLINK_RM_FOLDER", "/"),
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
}
