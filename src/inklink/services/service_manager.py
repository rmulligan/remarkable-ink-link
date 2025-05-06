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
    """Handles instantiation of all service dependencies."""

    def __init__(self):
        try:
            self.qr_service = QRCodeService(CONFIG["TEMP_DIR"])
            self.pdf_service = PDFService(CONFIG["TEMP_DIR"], CONFIG["OUTPUT_DIR"])
            self.web_scraper = WebScraperService()
            self.document_service = DocumentService(
                CONFIG["TEMP_DIR"], CONFIG["DRAWJ2D_PATH"]
            )
            self.remarkable_service = RemarkableService(
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
        except RuntimeError as e:
            logger.error(f"Runtime error during service initialization: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def get_services(self):
        return {
            "qr_service": self.qr_service,
            "pdf_service": self.pdf_service,
            "web_scraper": self.web_scraper,
            "document_service": self.document_service,
            "remarkable_service": self.remarkable_service,
        }