from pydantic import BaseModel, Field

class HCLResourceConfig(BaseModel):
    resource_type: str = Field(..., description="Type of the HCL resource")
    resource_name: str = Field(..., description="Name of the HCL resource")
    attributes: dict = Field(default_factory=dict, description="Resource attributes")
