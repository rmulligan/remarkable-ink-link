from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any


class IQRCodeService(ABC):
    @abstractmethod
    def generate_qr(self, url: str) -> Tuple[str, str]:
        """Generate QR code for URL and return (filepath, filename)"""
        pass


class IWebScraperService(ABC):
    @abstractmethod
    def scrape(self, url: str) -> Dict:
        """Scrape webpage content and return structured data"""
        pass


class IDocumentService(ABC):
    @abstractmethod
    def create_hcl(self, url: str, qr_path: str, content: Dict) -> Optional[str]:
        """Create HCL script from content"""
        pass

    @abstractmethod
    def create_rmdoc(self, hcl_path: str, url: str) -> Optional[str]:
        """Convert HCL to Remarkable document"""
        pass


class IPDFService(ABC):
    @abstractmethod
    def is_pdf_url(self, url: str) -> bool:
        """Check if URL points to PDF"""
        pass

    @abstractmethod
    def process_pdf(self, url: str, qr_path: str) -> Optional[Dict]:
        """Process PDF URL and return document info"""
        pass


class IRemarkableService(ABC):
    @abstractmethod
    def upload(self, doc_path: str, title: str) -> Tuple[bool, str]:
        """Upload document to Remarkable Cloud"""
        pass

class IHandwritingRecognitionService(ABC):
    @abstractmethod
    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """Extract strokes from a reMarkable file"""
        pass
    
    @abstractmethod
    def recognize_handwriting(self, strokes: List[Dict[str, Any]], language: str = "en_US") -> Dict[str, Any]:
        """Send strokes to handwriting recognition service and return results"""
        pass
    
    @abstractmethod
    def extract_and_recognize(self, rm_file_path: str, language: str = "en_US") -> Dict[str, Any]:
        """Extract strokes and perform handwriting recognition in one step"""
        pass

class IGoogleDocsService(ABC):
    @abstractmethod
    def fetch(self, url_or_id: str) -> Dict:
        """Fetch Google Docs document by URL or ID and return structured data"""
        pass
