from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any, Union


class IQRCodeService(ABC):
    @abstractmethod
    def generate_qr(self, url: str) -> Tuple[str, str]:
        """Generate QR code for URL and return (filepath, filename)"""
        pass

    @abstractmethod
    def generate_svg_qr(self, url: str) -> Tuple[str, str]:
        """Generate SVG QR code for URL and return (filepath, filename)"""
        pass

    @abstractmethod
    def generate_custom_qr(
        self, url: str, config: Dict[str, Any], svg: bool = False
    ) -> Tuple[str, str]:
        """Generate QR code with custom configuration"""
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
    def create_rmdoc_from_content(
        self, url: str, qr_path: str, content: Dict[str, Any]
    ) -> Optional[str]:
        """Create reMarkable document from structured content"""
        pass

    @abstractmethod
    def create_rmdoc_from_html(
        self, url: str, qr_path: str, html_content: str, title: Optional[str] = None
    ) -> Optional[str]:
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

    @abstractmethod
    def add_watermark(
        self, pdf_path: str, watermark_path: str, output_path: str
    ) -> bool:
        """Add watermark (like a QR code) to each page of a PDF"""
        pass

    @abstractmethod
    def extract_text(self, pdf_path: str) -> List[str]:
        """Extract text from each page of a PDF"""
        pass

    @abstractmethod
    def convert_to_images(
        self, pdf_path: str, output_dir: Optional[str] = None
    ) -> List[str]:
        """Convert PDF to images"""
        pass

    @abstractmethod
    def generate_index_notebook(
        self,
        pages: List[Dict[str, Any]],
        output_path: str,
        graph_title: str = "Index Node Graph",
    ) -> bool:
        """Generate an index notebook as a PDF containing a node graph with cross-references"""
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

    @abstractmethod
    def fetch_as_pdf(self, url_or_id: str, output_path: str) -> bool:
        """Fetch Google Docs document as PDF and save to output_path"""
        pass

    @abstractmethod
    def fetch_as_docx(self, url_or_id: str, output_path: str) -> bool:
        """Fetch Google Docs document as DOCX and save to output_path"""
        pass

    @abstractmethod
    def list_documents(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """List Google Docs documents with metadata"""
        pass


class IAIService(ABC):
    @abstractmethod
    def ask(self, prompt: str) -> str:
        """
        Ask a prompt to the AI model and return the response text.
        Simplified interface for quick queries.
        """
        pass

    @abstractmethod
    def process_query(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None,
        structured_content: Optional[
            Union[List[Dict[str, Any]], Dict[str, Any]]
        ] = None,
        context_window: Optional[int] = None,
        selected_pages: Optional[List[Union[int, str]]] = None,
    ) -> str:
        """
        Process a text query and return an AI response.

        Parameters:
            query_text: The user's query.
            context: Additional context as a dictionary.
            structured_content: Structured document content, e.g., list of pages with links.
            context_window: Number of most recent pages to include as context.
            selected_pages: Specific pages to include as context.

        Returns:
            AI-generated response.
        """
        pass
