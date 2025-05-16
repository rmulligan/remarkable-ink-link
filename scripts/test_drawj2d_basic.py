#!/usr/bin/env python3
"""Test basic drawj2d functionality for Phase 1."""

import logging
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from inklink.services.drawj2d_service import get_drawj2d_service  # noqa: E402

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_basic_drawj2d():
    """Test basic drawj2d functionality with a simple HCL script."""
    try:
        # Get the drawj2d service
        service = get_drawj2d_service()
        logger.info("Drawj2d service initialized successfully")

        # Create test HCL file
        test_hcl_path = service.create_test_hcl()
        logger.info(f"Created test HCL file: {test_hcl_path}")

        # Process the HCL file
        logger.info("Processing HCL with drawj2d...")
        success, result = service.process_hcl(test_hcl_path)

        if success:
            logger.info("✓ drawj2d processing successful!")
            logger.info(f"Output file: {result['output_path']}")
            logger.info(f"Duration: {result['duration']:.2f} seconds")

            if result["stdout"]:
                logger.info(f"STDOUT: {result['stdout']}")
            if result["stderr"]:
                logger.warning(f"STDERR: {result['stderr']}")

            # Check if output file exists
            if os.path.exists(result["output_path"]):
                file_size = os.path.getsize(result["output_path"])
                logger.info(f"Output file size: {file_size} bytes")
                return True
            logger.error("Output file not found!")
            return False
        else:
            logger.error(f"✗ drawj2d processing failed: {result.get('error')}")
            if result.get("stdout"):
                logger.error(f"STDOUT: {result['stdout']}")
            if result.get("stderr"):
                logger.error(f"STDERR: {result['stderr']}")
            return False

    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_code_rendering():
    """Test rendering some simple code."""
    try:
        service = get_drawj2d_service()

        # Simple Python code example
        code = """def hello_world():
    print("Hello, reMarkable!")
    return 42

if __name__ == "__main__":
    result = hello_world()
    print(f"The answer is: {result}")"""

        logger.info("Testing code rendering...")
        success, result = service.render_syntax_highlighted_code(
            code=code, language="python"
        )

        if success:
            logger.info("✓ Code rendering successful!")
            logger.info(f"Output file: {result['output_path']}")
            return True
        logger.error(f"✗ Code rendering failed: {result.get('error')}")
        return False

    except Exception as e:
        logger.error(f"Code rendering test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Testing drawj2d Integration - Phase 1")
    print("=" * 50)

    # Test basic functionality
    print("\nTest 1: Basic HCL processing")
    if test_basic_drawj2d():
        print("✓ Basic test passed!")
    else:
        print("✗ Basic test failed!")
        sys.exit(1)

    # Test code rendering
    print("\nTest 2: Code rendering")
    if test_code_rendering():
        print("✓ Code rendering test passed!")
    else:
        print("✗ Code rendering test failed!")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("All tests passed! drawj2d is working correctly.")
    print("=" * 50)
