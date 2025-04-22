import os
import requests
import shutil
from io import BytesIO
import pytest

from inklink.services.pdf_service import PDFService


class DummyHeadResponse:
    def __init__(self, headers):
        self._headers = headers

    @property
    def headers(self):
        return self._headers


class DummyGetResponse:
    def __init__(self, content, status_code=200, headers=None):
        self._content = content
        self.status_code = status_code
        self._headers = headers or {}

    @property
    def headers(self):
        return self._headers

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise requests.HTTPError(f"Status code: {self.status_code}")

    def iter_content(self, chunk_size=8192):
        yield self._content


@pytest.fixture
def pdf_service(tmp_path):
    temp_dir = tmp_path / "temp"
    out_dir = tmp_path / "out"
    return PDFService(str(temp_dir), str(out_dir))


def test_is_pdf_url_extension(pdf_service):
    assert pdf_service.is_pdf_url("http://example.com/file.pdf")
    assert pdf_service.is_pdf_url("http://example.com/file.PDF")
    assert not pdf_service.is_pdf_url("http://example.com/file.txt")


def test_is_pdf_url_header(monkeypatch, pdf_service):
    def fake_head(url, allow_redirects, timeout):
        return DummyHeadResponse({"Content-Type": "application/pdf"})

    monkeypatch.setattr(requests, "head", fake_head)
    assert pdf_service.is_pdf_url("http://example.com/nomatch")


def test_process_pdf(monkeypatch, tmp_path, pdf_service):

def test_process_pdf_raster_mode(monkeypatch, tmp_path, pdf_service):
    """Test raster mode generates PNG images for each PDF page."""
    from inklink.config import CONFIG
    import pdf2image
    from PIL import Image

    # Enable raster mode
    monkeypatch.setitem(CONFIG, "PDF_RENDER_MODE", "raster")

    # Prepare dummy PDF content
    pdf_bytes = b"%PDF-1.4 dummy pdf"
    pdf_bytes = b"%PDF-1.4 dummy content"

    def fake_get(url, stream, timeout):
        return DummyGetResponse(pdf_bytes)

    monkeypatch.setattr(requests, "get", fake_get)

    # Mock convert_from_path to return two dummy images
    def fake_convert(path):
        return [Image.new("RGB", (100, 200)), Image.new("RGB", (200, 100))]
    monkeypatch.setattr(pdf2image, "convert_from_path", fake_convert)

    result = pdf_service.process_pdf("http://example.com/test.pdf", qr_path="")
    assert "images" in result
    images = result["images"]
    assert isinstance(images, list) and len(images) == 2
    for img_path in images:
        assert os.path.exists(img_path)
        assert img_path.lower().endswith(".png")
    assert result is not None
    pdf_path = result.get("pdf_path")
    assert pdf_path and os.path.exists(pdf_path)
    # Title should be non-empty string
    assert isinstance(result.get("title"), str) and result.get("title")
    # Clean up
    shutil.rmtree(os.path.dirname(pdf_path))
