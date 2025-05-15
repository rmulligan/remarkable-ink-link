from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

<< << << < HEAD
== == == =
>>>>>> > c5c0feb(style: format code with Autopep8, Black and isort)


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
        """Initialize the MyScript Web API with authentication keys

        Note: Despite the method name, this initializes the REST API, not an SDK.
        The method name is kept for backward compatibility.
        """
        pass

    @abstractmethod
    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """Extract strokes from a reMarkable file"""
        pass

    @abstractmethod
    def convert_to_iink_format(self, strokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert reMarkable strokes to MyScript Web API compatible format

        Note: Despite the method name, this formats data for the REST API, not an SDK.
        The method name is kept for backward compatibility.
        """
        pass

    @abstractmethod
    def recognize_handwriting(
        self,
        iink_data: Dict[str, Any],
        content_type: str = "Text",
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """Process ink data through the MyScript Web API and return recognition results

        Uses the REST API endpoint for handwriting recognition.
        """
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


class IEPUBGenerator(ABC):
    @abstractmethod
    def create_epub_from_markdown(
        self,
        title: str,
        content: str,
        author: str = "InkLink",
        entity_links: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create an EPUB document from markdown content.

        Args:
            title: Title of the EPUB document
            content: Markdown content
            author: Author of the document
            entity_links: Dictionary mapping entity names to their anchor IDs
            metadata: Additional metadata for the EPUB

        Returns:
            Tuple of (success, result_dict)
        """
        pass

    @abstractmethod
    def enhance_markdown_with_hyperlinks(
        self, markdown_content: str, entity_links: Dict[str, str]
    ) -> str:
        """
        Enhance markdown content with hyperlinks.

        Args:
            markdown_content: Original markdown content
            entity_links: Dictionary mapping entity names to their anchor IDs

        Returns:
            Enhanced markdown content with hyperlinks
        """
        pass


class IKnowledgeGraphService(ABC):
    @abstractmethod
    def get_entities(
        self, types: Optional[List[str]] = None, min_references: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get entities from the knowledge graph, optionally filtered by type.

        Args:
            types: Optional list of entity types to filter by
            min_references: Minimum number of references for an entity to be included

        Returns:
            List of entity dictionaries
        """
        pass

    @abstractmethod
    def get_topics(
        self, limit: int = 20, min_connections: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get topics from the knowledge graph.

        Topics are derived from entity clusters and semantic connections.

        Args:
            limit: Maximum number of topics to return
            min_connections: Minimum number of connections for a topic to be included

        Returns:
            List of topic dictionaries
        """
        pass

    @abstractmethod
    def get_notebooks(self) -> List[Dict[str, Any]]:
        """
        Get notebooks from the knowledge graph.

        Returns:
            List of notebook dictionaries with their entities and topics
        """
        pass


class IKnowledgeIndexService(ABC):
    @abstractmethod
    def create_entity_index(
        self,
        entity_types: Optional[List[str]] = None,
        min_references: int = 1,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create an entity index notebook grouping entities by type.

        Args:
            entity_types: Optional list of entity types to include (None for all)
            min_references: Minimum number of references for an entity to be included
            upload_to_remarkable: Whether to upload index to reMarkable Cloud

        Returns:
            Tuple of (success, result_dict)
        """
        pass

    @abstractmethod
    def create_topic_index(
        self,
        top_n_topics: int = 20,
        min_connections: int = 2,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a topic index notebook organizing content by topic.

        Args:
            top_n_topics: Number of top topics to include
            min_connections: Minimum connections for a topic to be included
            upload_to_remarkable: Whether to upload index to reMarkable Cloud

        Returns:
            Tuple of (success, result_dict)
        """
        pass

    @abstractmethod
    def create_notebook_index(
        self,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a notebook index organizing content by source notebook.

        Args:
            upload_to_remarkable: Whether to upload index to reMarkable Cloud

        Returns:
            Tuple of (success, result_dict)
        """
        pass

    @abstractmethod
    def create_master_index(
        self,
        upload_to_remarkable: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a master index combining entity, topic, and notebook indices.

        Args:
            upload_to_remarkable: Whether to upload index to reMarkable Cloud

        Returns:
            Tuple of (success, result_dict)
        """
        pass


class ILimitlessLifeLogService(ABC):
    @abstractmethod
    def sync_life_logs(self, force_full_sync: bool = False) -> Tuple[bool, str]:
        """
        Sync life logs from Limitless API to knowledge graph.

        Args:
            force_full_sync: If True, sync all life logs regardless of last sync time

        Returns:
            Tuple of (success, message)
        """
        pass

    @abstractmethod
    def get_life_log(self, log_id: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        Retrieve a specific life log by ID.

        Args:
            log_id: ID of the life log to retrieve

        Returns:
            Tuple of (success, life_log_or_error)
        """
        pass

    @abstractmethod
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get the current sync status.

        Returns:
            Dictionary with sync status information
        """
        pass

    @abstractmethod
    def clear_cache(self) -> Tuple[bool, str]:
        """
        Clear the local cache of life logs.

        Returns:
            Tuple of (success, message)
        """
        pass
