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


class IContentConverter(ABC):
    @abstractmethod
    def can_convert(self, content_type: str) -> bool:
        """Check if this converter can handle the given content type"""
        pass
    
    @abstractmethod
    def convert(self, content: Dict[str, Any], output_path: str) -> Optional[str]:
        """Convert content to the target format and return the output path"""
        pass


class IDocumentRenderer(ABC):
    @abstractmethod
    def render(self, content: Dict[str, Any], output_path: str) -> Optional[str]:
        """Render content to the output path and return the path on success"""
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
    
    @abstractmethod
    def create_rmdoc_from_content(self, url: str, qr_path: str, content: Dict[str, Any]) -> Optional[str]:
        """Create reMarkable document from structured content"""
        pass
    
    @abstractmethod
    def create_rmdoc_from_html(self, url: str, qr_path: str, html_content: str, title: Optional[str] = None) -> Optional[str]:
        """Create reMarkable document directly from HTML content"""
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
    def initialize_iink_sdk(self, application_key: str, hmac_key: str) -> bool:
        """Initialize the MyScript iink SDK with authentication keys"""
        pass

    @abstractmethod
    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """Extract strokes from a reMarkable file"""
        pass

    @abstractmethod
    def convert_to_iink_format(self, strokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert reMarkable strokes to iink SDK compatible format"""
        pass

    @abstractmethod
    def recognize_handwriting(
        self,
        iink_data: Dict[str, Any],
        content_type: str = "Text",
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """Process ink data through the iink SDK and return recognition results"""
        pass

    @abstractmethod
    def export_content(
        self, content_id: str, format_type: str = "text"
    ) -> Dict[str, Any]:
        """Export recognized content in the specified format (text, JIIX, etc.)"""
        pass


class IGoogleDocsService(ABC):
    @abstractmethod
    def fetch(self, url_or_id: str) -> Dict:
        """Fetch Google Docs document by URL or ID and return structured data"""
        pass