from rmc.render import render_template
from src.inklink.config import HCLResourceConfig

def render_hcl_resource(config: HCLResourceConfig, template_path: str = "src/inklink/hcl_templates/main.j2") -> str:
    """
    Render an HCL resource using the provided config and Jinja2 template.
    """
    return render_template(template_path, config.dict())