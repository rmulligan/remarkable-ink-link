import os
import subprocess
from inklink.services.remarkable_service import RemarkableService


class DummyResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_upload_missing_doc(monkeypatch, tmp_path):
    # Setup service with fake rmapi path
    rmapi = str(tmp_path / "rmapi")
    service = RemarkableService(rmapi, upload_folder="/")
    # doc_path does not exist
    success, message = service.upload(str(tmp_path / "noexist.rm"), "Title")
    assert not success
    assert "Document not found" in message


def test_upload_missing_rmapi(monkeypatch, tmp_path):
    # Create dummy doc file
    doc_path = tmp_path / "file.rm"
    doc_path.write_text("data")
    service = RemarkableService(str(tmp_path / "noapi"), upload_folder="/")
    success, message = service.upload(str(doc_path), "Title")
    assert not success
    assert "rmapi executable not found" in message


def test_upload_success_and_rename(monkeypatch, tmp_path):
    # Create dummy rmapi and doc file
    rmapi = tmp_path / "rmapi"
    rmapi.write_text("")
    os.chmod(str(rmapi), 0o755)
    doc_path = tmp_path / "file.rm"
    doc_path.write_text("data")
    service = RemarkableService(str(rmapi), upload_folder="/")

    # Mock subprocess.run to simulate success and ID in stdout
    def fake_run(cmd, capture_output, text, check):
        if cmd[1] == "put":
            return DummyResult(returncode=0, stdout="Uploaded. ID: abc123\n")
        if cmd[1] == "mv":
            return DummyResult(returncode=0)
        return DummyResult(returncode=1, stderr="error")

    monkeypatch.setattr(subprocess, "run", fake_run)
    success, message = service.upload(str(doc_path), "MyTitle")
    assert success
    assert "uploaded to remarkable" in message.lower()
