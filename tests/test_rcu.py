"""Tests for RCU (reMarkable Content Uploader) integration."""

import os
import pytest
import subprocess
from unittest.mock import patch, MagicMock

# Import the modules directly from the package to ensure proper testing
import inklink.utils.rcu as rcu


@pytest.fixture
def temp_markdown_file(tmp_path):
    """Create a temporary markdown file for testing."""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test Document\n\nThis is a test.")
    return str(md_file)


@pytest.fixture
def temp_html_file(tmp_path):
    """Create a temporary HTML file for testing."""
    html_file = tmp_path / "test.html"
    html_file.write_text(
        "<html><body><h1>Test</h1><p>This is a test.</p></body></html>"
    )
    return str(html_file)


def test_check_rcu_installed_success(monkeypatch):
    """Test RCU installation check when RCU is available."""
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(subprocess, "run", mock_run)

    assert rcu.check_rcu_installed() is True
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0][0] == "rcu"
    assert "--version" in mock_run.call_args[0][0]


def test_check_rcu_installed_failure(monkeypatch):
    """Test RCU installation check when RCU is not available."""
    # Case 1: Command exists but returns error
    mock_run = MagicMock()
    mock_run.return_value.returncode = 1
    monkeypatch.setattr(subprocess, "run", mock_run)

    assert rcu.check_rcu_installed() is False

    # Case 2: Command doesn't exist
    def raise_error(*args, **kwargs):
        raise FileNotFoundError("No such file or directory")

    monkeypatch.setattr(subprocess, "run", raise_error)
    assert rcu.check_rcu_installed() is False


def test_install_rcu_linux_success(monkeypatch):
    """Test successful RCU installation on Linux."""
    # Mock platform.system to return 'Linux'
    monkeypatch.setattr(rcu.platform, "system", lambda: "Linux")

    # Mock subprocess.run for successful pip install
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(subprocess, "run", mock_run)

    assert rcu.install_rcu() is True
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0][0] == "pip"
    assert "install" in mock_run.call_args[0][0]
    assert "rcu" in mock_run.call_args[0][0]


def test_install_rcu_linux_fallback(monkeypatch):
    """Test RCU installation on Linux with pip failure and GitHub fallback."""
    # Mock platform.system to return 'Linux'
    monkeypatch.setattr(rcu.platform, "system", lambda: "Linux")

    # Mock subprocess.run for pip failure, then git success
    call_count = 0

    def mock_run(*args, **kwargs):
        nonlocal call_count
        mock_result = MagicMock()

        if call_count == 0:  # First call (pip) fails
            mock_result.returncode = 1
        else:  # Second call (git clone) succeeds
            mock_result.returncode = 0

        call_count += 1
        return mock_result

    monkeypatch.setattr(subprocess, "run", mock_run)

    assert rcu.install_rcu() is True


def test_install_rcu_unsupported_os(monkeypatch):
    """Test RCU installation on unsupported OS."""
    # Mock platform.system to return 'Windows'
    monkeypatch.setattr(rcu.platform, "system", lambda: "Windows")

    # No need to mock subprocess.run as it shouldn't be called
    assert rcu.install_rcu() is False


def test_ensure_rcu_available_already_installed(monkeypatch):
    """Test ensure_rcu_available when RCU is already installed."""
    # Mock check_rcu_installed to return True
    monkeypatch.setattr(rcu, "check_rcu_installed", lambda: True)

    # Mock install_rcu (shouldn't be called)
    mock_install = MagicMock()
    monkeypatch.setattr(rcu, "install_rcu", mock_install)

    assert rcu.ensure_rcu_available() is True
    mock_install.assert_not_called()


def test_ensure_rcu_available_needs_install(monkeypatch):
    """Test ensure_rcu_available when RCU needs to be installed."""
    # Mock check_rcu_installed to return False first, then True after install
    check_calls = 0

    def mock_check():
        nonlocal check_calls
        result = check_calls > 0  # False first time, True afterwards
        check_calls += 1
        return result

    monkeypatch.setattr(rcu, "check_rcu_installed", mock_check)

    # Mock install_rcu to succeed
    monkeypatch.setattr(rcu, "install_rcu", lambda: True)

    assert rcu.ensure_rcu_available() is True


def test_convert_markdown_to_rm_success(monkeypatch, temp_markdown_file):
    """Test successful markdown to rm conversion."""
    # Mock ensure_rcu_available to return True
    monkeypatch.setattr(rcu, "ensure_rcu_available", lambda: True)

    # Mock subprocess.run for successful conversion
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(subprocess, "run", mock_run)

    # Mock os.path.exists to make output file check pass
    original_exists = os.path.exists

    def mock_exists(path):
        if path.endswith(".rm"):
            return True
        return original_exists(path)

    monkeypatch.setattr(os.path, "exists", mock_exists)

    success, result = rcu.convert_markdown_to_rm(temp_markdown_file)

    assert success is True
    assert result.endswith(".rm")
    mock_run.assert_called_once()
    # Check correct command was called
    args = mock_run.call_args[0][0]
    assert args[0] == "rcu"
    assert "convert" in args
    assert "--input" in args
    assert temp_markdown_file in args


def test_convert_markdown_to_rm_failure(monkeypatch, temp_markdown_file):
    """Test failed markdown to rm conversion."""
    # Mock ensure_rcu_available to return True
    monkeypatch.setattr(rcu, "ensure_rcu_available", lambda: True)

    # Mock subprocess.run for failed conversion
    mock_run = MagicMock()
    mock_run.return_value.returncode = 1
    mock_run.return_value.stderr = "Conversion error"
    monkeypatch.setattr(subprocess, "run", mock_run)

    success, result = rcu.convert_markdown_to_rm(temp_markdown_file)

    assert success is False
    assert "Conversion error" in result


def test_convert_html_to_rm_success(monkeypatch, temp_html_file):
    """Test successful HTML to rm conversion."""
    # Mock ensure_rcu_available to return True
    monkeypatch.setattr(rcu, "ensure_rcu_available", lambda: True)

    # Mock subprocess.run for successful conversion
    mock_run = MagicMock()
    mock_run.return_value.returncode = 0
    monkeypatch.setattr(subprocess, "run", mock_run)

    # Mock os.path.exists to make output file check pass
    original_exists = os.path.exists

    def mock_exists(path):
        if path.endswith(".rm"):
            return True
        return original_exists(path)

    monkeypatch.setattr(os.path, "exists", mock_exists)

    success, result = rcu.convert_html_to_rm(temp_html_file)

    assert success is True
    assert result.endswith(".rm")
    mock_run.assert_called_once()
    # Check correct command was called
    args = mock_run.call_args[0][0]
    assert args[0] == "rcu"
    assert "convert" in args
    assert "--html" in args
    assert "--input" in args
    assert temp_html_file in args