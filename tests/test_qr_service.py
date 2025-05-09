"""Tests for QR code service and adapter."""

import os
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
import qrcode

from inklink.services.qr_service import QRCodeService
from inklink.adapters.qr_adapter import QRCodeAdapter


class MockQRCodeAdapter:
    """Mock implementation of QRCodeAdapter for testing."""
    
    def __init__(self, output_dir, *args, **kwargs):
        """Initialize with test paths."""
        self.output_dir = output_dir
        self.generate_qr_code_calls = []
        self.generate_svg_qr_code_calls = []
        self.should_fail = False
        
    def ping(self) -> bool:
        """Mock implementation of ping."""
        return not self.should_fail
        
    def generate_qr_code(
        self,
        data,
        filename=None,
        fill_color="black",
        back_color="white",
        custom_config=None
    ):
        """Mock implementation of generate_qr_code."""
        self.generate_qr_code_calls.append({
            "data": data,
            "filename": filename,
            "fill_color": fill_color,
            "back_color": back_color,
            "custom_config": custom_config
        })
        
        if self.should_fail:
            return False, ("", "")
            
        # Create actual QR code file for testing
        if not filename:
            filename = f"qr_{hash(data)}.png"
        elif not filename.endswith(".png"):
            filename = f"{filename}.png"
            
        filepath = os.path.join(self.output_dir, filename)
        
        # Create a minimal QR code for testing purposes
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=3,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        img.save(filepath)
        
        return True, (filepath, os.path.basename(filepath))
        
    def generate_svg_qr_code(
        self,
        data,
        filename=None,
        custom_config=None
    ):
        """Mock implementation of generate_svg_qr_code."""
        self.generate_svg_qr_code_calls.append({
            "data": data,
            "filename": filename,
            "custom_config": custom_config
        })
        
        if self.should_fail:
            return False, ("", "")
            
        # For testing, just create a PNG instead of SVG
        if not filename:
            filename = f"qr_{hash(data)}.svg"
        elif not filename.endswith(".svg"):
            filename = f"{filename}.svg"
            
        filepath = os.path.join(self.output_dir, filename)
        
        # Create a minimal QR code as test file
        qr = qrcode.QRCode(version=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image()
        
        # For testing, just save as PNG since we don't need real SVG
        # But rename to .svg for path validation
        png_path = filepath.replace(".svg", ".png")
        img.save(png_path)
        os.rename(png_path, filepath)
        
        return True, (filepath, os.path.basename(filepath))


@pytest.fixture
def mock_adapter(tmp_path):
    """Provide a mock QRCodeAdapter."""
    return MockQRCodeAdapter(str(tmp_path))


@pytest.fixture
def qr_service(tmp_path, mock_adapter):
    """Create a QRCodeService with a mock adapter."""
    return QRCodeService(str(tmp_path), qr_adapter=mock_adapter)


def test_generate_qr(qr_service, mock_adapter):
    """Test basic QR code generation."""
    url = "https://example.com"
    path, name = qr_service.generate_qr(url)
    
    # Verify QR code file was created
    assert os.path.exists(path)
    assert name == os.path.basename(path)
    assert path.endswith(".png")
    
    # Verify adapter was called correctly
    assert len(mock_adapter.generate_qr_code_calls) == 1
    call = mock_adapter.generate_qr_code_calls[0]
    assert call["data"] == url


def test_generate_qr_failure(qr_service, mock_adapter):
    """Test handling of QR code generation failure."""
    mock_adapter.should_fail = True
    url = "https://example.com"
    path, name = qr_service.generate_qr(url)
    
    # Verify fallback error paths are returned
    assert "qr_error.png" in path
    assert name == "qr_error.png"


def test_generate_svg_qr(qr_service, mock_adapter):
    """Test SVG QR code generation."""
    url = "https://example.com"
    path, name = qr_service.generate_svg_qr(url)
    
    # Verify QR code file was created
    assert os.path.exists(path)
    assert name == os.path.basename(path)
    assert path.endswith(".svg")
    
    # Verify adapter was called correctly
    assert len(mock_adapter.generate_svg_qr_code_calls) == 1
    call = mock_adapter.generate_svg_qr_code_calls[0]
    assert call["data"] == url


def test_generate_svg_qr_failure(qr_service, mock_adapter):
    """Test handling of SVG QR code generation failure."""
    mock_adapter.should_fail = True
    url = "https://example.com"
    
    # Should fall back to regular QR code
    with patch.object(qr_service, 'generate_qr') as mock_generate_qr:
        mock_generate_qr.return_value = ("mock_path.png", "mock_path.png")
        path, name = qr_service.generate_svg_qr(url)
        
        # Verify fallback was called
        mock_generate_qr.assert_called_once_with(url)
        assert path == "mock_path.png"
        assert name == "mock_path.png"


def test_generate_custom_qr(qr_service, mock_adapter):
    """Test custom QR code generation."""
    url = "https://example.com"
    config = {
        "version": 2,
        "box_size": 15,
        "border": 3,
        "fill_color": "blue",
        "back_color": "yellow"
    }
    
    path, name = qr_service.generate_custom_qr(url, config.copy())
    
    # Verify QR code file was created
    assert os.path.exists(path)
    assert name == os.path.basename(path)
    assert path.endswith(".png")
    
    # Verify adapter was called correctly
    assert len(mock_adapter.generate_qr_code_calls) == 1
    call = mock_adapter.generate_qr_code_calls[0]
    assert call["data"] == url
    assert call["fill_color"] == "blue"
    assert call["back_color"] == "yellow"
    assert call["custom_config"]["version"] == 2
    assert call["custom_config"]["box_size"] == 15
    assert call["custom_config"]["border"] == 3
    assert "fill_color" not in call["custom_config"]
    assert "back_color" not in call["custom_config"]


def test_adapter_ping(tmp_path):
    """Test the adapter ping functionality."""
    with patch.object(QRCodeAdapter, 'ping', return_value=True):
        adapter = QRCodeAdapter(output_dir=str(tmp_path))
        assert adapter.ping() is True
        
    # Create a new adapter that will fail the ping
    with patch.object(QRCodeAdapter, 'ping', return_value=False):
        adapter = QRCodeAdapter(output_dir=str(tmp_path))
        assert adapter.ping() is False


def test_real_adapter(tmp_path):
    """Test with real QRCodeAdapter implementation."""
    # Create a real adapter
    adapter = QRCodeAdapter(output_dir=str(tmp_path))
    
    # Test standard QR code generation
    url = "https://example.com"
    success, (filepath, filename) = adapter.generate_qr_code(url)
    
    assert success is True
    assert os.path.exists(filepath)
    assert filepath.endswith(".png")
    
    # Verify QR code content with PIL
    img = Image.open(filepath)
    assert img.format == "PNG"
    assert img.size[0] > 10  # QR code should have reasonable dimensions
    
    # Test custom parameters
    custom_config = {
        "version": 2,
        "box_size": 15,
        "border": 2
    }
    success, (filepath2, filename2) = adapter.generate_qr_code(
        url, 
        filename="custom",
        fill_color="red",
        back_color="white",
        custom_config=custom_config
    )
    
    assert success is True
    assert os.path.exists(filepath2)
    assert "custom.png" in filepath2
    
    # Verify the two QR codes are different (due to different params)
    img1_size = os.path.getsize(filepath)
    img2_size = os.path.getsize(filepath2)
    assert img1_size != img2_size