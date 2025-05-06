from pydantic import BaseModel, Field

class HCLResourceConfig(BaseModel):
    resource_type: str = Field(..., description="Type of the HCL resource")
    resource_name: str = Field(..., description="Name of the HCL resource")
    attributes: dict = Field(default_factory=dict, description="Resource attributes")
# Default configuration dictionary for InkLink
CONFIG = {
    "TEMP_DIR": "/tmp/inklink",
    "OUTPUT_DIR": "/tmp/inklink/output",
    "DRAWJ2D_PATH": "/usr/local/bin/drawj2d",
    "RMAPI_PATH": "rmapi",
    "RM_FOLDER": "InkLink",
    "HOST": "0.0.0.0",
    "PORT": 9999,
    "PAGE_WIDTH": 2160,
    "PAGE_HEIGHT": 1620,
    "PAGE_MARGIN": 120,
    "HEADING_FONT": "Liberation Sans",
    "BODY_FONT": "Liberation Sans",
    "CODE_FONT": "DejaVu Sans Mono",
    "MAX_RETRIES": 3,
    "RETRY_DELAY": 2,
    "PDF_RENDER_MODE": "outline"
}
