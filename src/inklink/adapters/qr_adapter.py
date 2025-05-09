"""QR Code adapter for InkLink.

This module provides an adapter for QR code generation using qrcode library.
"""

import os
import logging
import qrcode
from typing import Optional, Tuple, Dict, Any

from inklink.adapters.adapter import Adapter

logger = logging.getLogger(__name__)


class QRCodeAdapter(Adapter):
    """Adapter for QR code generation."""

    def __init__(
        self,
        output_dir: str,
        version: int = 1,
        error_correction: int = qrcode.constants.ERROR_CORRECT_L,
        box_size: int = 10,
        border: int = 4,
    ):
        """
        Initialize the QR code adapter.

        Args:
            output_dir: Directory to save generated QR codes
            version: QR code version (1-40, controls complexity)
            error_correction: Error correction level
            box_size: Size of each box in pixels
            border: Border size in boxes
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # QR code configuration
        self.version = version
        self.error_correction = error_correction
        self.box_size = box_size
        self.border = border

    def ping(self) -> bool:
        """
        Check if the adapter can generate QR codes.

        Returns:
            True if the output directory is writable, False otherwise
        """
        try:
            # Check if output directory exists and is writable
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir, exist_ok=True)

            test_file = os.path.join(self.output_dir, ".qr_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True

        except Exception as e:
            logger.error(f"QR code adapter ping failed: {e}")
            return False

    def generate_qr_code(
        self,
        data: str,
        filename: Optional[str] = None,
        fill_color: str = "black",
        back_color: str = "white",
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Tuple[str, str]]:
        """
        Generate a QR code image.

        Args:
            data: The data to encode in the QR code
            filename: Optional custom filename (without extension)
            fill_color: Color of the QR code
            back_color: Background color
            custom_config: Optional custom configuration to override defaults

        Returns:
            Tuple of (success, (filepath, filename))
        """
        try:
            # Use custom config if provided, otherwise use defaults
            config = custom_config or {
                "version": self.version,
                "error_correction": self.error_correction,
                "box_size": self.box_size,
                "border": self.border,
            }

            # Create QR code object
            qr = qrcode.QRCode(
                version=config.get("version", self.version),
                error_correction=config.get("error_correction", self.error_correction),
                box_size=config.get("box_size", self.box_size),
                border=config.get("border", self.border),
            )

            # Add data and generate QR code
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color=fill_color, back_color=back_color)

            # Generate filename if not provided
            if not filename:
                filename = f"qr_{hash(data)}"

            # Ensure filename has .png extension
            if not filename.endswith(".png"):
                filename = f"{filename}.png"

            # Save the QR code image
            filepath = os.path.join(self.output_dir, filename)
            img.save(filepath)

            return True, (filepath, os.path.basename(filepath))

        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            return False, ("", "")

    def generate_svg_qr_code(
        self,
        data: str,
        filename: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Tuple[str, str]]:
        """
        Generate a QR code in SVG format.

        Args:
            data: The data to encode in the QR code
            filename: Optional custom filename (without extension)
            custom_config: Optional custom configuration to override defaults

        Returns:
            Tuple of (success, (filepath, filename))
        """
        try:
            # Check if SVG factory is available
            try:
                import qrcode.image.svg

                factory = qrcode.image.svg.SvgImage
            except ImportError:
                logger.error("SVG support not available, falling back to PNG")
                return self.generate_qr_code(
                    data, filename, custom_config=custom_config
                )

            # Use custom config if provided, otherwise use defaults
            config = custom_config or {
                "version": self.version,
                "error_correction": self.error_correction,
                "box_size": self.box_size,
                "border": self.border,
            }

            # Create QR code object
            qr = qrcode.QRCode(
                version=config.get("version", self.version),
                error_correction=config.get("error_correction", self.error_correction),
                box_size=config.get("box_size", self.box_size),
                border=config.get("border", self.border),
                image_factory=factory,
            )

            # Add data and generate QR code
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image()

            # Generate filename if not provided
            if not filename:
                filename = f"qr_{hash(data)}"

            # Ensure filename has .svg extension
            if not filename.endswith(".svg"):
                filename = f"{filename}.svg"

            # Save the QR code image
            filepath = os.path.join(self.output_dir, filename)
            img.save(filepath)

            return True, (filepath, os.path.basename(filepath))

        except Exception as e:
            logger.error(f"Failed to generate SVG QR code: {e}")
            return False, ("", "")
