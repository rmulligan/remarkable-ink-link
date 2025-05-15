from inklink.config import HCLResourceConfig
from inklink.utils.hcl_render import render_hcl_resource


class HCLTemplateService:
    """
    Service for rendering HCL resources using Jinja2 templates and rmc.
    """

    @staticmethod
    def render(
        config: HCLResourceConfig,
        template_path: str = "inklink/hcl_templates/main.j2",
    ) -> str:
        return render_hcl_resource(config, template_path)
