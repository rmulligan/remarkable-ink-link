"""QR code generation service for Pi Share Receiver."""

import os
import qrcode
from typing import Tuple

class QRCodeService:
    """Generates QR codes for URLs."""
    
    def __init__(self, output_path: str):
        """Initialize with output path for QR codes.
        
        Args:
            output_path: Directory to save QR codes
        """
        self.output_path = output_path
        os.makedirs(output_path, exist_ok=True)

    def generate_qr(self, url: str) -> Tuple[str, str]:
        """Generate QR code for URL and return filepath and filename.
        
        Args:
            url: The URL to encode in the QR code
            
        Returns:
            Tuple of (filepath, filename)
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save QR Code image
        filename = f"qr_{hash(url)}.png"
        filepath = os.path.join(self.output_path, filename)
        img.save(filepath)
        
        return filepath, filename