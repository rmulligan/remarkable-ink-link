import os
from inklink.services.qr_service import QRCodeService


def test_generate_qr(tmp_path):
    service = QRCodeService(str(tmp_path))
    url = "https://example.com"
    path, name = service.generate_qr(url)
    assert os.path.exists(path)
    assert name == os.path.basename(path)
    assert path.endswith(".png")
