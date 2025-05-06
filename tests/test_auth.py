import subprocess
from fastapi.testclient import TestClient
import pytest

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
    # Fake subprocess.run to simulate rmapi pairing
    def fake_run(cmd, capture_output, text):
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)
    # Use the 'code' form field for pairing code
    response = client.post("/auth", data={"code": "ABC123"})
    # Successful pairing returns 200, failure returns 400
    assert response.status_code in (200, 400)
    assert expected in response.text
