import logging
import traceback

from src.inklink.services.qr_service import QRCodeService
from src.inklink.services.pdf_service import PDFService
from src.inklink.services.web_scraper_service import WebScraperService
from src.inklink.services.document_service import DocumentService
from src.inklink.services.remarkable_service import RemarkableService
from src.inklink.config import CONFIG

logger = logging.getLogger(__name__)

class ServiceManager:
    """Handles instantiation of all service dependencies with support for dependency injection."""

    def __init__(
        self,
        qr_service=None,
        pdf_service=None,
        web_scraper=None,
        document_service=None,
        remarkable_service=None,
    ):
        try:
            self.qr_service = qr_service or QRCodeService(CONFIG["TEMP_DIR"])
            self.pdf_service = pdf_service or PDFService(CONFIG["TEMP_DIR"], CONFIG["OUTPUT_DIR"])
            self.web_scraper = web_scraper or WebScraperService()
            self.document_service = document_service or DocumentService(
                CONFIG["TEMP_DIR"], CONFIG["DRAWJ2D_PATH"]
            )
            self.remarkable_service = remarkable_service or RemarkableService(
                CONFIG["RMAPI_PATH"], CONFIG["RM_FOLDER"]
            )
        except KeyError as e:
            logger.error(f"Configuration key error during service initialization: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        except FileNotFoundError as e:
            logger.error(f"File not found during service initialization: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"Error initializing services: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def get_services(self):
        """
        Retrieves all instantiated service objects.

        Returns:
            dict: A dictionary containing the following key-value pairs:
                - "qr_service" (QRCodeService): The QR code service instance.
                - "pdf_service" (PDFService): The PDF service instance.
                - "web_scraper" (WebScraperService): The web scraper service instance.
                - "document_service" (DocumentService): The document service instance.
                - "remarkable_service" (RemarkableService): The Remarkable service instance.
        """
        return {
            "qr_service": self.qr_service,
            "pdf_service": self.pdf_service,
            "web_scraper": self.web_scraper,
            "document_service": self.document_service,
            "remarkable_service": self.remarkable_service,
        }