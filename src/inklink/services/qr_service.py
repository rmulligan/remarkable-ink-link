"""QR code generation service for InkLink."""

import os
import logging
from typing import Tuple, Optional, Dict, Any

from inklink.services.interfaces import IQRCodeService
from inklink.adapters.qr_adapter import QRCodeAdapter

logger = logging.getLogger(__name__)


class QRCodeService(IQRCodeService):
    """Generates QR codes for URLs."""

    def __init__(
        self, 
        temp_dir: str,
        qr_adapter: Optional[QRCodeAdapter] = None
    ):
        """
        Initialize with output path for QR codes.

        Args:
            temp_dir: Directory to save QR codes
            qr_adapter: Optional pre-configured QRCodeAdapter
        """
        self.output_path = temp_dir
        
        # Use provided adapter or create a new one
        self.adapter = qr_adapter or QRCodeAdapter(
            output_dir=temp_dir,
            version=1,
            box_size=10,
            border=4
        )

    def generate_qr(self, url: str) -> Tuple[str, str]:
        """
        Generate QR code for URL and return filepath and filename.

        Args:
            url: The URL to encode in the QR code

        Returns:
            Tuple of (filepath, filename)
        """
        success, (filepath, filename) = self.adapter.generate_qr_code(url)
        
        if not success:
            logger.error(f"Failed to generate QR code for URL: {url}")
            # Create an empty filename to avoid null references
            return os.path.join(self.output_path, "qr_error.png"), "qr_error.png"
            
        return filepath, filename
        
    def generate_svg_qr(self, url: str) -> Tuple[str, str]:
        """
        Generate SVG QR code for URL and return filepath and filename.
        
        Args:
            url: The URL to encode in the QR code
            
        Returns:
            Tuple of (filepath, filename)
        """
        success, (filepath, filename) = self.adapter.generate_svg_qr_code(url)
        
        if not success:
            logger.error(f"Failed to generate SVG QR code for URL: {url}")
            # Fall back to regular QR code
            return self.generate_qr(url)
            
        return filepath, filename
        
    def generate_custom_qr(
        self, 
        url: str, 
        config: Dict[str, Any],
        svg: bool = False
    ) -> Tuple[str, str]:
        """
        Generate a custom QR code with specific configuration.
        
        Args:
            url: The URL to encode in the QR code
            config: Configuration parameters (version, box_size, etc.)
            svg: Whether to generate an SVG QR code
            
        Returns:
            Tuple of (filepath, filename)
        """
        if svg:
            success, (filepath, filename) = self.adapter.generate_svg_qr_code(
                data=url,
                custom_config=config
            )
        else:
            fill_color = config.pop("fill_color", "black")
            back_color = config.pop("back_color", "white")
            
            success, (filepath, filename) = self.adapter.generate_qr_code(
                data=url,
                fill_color=fill_color,
                back_color=back_color,
                custom_config=config
            )
            
        if not success:
            logger.error(f"Failed to generate custom QR code for URL: {url}")
            return self.generate_qr(url)
            
        return filepath, filename