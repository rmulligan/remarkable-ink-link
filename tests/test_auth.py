# `import subprocess` in Python is used to import the built-in module `subprocess`, which allows you
# to spawn new processes, connect to their input/output/error pipes, and obtain their return codes.
# This module provides a way to run system commands and interact with the system shell from within a
# Python script.
# `import subprocess` in Python is used to import the built-in module `subprocess`, which allows you
# to spawn new processes, connect to their input/output/error pipes, and obtain their return codes.
# This module provides a way to run system commands and interact with the system shell from within a
# Python script.
import subprocess

import pytest
from fastapi.testclient import TestClient

from inklink.auth import app

client = TestClient(app)


def test_auth_form():
    response = client.get("/auth")
    assert response.status_code == 200
    # Should show the new pairing instructions with correct heading
    assert "Pairing Code" in response.text
    assert "https://my.remarkable.com/device/remarkable?showOtp=true" in response.text


@pytest.mark.parametrize(
    "returncode,stderr,expected",
    [
        (0, "", "Authentication successful!"),
        (1, "failed", "Authentication failed"),
    ],
)
def test_auth_submit(monkeypatch, returncode, stderr, expected):
    # Mock os.path.exists and os.access for rmapi path validation
    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("os.access", lambda x, y: True)

    # Fake subprocess.run to simulate rmapi pairing
    def fake_run(cmd, capture_output, text, shell=False, timeout=None, check=False):
        # The check parameter is used in the auth code but not in the test
        if check and returncode != 0:
            raise subprocess.CalledProcessError(returncode, cmd, stderr=stderr)
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Use a code from the allowlist defined in auth.py
    # The allowlist contains: {"123456", "abcdef", "A1B2C3D4"}
    response = client.post("/auth", data={"code": "A1B2C3D4"})

    # Expected status depends on the mock returncode
    if returncode == 0:
        assert response.status_code == 200
    else:
        assert response.status_code == 400

    assert expected in response.text


def test_auth_submit_invalid_code():
    # Test invalid pairing code formats
    invalid_codes = [
        "",  # Empty
        "123",  # Too short
        "123456789",  # Too long
        "ABC-123",  # Contains hyphen
        "ABC 123",  # Contains space
        "ABC@123",  # Contains special character
    ]

    for code in invalid_codes:
        response = client.post("/auth", data={"code": code})
        assert response.status_code == 400
        assert "Invalid pairing code format" in response.text
