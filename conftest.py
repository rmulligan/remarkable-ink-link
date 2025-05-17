"""Global pytest configuration and fixtures."""

import os
import pytest


def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "live: mark test as requiring live services")
    config.addinivalue_line(
        "markers", "requires_rmapi: mark test as requiring rmapi binary"
    )
    config.addinivalue_line(
        "markers", "requires_api_keys: mark test as requiring API keys"
    )
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "skip: skip the test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip tests based on environment."""
    skip_integration = pytest.mark.skip(reason="integration tests disabled in CI")
    skip_live = pytest.mark.skip(reason="live service tests disabled in CI")
    skip_no_rmapi = pytest.mark.skip(reason="rmapi not available")
    skip_no_keys = pytest.mark.skip(reason="API keys not available")

    # Check if we're in CI
    is_ci = os.environ.get("CI", "").lower() == "true"

    # Check for rmapi
    rmapi_path = os.environ.get("RMAPI_PATH", "rmapi")
    has_rmapi = (
        os.path.exists(rmapi_path)
        or os.system(f"which {rmapi_path} > /dev/null 2>&1") == 0
    )

    # Check for API keys
    has_api_keys = all(
        [
            os.environ.get("LIMITLESS_API_KEY"),
            os.environ.get("MYSCRIPT_APP_KEY"),
            os.environ.get("MYSCRIPT_API_KEY"),
        ]
    )

    for item in items:
        # Skip integration tests in CI unless explicitly enabled
        if (
            is_ci
            and "integration" in item.keywords
            and not os.environ.get("RUN_INTEGRATION_TESTS")
        ):
            item.add_marker(skip_integration)

        # Skip live tests in CI unless explicitly enabled
        if is_ci and "live" in item.keywords and not os.environ.get("RUN_LIVE_TESTS"):
            item.add_marker(skip_live)

        # Skip tests requiring rmapi if not available
        if "requires_rmapi" in item.keywords and not has_rmapi:
            item.add_marker(skip_no_rmapi)

        # Skip tests requiring API keys if not available
        if "requires_api_keys" in item.keywords and not has_api_keys:
            item.add_marker(skip_no_keys)

        # Skip specific problematic tests in CI
        if is_ci and item.nodeid in [
            "tests/adapters/test_rmapi_list.py::test_rmapi_list",
            "tests/test_limitless_live.py",
            "tests/test_live_roundtrip.py",
        ]:
            item.add_marker(pytest.mark.skip(reason="Known to fail in CI"))


# Fixtures
@pytest.fixture
def mock_rmapi_path(tmp_path):
    """Create a mock rmapi executable for testing."""
    rmapi = tmp_path / "rmapi"
    rmapi.write_text("#!/bin/bash\necho 'mock rmapi'\n")
    os.chmod(str(rmapi), 0o755)
    return str(rmapi)


@pytest.fixture
def ci_environment():
    """Set up CI-friendly environment variables."""
    old_env = dict(os.environ)
    os.environ["CI"] = "true"
    os.environ["RMAPI_PATH"] = "rmapi"
    yield
    os.environ.clear()
    os.environ.update(old_env)
