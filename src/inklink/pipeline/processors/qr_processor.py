"""QR code generation processor for InkLink.

This module provides a processor for generating QR codes.
"""

import logging
from typing import Any, Dict, Optional

from inklink.pipeline.processor import PipelineContext, Processor
from inklink.services.interfaces import IQRCodeService

logger = logging.getLogger(__name__)


class QRProcessor(Processor):
    """Generates QR codes for URLs."""

    def __init__(self, qr_service: IQRCodeService):
        """
        Initialize with QR code service.

        Args:
            qr_service: QR code service for generating QR codes
        """
        self.qr_service = qr_service

    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the context by generating a QR code.

        Args:
            context: Pipeline context with url

        Returns:
            Updated pipeline context with QR code path
        """
        url = context.url

        # Skip if URL is not valid
        if not url or context.has_errors():
            return context

        try:
            # Generate QR code
            qr_path, qr_filename = self.qr_service.generate_qr(url)

            # Add QR code to context
            context.add_artifact("qr_path", qr_path)
            context.add_artifact("qr_filename", qr_filename)
            logger.info(f"QR code generated: {qr_filename}")

        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            context.add_error(
                f"Failed to generate QR code: {str(e)}", processor=str(self)
            )

        return context
