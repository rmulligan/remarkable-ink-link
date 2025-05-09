import jinja2
from inklink.config import HCLResourceConfig


def render_hcl_resource(
    config: HCLResourceConfig, template_path: str = "inklink/hcl_templates/main.j2"
) -> str:
    """
    Render an HCL resource using the provided config and Jinja2 template.
    """
    # Simple Jinja2 rendering implementation to replace rmc.render dependency
    try:
        with open(template_path, "r") as f:
            template_str = f.read()
        template = jinja2.Template(template_str)
        return template.render(**config.dict())
    except Exception as e:
        print(f"Error rendering template: {e}")
        # Fallback to basic HCL rendering
        attributes = config.attributes or {}
        result = [f'resource "{config.resource_type}" "{config.resource_name}" {{']
        for key, value in attributes.items():
            if isinstance(value, str):
                result.append(f'  {key} = "{value}"')
            else:
                result.append(f"  {key} = {value}")
        result.append("}")
        return "\n".join(result)
