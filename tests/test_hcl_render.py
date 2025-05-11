import pytest
import os
import tempfile
from typing import Dict, Any
from inklink.config import HCLResourceConfig
from inklink.utils.hcl_render import render_hcl_resource, create_hcl_from_content


def test_render_hcl_resource_basic():
    """Test rendering HCL resource blocks from configuration."""
    config = HCLResourceConfig(
        resource_type="aws_instance",
        resource_name="example",
        attributes={"ami": "ami-123456", "instance_type": "t2.micro"},
    )
    hcl = render_hcl_resource(config)
    assert 'resource "aws_instance" "example"' in hcl
    assert 'ami = "ami-123456"' in hcl
    assert 'instance_type = "t2.micro"' in hcl


def test_create_hcl_from_content_basic():
    """Test creating HCL content with both default and custom configs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        url = "https://example.com"
        qr_path = os.path.join(temp_dir, "qr.png")
        with open(qr_path, "w") as f:
            f.write("dummy qr")

        content = {"title": "Test Page", "structured_content": []}

        # Test with default config
        hcl_path = create_hcl_from_content(url, qr_path, content, temp_dir)
        assert hcl_path is not None
        assert os.path.exists(hcl_path)

        # Test with custom config
        custom_config: Dict[str, Any] = {
            "PAGE_WIDTH": 1000,
            "PAGE_HEIGHT": 800,
            "PAGE_MARGIN": 50,
            "HEADING_FONT": "Custom Font",
        }

        hcl_path = create_hcl_from_content(
            url, qr_path, content, temp_dir, custom_config
        )
        assert hcl_path is not None
        assert os.path.exists(hcl_path)

        # Check that the custom config values were used
        with open(hcl_path, "r") as f:
            content = f.read()
            assert "page_width: 1000" in content
            assert "page_height: 800" in content
            assert 'font: "Custom Font"' in content
