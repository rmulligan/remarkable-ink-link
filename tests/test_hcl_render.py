import pytest
from inklink.config import HCLResourceConfig
from inklink.utils.hcl_render import render_hcl_resource


def test_render_hcl_resource_basic():
    config = HCLResourceConfig(
        resource_type="aws_instance",
        resource_name="example",
        attributes={"ami": "ami-123456", "instance_type": "t2.micro"},
    )
    hcl = render_hcl_resource(config)
    assert 'resource "aws_instance" "example"' in hcl
    assert 'ami = "ami-123456"' in hcl
    assert 'instance_type = "t2.micro"' in hcl
