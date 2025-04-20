import subprocess
from fastapi.testclient import TestClient
import pytest

from inklink.auth import app

client = TestClient(app)


def test_auth_form():
    response = client.get("/auth")
    assert response.status_code == 200
    assert "InkLink reMarkable Cloud Authentication" in response.text


@pytest.mark.parametrize(
    "returncode,stderr,expected",
    [
        (0, "", "Authentication successful!"),
        (1, "failed", "Authentication failed"),
    ],
)
def test_auth_submit(monkeypatch, returncode, stderr, expected):
    # Fake subprocess.run
    def fake_run(cmd, capture_output, text):
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)
    response = client.post("/auth", data={"username": "user", "password": "pass"})
    assert response.status_code in (200, 400)
    assert expected in response.text
