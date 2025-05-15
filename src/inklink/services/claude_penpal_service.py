#!/usr/bin/env python
"""Claude Penpal Service - Monitors reMarkable notebooks for handwritten queries.

This service provides a penpal-style interaction with Claude, where:
- Notebooks are organized by subject
- Queries are identified with #Lilly tags
- Context is provided with #Context tags
- Knowledge graph processing uses #kg tags
- Responses are inserted directly after query pages
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from inklink.adapters.rmapi_adapter import RmapiAdapter
from inklink.config import CONFIG
from inklink.services.document_service import DocumentService
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)

logger = logging.getLogger(__name__)


class ClaudePenpalService:
    """Service for monitoring and processing handwritten queries for Claude."""

    def __init__(
        self,
        rmapi_path: Optional[str] = None,
        claude_command: Optional[str] = None,
        model: Optional[str] = None,
        query_tag: str = "Lilly",
        context_tag: str = "Context",
        knowledge_graph_tag: str = "kg",
        new_conversation_tag: str = "new",
        subject_tag: Optional[str] = None,
        default_subject: Optional[str] = None,
        use_subject_dirs: Optional[bool] = None,
        pre_filter_tag: Optional[str] = "HasLilly",
        mcp_tool_tags: Optional[List[str]] = None,
        poll_interval: int = 60,
        syntax_highlighting: bool = True,
        remove_tags_after_processing: bool = True,
        use_conversation_ids: bool = True,
    ):
        """Initialize the service with necessary components.

        Args:
            rmapi_path: Path to rmapi executable
            claude_command: Command to invoke Claude CLI
            model: Claude model to use
            query_tag: Tag to identify query pages (default: Lilly)
            context_tag: Tag to identify additional context pages
            knowledge_graph_tag: Tag to identify pages for KG processing (default: kg)
            new_conversation_tag: Tag to identify start of new conversation (default: new)
            subject_tag: Tag that indicates the subject classification for notebooks
            default_subject: Default subject to use if none is specified
            use_subject_dirs: Whether to organize notebooks into subject directories
            pre_filter_tag: Document-level tag to pre-filter notebooks (default: HasLilly)
                           This optimizes performance by only checking notebooks with this tag
            mcp_tool_tags: List of tags that map to MCP tools to enforce
            poll_interval: How often to check for new pages (seconds)
            syntax_highlighting: Whether to enable syntax highlighting for code
            remove_tags_after_processing: Whether to remove tags after processing
            use_conversation_ids: Whether to use separate Claude conversation IDs per notebook
        """
        self.rmapi_path = rmapi_path or CONFIG.get("RMAPI_PATH")
        self.claude_command = claude_command or CONFIG.get(
            "CLAUDE_COMMAND", "/home/ryan/.claude/local/claude"
        )
        self.model = model or CONFIG.get("CLAUDE_MODEL", "")
        self.query_tag = query_tag
        self.context_tag = context_tag
        self.knowledge_graph_tag = knowledge_graph_tag
        self.new_conversation_tag = new_conversation_tag
        self.subject_tag = subject_tag or CONFIG.get("LILLY_SUBJECT_TAG", "Subject")
        self.default_subject = default_subject or CONFIG.get(
            "LILLY_DEFAULT_SUBJECT", "General"
        )
        self.use_subject_dirs = (
            use_subject_dirs
            if use_subject_dirs is not None
            else CONFIG.get("LILLY_USE_SUBJECT_DIRS", True)
        )
        self.pre_filter_tag = pre_filter_tag or CONFIG.get(
            "LILLY_PRE_FILTER_TAG", "HasLilly"
        )
        self.mcp_tool_tags = mcp_tool_tags or []
        self.poll_interval = poll_interval
        self.syntax_highlighting = syntax_highlighting
        self.remove_tags_after_processing = remove_tags_after_processing
        self.use_conversation_ids = use_conversation_ids
        self.temp_dir = CONFIG.get("TEMP_DIR")
        os.makedirs(self.temp_dir, exist_ok=True)

        # Track notebooks with active context and conversation IDs
        self.notebook_contexts: Dict[str, bool] = {}
        self.notebook_conversation_ids: Dict[str, str] = {}

        # Create base Lilly directory for notebook storage
        lilly_root = CONFIG.get("LILLY_ROOT_DIR", os.path.expanduser("~/dev"))
        self.lilly_dir = os.path.join(lilly_root, "Lilly")
        os.makedirs(self.lilly_dir, exist_ok=True)
        logger.info(f"Using Lilly directory for notebook storage: {self.lilly_dir}")

        # Create default subject directory if using subject organization
        if self.use_subject_dirs:
            default_subject_dir = os.path.join(
                self.lilly_dir, self._sanitize_name(self.default_subject)
            )
            os.makedirs(default_subject_dir, exist_ok=True)
            logger.info(f"Created default subject directory: {default_subject_dir}")

        # Store conversation IDs in the Lilly directory
        self.conversation_storage_path = os.path.join(
            self.lilly_dir, "claude_conversation_ids.json"
        )

        # Load existing conversation IDs if available
        self._load_conversation_ids()

        # Initialize components
        self.rmapi_adapter = RmapiAdapter(self.rmapi_path)
        self.handwriting_service = HandwritingRecognitionService(
            claude_command=self.claude_command, model=self.model
        )
        self.document_service = DocumentService(
            temp_dir=self.temp_dir, drawj2d_path=CONFIG.get("DRAWJ2D_PATH")
        )

        # Initialize knowledge graph service if available
        try:
            from inklink.services.knowledge_graph_service import KnowledgeGraphService

            self.kg_service = KnowledgeGraphService()
            logger.info("Knowledge graph service initialized")
        except ImportError:
            logger.warning("Knowledge graph service not available")
            self.kg_service = None

        # Set up tracking for processed queries by page ID
        self.processed_pages = set()
        self._running = False
        self._monitor_thread = None

        logger.info("Claude Penpal service initialized")

    def start_monitoring(self):
        """Start the monitoring thread."""
        if self._running:
            logger.warning("Monitoring already active")
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"Started monitoring for tagged pages")

    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
            logger.info("Stopped monitoring")

    def _monitor_loop(self):
        """Main monitoring loop for finding tagged pages within notebooks."""
        while self._running:
            try:
                # Use pre-filtering with the HasLilly tag to optimize notebook checking
                if self.pre_filter_tag:
                    logger.info(
                        f"Using pre-filter tag '{self.pre_filter_tag}' to optimize notebook selection"
                    )
                    filtered_notebooks = self.rmapi_adapter.find_tagged_notebooks(
                        tag=self.pre_filter_tag,
                        pre_filter_tag=None,  # No recursive pre-filtering
                    )

                    if not filtered_notebooks:
                        logger.warning(
                            f"No notebooks found with pre-filter tag '{self.pre_filter_tag}'"
                        )
                        time.sleep(self.poll_interval)
                        continue

                    logger.info(
                        f"Found {len(filtered_notebooks)} notebooks with pre-filter tag '{self.pre_filter_tag}'"
                    )

                    # Convert to the same format as list_files() for compatibility
                    notebooks = []
                    for nb in filtered_notebooks:
                        notebooks.append(
                            {
                                "ID": nb.get("id"),
                                "VissibleName": nb.get("name"),
                                "Type": "DocumentType",
                            }
                        )
                else:
                    # If no pre-filtering, use the standard method to list all notebooks
                    success, notebooks = self.rmapi_adapter.list_files()
                    if not success:
                        logger.error("Failed to list notebooks")
                        time.sleep(self.poll_interval)
                        continue

                # Process each notebook to check for tagged pages
                for notebook in notebooks:
                    self._check_notebook_for_tagged_pages(notebook)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                import traceback

                logger.error(traceback.format_exc())

            # Wait for next poll interval
            time.sleep(self.poll_interval)

    def _load_conversation_ids(self):
        """Load saved conversation IDs from storage."""
        try:
            if os.path.exists(self.conversation_storage_path):
                with open(self.conversation_storage_path, "r") as f:
                    self.notebook_conversation_ids = json.load(f)
                    logger.info(
                        f"Loaded {len(self.notebook_conversation_ids)} conversation IDs"
                    )
        except Exception as e:
            logger.error(f"Error loading conversation IDs: {e}")
            self.notebook_conversation_ids = {}

    def _save_conversation_ids(self):
        """Save conversation IDs to storage."""
        try:
            with open(self.conversation_storage_path, "w") as f:
                json.dump(self.notebook_conversation_ids, f)
            logger.info(f"Saved {len(self.notebook_conversation_ids)} conversation IDs")
        except Exception as e:
            logger.error(f"Error saving conversation IDs: {e}")

    def _check_notebook_for_tagged_pages(self, notebook):
        """Check a notebook for pages with tags.

        Args:
            notebook: Notebook information from rmapi
        """
        notebook_id = notebook.get("ID")
        notebook_name = notebook.get("VissibleName", "Notebook")  # Note: typo from API

        # First, see if we have metadata for this notebook to determine the subject
        metadata = self._get_notebook_metadata(notebook_id, notebook_name)

        # Create or get the notebook-specific directory based on metadata
        notebook_dir = self._get_notebook_directory(notebook_name, metadata)

        try:
            # Create paths for notebook files
            download_path = os.path.join(notebook_dir, f"{notebook_name}.rmdoc")
            extract_dir = os.path.join(notebook_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            # Download notebook
            logger.info(f"Downloading notebook {notebook_name} to {download_path}")
            success, _ = self.rmapi_adapter.download_file(
                notebook_id, download_path, "zip"
            )

            if not success:
                logger.warning(f"Failed to download notebook {notebook_id}")
                return

            # Extract and scan for tagged pages
            pages_data = self._extract_notebook_pages(download_path, extract_dir)

            if not pages_data:
                logger.debug(f"No pages found in notebook {notebook_id}")
                return

            # Find query pages
            query_pages = [p for p in pages_data if self._has_tag(p, self.query_tag)]

            # Process each query page
            for query_page in query_pages:
                page_id = query_page["id"]

                # Skip if already processed
                if page_id in self.processed_pages:
                    continue

                logger.info(
                    f"Processing query page {page_id} in notebook {notebook_name}"
                )

                # Check if this page has the 'new' tag to start a new conversation
                start_new_conversation = self._has_tag(
                    query_page, self.new_conversation_tag
                )
                if start_new_conversation:
                    logger.info(
                        f"New conversation requested for notebook {notebook_name}"
                    )
                    self.notebook_contexts[notebook_id] = False

                    # Reset conversation ID if using separate IDs
                    if (
                        self.use_conversation_ids
                        and notebook_id in self.notebook_conversation_ids
                    ):
                        logger.info(
                            f"Resetting conversation ID for notebook {notebook_id}"
                        )
                        del self.notebook_conversation_ids[notebook_id]
                        self._save_conversation_ids()

                # Find context pages (must come before the query page)
                page_idx = pages_data.index(query_page)
                context_pages = [
                    p
                    for p in pages_data[:page_idx]
                    if self._has_tag(p, self.context_tag)
                ]

                # Check for MCP tool tags
                mcp_tools = self._get_mcp_tools_from_tags(query_page)

                # Process the query with context
                self._process_query_with_context(
                    notebook_id=notebook_id,
                    notebook_name=notebook_name,
                    notebook_path=download_path,
                    notebook_dir=notebook_dir,
                    query_page=query_page,
                    context_pages=context_pages,
                    mcp_tools=mcp_tools,
                    new_conversation=start_new_conversation,
                    all_pages=pages_data,
                )

                # Mark as processed
                self.processed_pages.add(page_id)

            # Find knowledge graph pages
            kg_pages = [
                p for p in pages_data if self._has_tag(p, self.knowledge_graph_tag)
            ]

            # Process each KG page
            for kg_page in kg_pages:
                page_id = kg_page["id"]

                # Skip if already processed
                if page_id in self.processed_pages:
                    continue

                logger.info(
                    f"Processing knowledge graph page {page_id} in notebook {notebook_name}"
                )

                # Process for knowledge graph
                self._process_page_for_knowledge_graph(
                    notebook_id=notebook_id,
                    notebook_name=notebook_name,
                    notebook_path=download_path,
                    notebook_dir=notebook_dir,
                    kg_page=kg_page,
                    all_pages=pages_data,
                )

                # Mark as processed
                self.processed_pages.add(page_id)

        except Exception as e:
            logger.error(f"Error processing notebook {notebook_id}: {e}")
            import traceback

            logger.error(traceback.format_exc())

    def _sanitize_name(self, name):
        """Sanitize a name for use as a directory name.

        Args:
            name: Name to sanitize

        Returns:
            Sanitized name safe for directory usage
        """
        # Replace non-alphanumeric characters (except spaces, hyphens, and underscores) with underscores
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
        # Replace spaces with underscores for better directory naming
        safe_name = safe_name.replace(" ", "_")
        return safe_name

    def _get_notebook_directory(self, notebook_name, metadata=None):
        """Get or create a directory for the specified notebook.

        Args:
            notebook_name: Name of the notebook
            metadata: Optional notebook metadata to extract subject from

        Returns:
            Path to the notebook directory
        """
        # Sanitize notebook name for use as directory name
        safe_notebook_name = self._sanitize_name(notebook_name)

        # Determine subject folder based on metadata or default
        subject = self.default_subject

        # Extract subject from metadata if available
        if metadata and self.use_subject_dirs:
            # Check for subject tag in notebook tags
            if "tags" in metadata and isinstance(metadata["tags"], list):
                for tag in metadata["tags"]:
                    if tag.startswith(f"{self.subject_tag}:"):
                        subject = tag.split(":", 1)[1].strip()
                        logger.info(f"Found subject '{subject}' in notebook tags")
                        break

            # Check for page with subject tag
            if "pages" in metadata and isinstance(metadata["pages"], list):
                for page in metadata["pages"]:
                    if "tags" in page and isinstance(page["tags"], list):
                        for tag in page["tags"]:
                            if tag.startswith(f"{self.subject_tag}:"):
                                subject = tag.split(":", 1)[1].strip()
                                logger.info(f"Found subject '{subject}' in page tags")
                                break

        # Sanitize subject name
        safe_subject = self._sanitize_name(subject)

        # Create directory path based on whether we're using subject directories
        if self.use_subject_dirs:
            subject_dir = os.path.join(self.lilly_dir, safe_subject)
            os.makedirs(subject_dir, exist_ok=True)
            notebook_dir = os.path.join(subject_dir, safe_notebook_name)
        else:
            notebook_dir = os.path.join(self.lilly_dir, safe_notebook_name)

        # Create directory if it doesn't exist
        os.makedirs(notebook_dir, exist_ok=True)
        logger.info(f"Using notebook directory: {notebook_dir}")

        return notebook_dir

    def _get_notebook_metadata(self, notebook_id, notebook_name):
        """Get metadata for a notebook, including tags and subject.

        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook

        Returns:
            Dictionary with notebook metadata or empty dict if not available
        """
        try:
            # Use the rmapi adapter to check for metadata
            # Reusing the _check_document_for_tag method which already downloads and extracts content
            has_tag, metadata = self.rmapi_adapter._check_document_for_tag(
                notebook_id, ""
            )

            if metadata:
                logger.info(f"Retrieved metadata for notebook {notebook_name}")
                return metadata
            else:
                logger.warning(
                    f"Could not retrieve metadata for notebook {notebook_name}"
                )
                return {}
        except Exception as e:
            logger.error(f"Error retrieving notebook metadata: {e}")
            return {}

    def _has_tag(self, page, tag):
        """Check if a page has a specific tag."""
        # Check explicit tags
        if "tags" in page and tag in page["tags"]:
            return True

        # Check for hashtag in text
        if "text" in page:
            tag_pattern = rf"#{tag}\b"
            if re.search(tag_pattern, page["text"], re.IGNORECASE):
                return True

        return False

    def _get_mcp_tools_from_tags(self, page) -> List[str]:
        """Extract MCP tool tags from a page.

        Args:
            page: Page data dictionary

        Returns:
            List of MCP tools to enforce
        """
        tools = []

        # Check for explicit tags that match MCP tool tags
        if "tags" in page:
            tools.extend([tag for tag in page["tags"] if tag in self.mcp_tool_tags])

        # Check for hashtags in text
        if "text" in page:
            for tool in self.mcp_tool_tags:
                tag_pattern = rf"#{tool}\b"
                if re.search(tag_pattern, page["text"], re.IGNORECASE):
                    tools.append(tool)

        return list(set(tools))  # Remove duplicates

    def _extract_notebook_pages(self, notebook_path, extract_dir):
        """Extract pages from notebook and gather metadata.

        Args:
            notebook_path: Path to notebook zip file
            extract_dir: Directory to extract files to

        Returns:
            List of page data dictionaries with page ID, filename, content, tags
        """
        try:
            import zipfile

            # Check if extract_dir already has content files
            content_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(".content"):
                        content_files.append(os.path.join(root, file))

            # If no content files found in extract_dir and notebook_path is a zip file, extract it
            if (
                not content_files
                and os.path.exists(notebook_path)
                and zipfile.is_zipfile(notebook_path)
            ):
                # Extract notebook
                with zipfile.ZipFile(notebook_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

                # Refresh content files list
                content_files = []
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith(".content"):
                            content_files.append(os.path.join(root, file))

            # Check if we found any content files
            if not content_files:
                logger.warning(
                    f"No content file found in notebook {notebook_path} or extraction directory {extract_dir}"
                )
                return []

            # Parse content file (usually only one)
            content_file = content_files[0]
            logger.info(f"Using content file: {content_file}")

            with open(content_file, "r") as f:
                notebook_content = json.load(f)

            # Get pages structure
            pages = notebook_content.get("pages", [])
            logger.info(f"Found {len(pages)} pages in content file")

            # Find all page files and match with content
            page_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(".rm"):
                        page_files.append(
                            {
                                "id": os.path.splitext(file)[0],
                                "path": os.path.join(root, file),
                            }
                        )

            logger.info(f"Found {len(page_files)} .rm files")

            # Match pages with their metadata and extract tags
            pages_data = []
            for page_file in page_files:
                page_id = page_file["id"]

                # Find page metadata from content file
                page_meta = next((p for p in pages if p.get("id") == page_id), {})

                # Get page tags
                tags = page_meta.get("tags", [])
                logger.info(f"Page {page_id} has tags: {tags}")

                # Extract text from page
                page_text = self._extract_text_from_page(page_file["path"])

                # Look for tag indicators like #Lilly, #Context, #kg
                tag_matches = re.findall(r"#(\w+)", page_text)
                for tag in tag_matches:
                    if tag not in tags:
                        tags.append(tag)

                # Add page data
                pages_data.append(
                    {
                        "id": page_id,
                        "path": page_file["path"],
                        "metadata": page_meta,
                        "tags": tags,
                        "text": page_text,
                    }
                )

            # Sort pages by position in notebook
            pages_with_meta = [
                (p, next((meta for meta in pages if meta.get("id") == p["id"]), {}))
                for p in pages_data
            ]
            try:
                pages_data = [
                    p[0]
                    for p in sorted(
                        pages_with_meta,
                        key=lambda x: pages.index(x[1]) if x[1] else 999999,
                    )
                ]
            except Exception as e:
                logger.warning(f"Failed to sort pages: {e}")
                # If sorting fails, keep original order
                pass

            # If we found pages with the Lilly tag, log them
            lilly_pages = [p for p in pages_data if self.query_tag in p["tags"]]
            if lilly_pages:
                logger.info(
                    f"Found {len(lilly_pages)} pages with '{self.query_tag}' tag"
                )
                for p in lilly_pages:
                    logger.info(f"  Page {p['id']} has {self.query_tag} tag")

            return pages_data

        except Exception as e:
            logger.error(f"Error extracting notebook pages: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return []

    def _extract_text_from_page(self, page_path):
        """Extract text from a single page.

        Args:
            page_path: Path to .rm file

        Returns:
            Extracted text
        """
        try:
            # Use handwriting service to extract text
            result = self.handwriting_service.recognize_from_ink(
                file_path=page_path, content_type="Text"
            )

            if result.get("success", False):
                return result.get("text", "")
            else:
                logger.warning(f"Failed to recognize text in {page_path}")
                return ""

        except Exception as e:
            logger.error(f"Error extracting text from page: {e}")
            return ""

    def _process_query_with_context(
        self,
        notebook_id,
        notebook_name,
        notebook_path,
        notebook_dir,
        query_page,
        context_pages,
        mcp_tools,
        new_conversation,
        all_pages,
    ):
        """Process a query page with its context and insert response.

        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook
            notebook_path: Path to downloaded notebook
            notebook_dir: Directory for notebook files
            query_page: Query page data
            context_pages: List of context page data
            mcp_tools: List of MCP tools to enforce
            new_conversation: Whether to start a new conversation
            all_pages: List of all pages in the notebook
        """
        try:
            # Extract query text
            query_text = query_page.get("text", "")
            if not query_text:
                logger.warning(f"No text found in query page {query_page['id']}")
                return

            # Combine context
            context_text = ""
            for ctx_page in context_pages:
                ctx_title = ctx_page.get("metadata", {}).get(
                    "visibleName", f"Context Page {ctx_page['id']}"
                )
                context_text += f"\n\nCONTEXT: {ctx_title}\n{ctx_page.get('text', '')}"

            # Add MCP tools context if any tools specified
            if mcp_tools:
                tools_text = f"\n\nPlease use the following MCP tools in your response: {', '.join(mcp_tools)}"
                context_text += tools_text
                logger.info(f"Enforcing MCP tools: {', '.join(mcp_tools)}")

            # Build prompt with context
            if context_text:
                prompt = f"CONTEXT:\n{context_text}\n\nQUERY:\n{query_text}"
            else:
                prompt = query_text

            # Process with Claude
            response_text = self._process_with_claude(
                notebook_id=notebook_id,
                prompt=prompt,
                new_conversation=new_conversation,
            )

            # Now we need to insert the response after the query page
            self._insert_response_after_query(
                notebook_id=notebook_id,
                notebook_name=notebook_name,
                notebook_path=notebook_path,
                notebook_dir=notebook_dir,
                query_page=query_page,
                response_text=response_text,
                all_pages=all_pages,
            )

            # Remove tags if configured
            if self.remove_tags_after_processing:
                # Determine which tags to remove
                tags_to_remove = [self.query_tag]

                # Only remove the new_conversation_tag if it exists
                if new_conversation:
                    tags_to_remove.append(self.new_conversation_tag)

                # Remove tags from query page
                self._remove_tags_from_page(
                    notebook_id=notebook_id,
                    notebook_name=notebook_name,
                    page_id=query_page["id"],
                    tags_to_remove=tags_to_remove,
                )

                # Remove tags from context pages
                for ctx_page in context_pages:
                    self._remove_tags_from_page(
                        notebook_id=notebook_id,
                        notebook_name=notebook_name,
                        page_id=ctx_page["id"],
                        tags_to_remove=[self.context_tag],
                    )

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            import traceback

            logger.error(traceback.format_exc())

    def _process_with_claude(
        self, notebook_id: str, prompt: str, new_conversation: bool = False
    ) -> str:
        """Process query with Claude CLI.

        Args:
            notebook_id: ID of the notebook for context tracking
            prompt: Text extracted from handwriting
            new_conversation: Whether to start a new conversation

        Returns:
            Response from Claude
        """
        try:
            # Create temporary files for input and output
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".txt", delete=False
            ) as input_file:
                input_path = input_file.name
                # Write query to input file
                input_file.write(prompt)
                input_file.flush()

            output_path = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name

            # Prepare Claude command
            model_flag = f"--model {self.model}" if self.model else ""

            # Determine which context mode to use
            use_context = not new_conversation and notebook_id in self.notebook_contexts

            # Build command based on context strategy
            if self.use_conversation_ids:
                # Use -r flag with conversation ID if we have one
                if use_context and notebook_id in self.notebook_conversation_ids:
                    conversation_id = self.notebook_conversation_ids[notebook_id]
                    context_flag = f"-r {conversation_id}"
                    cmd = f"{self.claude_command} {model_flag} {context_flag} < {input_path} > {output_path}"
                else:
                    # New conversation, will capture and save the ID
                    cmd = f"{self.claude_command} {model_flag} < {input_path} > {output_path} 2> /tmp/claude_stderr.txt"
            else:
                # Use simple -c flag
                context_flag = "-c" if use_context else ""
                cmd = f"{self.claude_command} {model_flag} {context_flag} < {input_path} > {output_path}"

            logger.info(f"Executing Claude command: {cmd}")

            # Execute command
            subprocess.run(cmd, shell=True, check=True)

            # If using conversation IDs and this is a new conversation, try to capture the ID
            if self.use_conversation_ids and (
                new_conversation or notebook_id not in self.notebook_conversation_ids
            ):
                try:
                    # Read stderr which might contain the conversation ID
                    if os.path.exists("/tmp/claude_stderr.txt"):
                        with open("/tmp/claude_stderr.txt", "r") as stderr_file:
                            stderr_content = stderr_file.read()
                            # Look for conversation ID, usually printed like "Conversation: abc123"
                            id_match = re.search(
                                r"Conversation:\s+([a-zA-Z0-9]+)", stderr_content
                            )
                            if id_match:
                                conversation_id = id_match.group(1)
                                self.notebook_conversation_ids[notebook_id] = (
                                    conversation_id
                                )
                                logger.info(
                                    f"Saved conversation ID {conversation_id} for notebook {notebook_id}"
                                )
                                self._save_conversation_ids()
                except Exception as e:
                    logger.error(f"Failed to capture conversation ID: {e}")

            # Mark this notebook as having an active context after successful execution
            self.notebook_contexts[notebook_id] = True

            # Read response
            with open(output_path, "r") as f:
                response = f.read().strip()

            # Clean up temp files
            os.unlink(input_path)
            os.unlink(output_path)
            if os.path.exists("/tmp/claude_stderr.txt"):
                os.unlink("/tmp/claude_stderr.txt")

            return response

        except Exception as e:
            logger.error(f"Error processing with Claude: {e}")
            return f"Error communicating with Claude: {str(e)}"

    def _insert_response_after_query(
        self,
        notebook_id,
        notebook_name,
        notebook_path,
        notebook_dir,
        query_page,
        response_text,
        all_pages,
    ):
        """Insert response page after query page in notebook.

        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook
            notebook_path: Path to downloaded notebook
            notebook_dir: Directory for notebook files
            query_page: Query page data
            response_text: Response text to insert
            all_pages: List of all pages in the notebook
        """
        try:
            import zipfile

            # Create temporary directory for modified notebook
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract notebook
                with zipfile.ZipFile(notebook_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Find content file
                content_file_path = None
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith(".content"):
                            content_file_path = os.path.join(root, file)
                            break

                if not content_file_path:
                    logger.error(f"No content file found in notebook {notebook_path}")
                    return

                # Load content
                with open(content_file_path, "r") as f:
                    content = json.load(f)

                # Find and load metadata file
                metadata_file_path = None
                content_id = os.path.splitext(os.path.basename(content_file_path))[0]
                metadata_file_path = os.path.join(
                    os.path.dirname(content_file_path), f"{content_id}.metadata"
                )

                metadata = {}
                if os.path.exists(metadata_file_path):
                    try:
                        with open(metadata_file_path, "r") as f:
                            metadata = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse metadata file: {metadata_file_path}"
                        )

                # Generate a new page ID
                response_page_id = str(uuid.uuid4())

                # Find position of query page
                pages = content.get("pages", [])
                query_idx = next(
                    (i for i, p in enumerate(pages) if p.get("id") == query_page["id"]),
                    -1,
                )

                if query_idx == -1:
                    logger.error(
                        f"Query page {query_page['id']} not found in notebook content"
                    )
                    return

                # Create response page metadata
                query_title = query_page.get("metadata", {}).get("visibleName", "Query")
                if not query_title or query_title == "Query":
                    query_title = query_page.get("visibleName", "Query")

                # FIXED VERSION: Use millisecond timestamp as string
                now_ms = str(int(time.time() * 1000))
                response_page = {
                    "id": response_page_id,
                    "lastModified": now_ms,  # String representation of milliseconds
                    "lastOpened": now_ms,  # String representation of milliseconds
                    "lastOpenedPage": 0,
                    "pinned": False,
                    "type": "DocumentType",
                    "visibleName": f"Response to {query_title}",
                }

                # Insert response page after query page
                pages.insert(query_idx + 1, response_page)
                content["pages"] = pages

                # Update notebook metadata - FIXED VERSION
                # The key issue is that we need to:
                # 1. Use millisecond timestamps as strings
                # 2. Ensure synced is true, not false
                # 3. Set parent to "" if not specified
                now_ms = str(int(time.time() * 1000))
                metadata.update(
                    {
                        "lastModified": now_ms,
                        "lastOpened": now_ms,
                        "lastOpenedPage": 0,
                        "parent": metadata.get("parent", "")
                        or "",  # Ensure parent is never None
                        "version": metadata.get("version", 1) + 1,
                        "pinned": False,
                        "synced": True,  # Must be true for reMarkable
                        "modified": False,
                        "deleted": False,
                        "metadatamodified": False,
                    }
                )

                # Write updated content
                with open(content_file_path, "w") as f:
                    json.dump(content, f)

                # Write updated metadata
                with open(metadata_file_path, "w") as f:
                    json.dump(metadata, f)

                # Parse response for structured content if needed
                self._parse_response_for_highlighting(response_text)

                # For now, just create basic text page
                # In a real implementation, this would use document service to create .rm file
                # with proper formatting and syntax highlighting
                rm_file_path = os.path.join(
                    os.path.dirname(content_file_path), f"{response_page_id}.rm"
                )

                # Write simple rm file (this is a placeholder, real implementation would use document service)
                with open(rm_file_path, "w") as f:
                    f.write(response_text)

                # Create modified notebook zip in the notebook-specific directory
                modified_filename = (
                    f"modified_{notebook_name}_{time.strftime('%Y%m%d_%H%M%S')}.rmdoc"
                )
                modified_path = os.path.join(notebook_dir, modified_filename)
                self._create_zip_from_directory(temp_dir, modified_path)

                # FIXED VERSION: Refresh to sync with remote state before upload
                logger.info(
                    "Refreshing rmapi to sync with remote state before upload..."
                )
                refresh_success, stdout, stderr = self.rmapi_adapter.run_command(
                    "refresh"
                )
                if not refresh_success:
                    logger.warning(f"Failed to refresh rmapi: {stderr}")
                else:
                    logger.info("Successfully refreshed rmapi")

                # Wait a moment to ensure refresh is complete
                time.sleep(1)

                # Upload modified notebook
                logger.info(f"Uploading modified notebook: {notebook_name}")
                success, message = self.rmapi_adapter.upload_file(
                    modified_path, notebook_name
                )
                if success:
                    logger.info(
                        f"Inserted response to query page {query_page['id']} in notebook {notebook_name}"
                    )
                else:
                    logger.error(f"Failed to upload modified notebook: {message}")

        except Exception as e:
            logger.error(f"Error inserting response: {e}")
            import traceback

            logger.error(traceback.format_exc())

    def _parse_response_for_highlighting(self, response_text):
        """Parse response text for code blocks and apply syntax highlighting.

        Args:
            response_text: Text of the response

        Returns:
            List of structured content items with highlighting
        """
        # Split the response text by code blocks
        items = []
        parts = re.split(r"(```(?:\w+)?\n[\s\S]*?\n```)", response_text)

        for part in parts:
            if part.startswith("```") and part.endswith("```"):
                # This is a code block, extract language and content
                match = re.match(r"```(\w+)?\n([\s\S]*?)\n```", part)
                if match:
                    lang = match.group(1) or "text"
                    code = match.group(2)

                    # If syntax highlighting is enabled, create colored code
                    if self.syntax_highlighting:
                        items.append(
                            {"type": "code_block", "language": lang, "content": code}
                        )
                    else:
                        items.append({"type": "code_block", "content": code})
                else:
                    # Add as regular paragraph if pattern doesn't match
                    items.append({"type": "paragraph", "content": part})
            else:
                # Regular text, add as paragraph(s)
                if part.strip():
                    for line in part.split("\n\n"):
                        if line.strip():
                            # Check for headings
                            heading_match = re.match(r"^(#+)\s+(.+)$", line.strip())
                            if heading_match:
                                level = len(heading_match.group(1))
                                text = heading_match.group(2)
                                items.append(
                                    {"type": f"h{min(level, 3)}", "content": text}
                                )
                            else:
                                items.append({"type": "paragraph", "content": line})

        return items

    def _create_zip_from_directory(self, directory, output_path):
        """Create a zip file from a directory.

        Args:
            directory: Directory to zip
            output_path: Path to save the zip file

        Returns:
            Path to created zip file
        """
        try:
            import zipfile

            with zipfile.ZipFile(output_path, "w") as zipf:
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, directory))

            return output_path

        except Exception as e:
            logger.error(f"Error creating zip from directory: {e}")
            return None

    def _process_page_for_knowledge_graph(
        self,
        notebook_id,
        notebook_name,
        notebook_path,
        notebook_dir,
        kg_page,
        all_pages,
    ):
        """Process a page for knowledge graph extraction.

        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook
            notebook_path: Path to downloaded notebook
            notebook_dir: Directory for notebook files
            kg_page: Knowledge graph page data
            all_pages: List of all pages in the notebook
        """
        try:
            # Check if KG service is available
            if not self.kg_service:
                error_msg = "Knowledge graph service is not available"
                logger.error(error_msg)

                # Create response with error message
                self._insert_response_after_query(
                    notebook_id=notebook_id,
                    notebook_name=notebook_name,
                    notebook_path=notebook_path,
                    notebook_dir=notebook_dir,
                    query_page=kg_page,
                    response_text=f"Error: {error_msg}\n\nKnowledge graph processing is not available.",
                    all_pages=all_pages,
                )
                return

            # Extract page text
            page_text = kg_page.get("text", "")
            if not page_text:
                logger.warning(f"No text found in KG page {kg_page['id']}")
                return

            # Use Claude to extract entities and relationships
            prompt = """
            Extract entities and relationships from the following text.
            Format as JSON with the following structure:
            {
                "entities": [
                    {"name": "Entity Name", "type": "Person/Organization/Concept/Project/Task", "properties": {}}
                ],
                "relationships": [
                    {"from": "Entity1", "to": "Entity2", "type": "relationship type", "properties": {}}
                ]
            }

            TEXT:
            """

            structured_data_text = self._process_with_claude(
                notebook_id=notebook_id, prompt=f"{prompt}\n\n{page_text}"
            )

            # Parse the JSON response
            try:
                # Try to extract JSON from the response
                json_match = re.search(
                    r"```json\n(.*?)\n```", structured_data_text, re.DOTALL
                )
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find JSON without markdown code blocks
                    json_match = re.search(r"(\{.*\})", structured_data_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        json_str = structured_data_text

                # Parse the JSON
                structured_data = json.loads(json_str)

                # Add entities to knowledge graph
                if "entities" in structured_data and structured_data["entities"]:
                    entities_to_add = []
                    for entity in structured_data["entities"]:
                        entities_to_add.append(
                            {
                                "name": entity["name"],
                                "entityType": entity["type"],
                                "observations": [
                                    f"From notebook: {notebook_name} ({notebook_id})",
                                    page_text,  # Add the full text as an observation
                                ],
                            }
                        )

                    if entities_to_add:
                        self.kg_service.create_entities(entities_to_add)
                        logger.info(
                            f"Added {len(entities_to_add)} entities to knowledge graph"
                        )

                # Add relationships to knowledge graph
                if (
                    "relationships" in structured_data
                    and structured_data["relationships"]
                ):
                    relations_to_add = []
                    for relation in structured_data["relationships"]:
                        relations_to_add.append(
                            {
                                "from": relation["from"],
                                "to": relation["to"],
                                "relationType": relation["type"],
                            }
                        )

                    if relations_to_add:
                        self.kg_service.create_relations(relations_to_add)
                        logger.info(
                            f"Added {len(relations_to_add)} relationships to knowledge graph"
                        )

                # Create a response with the summary of KG processing
                summary = f"""
                # Knowledge Graph Processing Results

                Notebook: {notebook_name}
                Page: {kg_page.get('metadata', {}).get('visibleName', 'Page')}

                ## Extracted Entities
                {", ".join([e["name"] for e in structured_data.get("entities", [])])}

                ## Extracted Relationships
                {", ".join([f"{r['from']} {r['type']} {r['to']}" for r in structured_data.get("relationships", [])])}

                The page content has been successfully processed and added to the knowledge graph.
                """

                # Insert the response after the KG page
                self._insert_response_after_query(
                    notebook_id=notebook_id,
                    notebook_name=notebook_name,
                    notebook_path=notebook_path,
                    notebook_dir=notebook_dir,
                    query_page=kg_page,
                    response_text=summary,
                    all_pages=all_pages,
                )

                # Remove tags if configured
                if self.remove_tags_after_processing:
                    self._remove_tags_from_page(
                        notebook_id=notebook_id,
                        notebook_name=notebook_name,
                        page_id=kg_page["id"],
                        tags_to_remove=[self.knowledge_graph_tag],
                    )

            except json.JSONDecodeError as je:
                error_msg = f"Failed to parse JSON from Claude response: {je}"
                logger.error(error_msg)

                # Insert error response
                self._insert_response_after_query(
                    notebook_id=notebook_id,
                    notebook_name=notebook_name,
                    notebook_path=notebook_path,
                    notebook_dir=notebook_dir,
                    query_page=kg_page,
                    response_text=f"Error: {error_msg}\n\nCould not process page for knowledge graph.",
                    all_pages=all_pages,
                )

        except Exception as e:
            logger.error(f"Error processing for knowledge graph: {e}")
            import traceback

            logger.error(traceback.format_exc())

    def _remove_tags_from_page(
        self, notebook_id, notebook_name, page_id, tags_to_remove
    ):
        """Remove tags from a page.

        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook
            page_id: ID of the page
            tags_to_remove: List of tags to remove
        """
        try:
            logger.info(f"Removing tags {tags_to_remove} from page {page_id}")

            # Download the notebook
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = os.path.join(temp_dir, f"{notebook_id}.zip")

                success, _ = self.rmapi_adapter.download_file(
                    notebook_id, download_path, "zip"
                )

                if not success:
                    logger.error(
                        f"Failed to download notebook {notebook_id} for tag removal"
                    )
                    return

                # Extract the notebook
                with zipfile.ZipFile(download_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Find content file
                content_file_path = None
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith(".content"):
                            content_file_path = os.path.join(root, file)
                            break

                if not content_file_path:
                    logger.error(f"No content file found in notebook {notebook_id}")
                    return

                # Load content file
                with open(content_file_path, "r") as f:
                    content = json.load(f)

                # Find the page and remove tags
                pages = content.get("pages", [])
                page_updated = False

                for page in pages:
                    if page.get("id") == page_id:
                        # Update explicit tags
                        if "tags" in page:
                            original_tags = (
                                page["tags"].copy()
                                if isinstance(page["tags"], list)
                                else []
                            )
                            page["tags"] = [
                                tag
                                for tag in original_tags
                                if tag not in tags_to_remove
                            ]
                            if original_tags != page["tags"]:
                                page_updated = True

                if page_updated:
                    # Save the updated content file
                    with open(content_file_path, "w") as f:
                        json.dump(content, f)

                    # Create the modified notebook zip
                    modified_path = os.path.join(
                        self.temp_dir, f"modified_{notebook_id}.zip"
                    )
                    self._create_zip_from_directory(temp_dir, modified_path)

                    # Upload the modified notebook
                    success, message = self.rmapi_adapter.upload_file(
                        modified_path, notebook_name
                    )

                    if success:
                        logger.info(f"Successfully removed tags from page {page_id}")
                    else:
                        logger.error(f"Failed to upload modified notebook: {message}")
                else:
                    logger.info(f"No tags were removed from page {page_id}")

        except Exception as e:
            logger.error(f"Error removing tags: {e}")
            import traceback

            logger.error(traceback.format_exc())
