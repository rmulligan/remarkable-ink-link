#!/usr/bin/env python
"""Claude Penpal Service - Monitors reMarkable notebooks for handwritten queries.

This service provides a penpal-style interaction with Claude, where:
- Notebooks are organized by subject
- Queries are identified with #Lilly tags
- Context is provided with #Context tags
- Knowledge graph processing uses #kg tags
- Responses are inserted directly after query pages
"""

import os
import time
import logging
import tempfile
import threading
import json
import re
import uuid
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from inklink.adapters.rmapi_adapter import RmapiAdapter
from inklink.services.handwriting_recognition_service import HandwritingRecognitionService
from inklink.services.document_service import DocumentService
from inklink.config import CONFIG

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
        poll_interval: int = 60,
        syntax_highlighting: bool = True,
        remove_tags_after_processing: bool = True
    ):
        """Initialize the service with necessary components.
        
        Args:
            rmapi_path: Path to rmapi executable
            claude_command: Command to invoke Claude CLI
            model: Claude model to use
            query_tag: Tag to identify query pages (default: Lilly)
            context_tag: Tag to identify additional context pages
            knowledge_graph_tag: Tag to identify pages for KG processing (default: kg)
            poll_interval: How often to check for new pages (seconds)
            syntax_highlighting: Whether to enable syntax highlighting for code
            remove_tags_after_processing: Whether to remove tags after processing
        """
        self.rmapi_path = rmapi_path or CONFIG.get("RMAPI_PATH")
        self.claude_command = claude_command or CONFIG.get("CLAUDE_COMMAND", "claude")
        self.model = model or CONFIG.get("CLAUDE_MODEL", "")
        self.query_tag = query_tag
        self.context_tag = context_tag
        self.knowledge_graph_tag = knowledge_graph_tag
        self.poll_interval = poll_interval
        self.syntax_highlighting = syntax_highlighting
        self.remove_tags_after_processing = remove_tags_after_processing
        self.temp_dir = CONFIG.get("TEMP_DIR")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Initialize components
        self.rmapi_adapter = RmapiAdapter(self.rmapi_path)
        self.handwriting_service = HandwritingRecognitionService(
            claude_command=self.claude_command,
            model=self.model
        )
        self.document_service = DocumentService(
            output_dir=self.temp_dir,
            drawj2d_path=CONFIG.get("DRAWJ2D_PATH")
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
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
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
                # Use rmapi to list all notebooks
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
                
            # Wait for next poll interval
            time.sleep(self.poll_interval)

    def _check_notebook_for_tagged_pages(self, notebook):
        """Check a notebook for pages with tags.
        
        Args:
            notebook: Notebook information from rmapi
        """
        notebook_id = notebook.get("ID")
        notebook_name = notebook.get("VissibleName", "Notebook")  # Note: typo from API
        
        try:
            # Download notebook
            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = os.path.join(temp_dir, f"{notebook_id}.zip")
                success, _ = self.rmapi_adapter.download_file(notebook_id, download_path, "zip")
                
                if not success:
                    logger.warning(f"Failed to download notebook {notebook_id}")
                    return
                    
                # Extract and scan for tagged pages
                pages_data = self._extract_notebook_pages(download_path, temp_dir)
                
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
                        
                    logger.info(f"Processing query page {page_id} in notebook {notebook_name}")
                    
                    # Find context pages (must come before the query page)
                    page_idx = pages_data.index(query_page)
                    context_pages = [
                        p for p in pages_data[:page_idx] 
                        if self._has_tag(p, self.context_tag)
                    ]
                    
                    # Process the query with context
                    self._process_query_with_context(
                        notebook_id=notebook_id,
                        notebook_name=notebook_name,
                        notebook_path=download_path,
                        query_page=query_page,
                        context_pages=context_pages,
                        all_pages=pages_data
                    )
                    
                    # Mark as processed
                    self.processed_pages.add(page_id)
                    
                # Find knowledge graph pages
                kg_pages = [p for p in pages_data if self._has_tag(p, self.knowledge_graph_tag)]
                
                # Process each KG page
                for kg_page in kg_pages:
                    page_id = kg_page["id"]
                    
                    # Skip if already processed
                    if page_id in self.processed_pages:
                        continue
                        
                    logger.info(f"Processing knowledge graph page {page_id} in notebook {notebook_name}")
                    
                    # Process for knowledge graph
                    self._process_page_for_knowledge_graph(
                        notebook_id=notebook_id,
                        notebook_name=notebook_name,
                        notebook_path=download_path,
                        kg_page=kg_page,
                        all_pages=pages_data
                    )
                    
                    # Mark as processed
                    self.processed_pages.add(page_id)
                    
        except Exception as e:
            logger.error(f"Error processing notebook {notebook_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
    def _has_tag(self, page, tag):
        """Check if a page has a specific tag."""
        # Check explicit tags
        if "tags" in page and tag in page["tags"]:
            return True
            
        # Check for hashtag in text
        if "text" in page:
            tag_pattern = rf'#{tag}\b'
            if re.search(tag_pattern, page["text"], re.IGNORECASE):
                return True
                
        return False
            
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
            
            # Extract notebook
            with zipfile.ZipFile(notebook_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            # Find content file
            content_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.content'):
                        content_files.append(os.path.join(root, file))
                        
            if not content_files:
                logger.warning(f"No content file found in notebook {notebook_path}")
                return []
                
            # Parse content file (usually only one)
            content_file = content_files[0]
            with open(content_file, 'r') as f:
                notebook_content = json.load(f)
                
            # Get pages structure
            pages = notebook_content.get("pages", [])
            
            # Find all page files and match with content
            page_files = []
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.rm'):
                        page_files.append({
                            "id": os.path.splitext(file)[0],
                            "path": os.path.join(root, file)
                        })
            
            # Match pages with their metadata and extract tags
            pages_data = []
            for page_file in page_files:
                page_id = page_file["id"]
                
                # Find page metadata from content file
                page_meta = next((p for p in pages if p.get("id") == page_id), {})
                
                # Get page tags
                tags = page_meta.get("tags", [])
                
                # Extract text from page
                page_text = self._extract_text_from_page(page_file["path"])
                
                # Look for tag indicators like #Lilly, #Context, #kg
                tag_matches = re.findall(r'#(\w+)', page_text)
                for tag in tag_matches:
                    if tag not in tags:
                        tags.append(tag)
                
                # Add page data
                pages_data.append({
                    "id": page_id,
                    "path": page_file["path"],
                    "metadata": page_meta,
                    "tags": tags,
                    "text": page_text
                })
            
            # Sort pages by position in notebook
            pages_with_meta = [(p, next((meta for meta in pages if meta.get("id") == p["id"]), {})) 
                              for p in pages_data]
            try:
                pages_data = [p[0] for p in sorted(pages_with_meta, 
                                                  key=lambda x: pages.index(x[1]) if x[1] else 999999)]
            except Exception:
                # If sorting fails, keep original order
                pass
            
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
                file_path=page_path, 
                content_type="Text"
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
        query_page,
        context_pages,
        all_pages
    ):
        """Process a query page with its context and insert response.
        
        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook
            notebook_path: Path to downloaded notebook
            query_page: Query page data
            context_pages: List of context page data
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
                ctx_title = ctx_page.get("metadata", {}).get("visibleName", f"Context Page {ctx_page['id']}")
                context_text += f"\n\nCONTEXT: {ctx_title}\n{ctx_page.get('text', '')}"
                
            # Build prompt with context
            if context_text:
                prompt = f"CONTEXT:\n{context_text}\n\nQUERY:\n{query_text}"
            else:
                prompt = query_text
                
            # Process with Claude
            response_text = self._process_with_claude(prompt)
            
            # Now we need to insert the response after the query page
            self._insert_response_after_query(
                notebook_id=notebook_id,
                notebook_name=notebook_name,
                notebook_path=notebook_path,
                query_page=query_page,
                response_text=response_text,
                all_pages=all_pages
            )
            
            # Remove tags if configured
            if self.remove_tags_after_processing:
                # Remove tags from query page
                self._remove_tags_from_page(
                    notebook_id=notebook_id,
                    notebook_name=notebook_name,
                    page_id=query_page["id"],
                    tags_to_remove=[self.query_tag]
                )
                
                # Remove tags from context pages
                for ctx_page in context_pages:
                    self._remove_tags_from_page(
                        notebook_id=notebook_id,
                        notebook_name=notebook_name,
                        page_id=ctx_page["id"],
                        tags_to_remove=[self.context_tag]
                    )
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _process_with_claude(self, query_text: str) -> str:
        """Process query with Claude CLI.
        
        Args:
            query_text: Text extracted from handwriting
            
        Returns:
            Response from Claude
        """
        try:
            # Create temporary files for input and output
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as input_file:
                input_path = input_file.name
                # Write query to input file
                input_file.write(query_text)
                input_file.flush()
            
            output_path = tempfile.NamedTemporaryFile(suffix='.txt', delete=False).name
            
            # Prepare Claude command
            model_flag = f"--model {self.model}" if self.model else ""
            cmd = f'{self.claude_command} {model_flag} < {input_path} > {output_path}'
            
            # Execute command
            subprocess.run(cmd, shell=True, check=True)
            
            # Read response
            with open(output_path, 'r') as f:
                response = f.read().strip()
            
            # Clean up temp files
            os.unlink(input_path)
            os.unlink(output_path)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing with Claude: {e}")
            return f"Error communicating with Claude: {str(e)}"
            
    def _insert_response_after_query(
        self,
        notebook_id,
        notebook_name,
        notebook_path,
        query_page,
        response_text,
        all_pages
    ):
        """Insert response page after query page in notebook.
        
        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook
            notebook_path: Path to downloaded notebook
            query_page: Query page data
            response_text: Response text to insert
            all_pages: List of all pages in the notebook
        """
        try:
            import zipfile
            
            # Create temporary directory for modified notebook
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract notebook
                with zipfile.ZipFile(notebook_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                    
                # Find content file
                content_file_path = None
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.content'):
                            content_file_path = os.path.join(root, file)
                            break
                            
                if not content_file_path:
                    logger.error(f"No content file found in notebook {notebook_path}")
                    return
                    
                # Load content
                with open(content_file_path, 'r') as f:
                    content = json.load(f)
                    
                # Generate a new page ID
                response_page_id = str(uuid.uuid4())
                
                # Find position of query page
                pages = content.get("pages", [])
                query_idx = next((i for i, p in enumerate(pages) if p.get("id") == query_page["id"]), -1)
                
                if query_idx == -1:
                    logger.error(f"Query page {query_page['id']} not found in notebook content")
                    return
                    
                # Create response page metadata
                query_title = query_page.get("metadata", {}).get("visibleName", "Query")
                now = datetime.now().isoformat()
                response_page = {
                    "id": response_page_id,
                    "lastModified": now,
                    "lastOpened": now,
                    "lastOpenedPage": 0,
                    "pinned": False,
                    "synced": False,
                    "type": "DocumentType",
                    "visibleName": f"Response to {query_title}"
                }
                
                # Insert response page after query page
                pages.insert(query_idx + 1, response_page)
                content["pages"] = pages
                
                # Write updated content
                with open(content_file_path, 'w') as f:
                    json.dump(content, f)
                    
                # Create response page with syntax highlighting
                structured_content = self._parse_response_for_highlighting(response_text)
                
                # For now, just create basic text page
                # In a real implementation, this would use document service to create .rm file
                # with proper formatting and syntax highlighting
                rm_file_path = os.path.join(os.path.dirname(content_file_path), f"{response_page_id}.rm")
                
                # Write simple rm file (this is a placeholder, real implementation would use document service)
                with open(rm_file_path, 'w') as f:
                    f.write(response_text)
                
                # Create modified notebook zip
                modified_path = os.path.join(self.temp_dir, f"modified_{os.path.basename(notebook_path)}")
                self._create_zip_from_directory(temp_dir, modified_path)
                
                # Upload modified notebook
                success, message = self.rmapi_adapter.upload_file(modified_path, notebook_name)
                if success:
                    logger.info(f"Inserted response to query page {query_page['id']} in notebook {notebook_name}")
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
        parts = re.split(r'(```(?:\w+)?\n[\s\S]*?\n```)', response_text)
        
        for part in parts:
            if part.startswith('```') and part.endswith('```'):
                # This is a code block, extract language and content
                match = re.match(r'```(\w+)?\n([\s\S]*?)\n```', part)
                if match:
                    lang = match.group(1) or 'text'
                    code = match.group(2)
                    
                    # If syntax highlighting is enabled, create colored code
                    if self.syntax_highlighting:
                        items.append({
                            "type": "code_block",
                            "language": lang,
                            "content": code
                        })
                    else:
                        items.append({
                            "type": "code_block",
                            "content": code
                        })
                else:
                    # Add as regular paragraph if pattern doesn't match
                    items.append({
                        "type": "paragraph",
                        "content": part
                    })
            else:
                # Regular text, add as paragraph(s)
                if part.strip():
                    for line in part.split('\n\n'):
                        if line.strip():
                            # Check for headings
                            heading_match = re.match(r'^(#+)\s+(.+)$', line.strip())
                            if heading_match:
                                level = len(heading_match.group(1))
                                text = heading_match.group(2)
                                items.append({
                                    "type": f"h{min(level, 3)}",
                                    "content": text
                                })
                            else:
                                items.append({
                                    "type": "paragraph",
                                    "content": line
                                })
        
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
            
            with zipfile.ZipFile(output_path, 'w') as zipf:
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(
                            file_path, 
                            os.path.relpath(file_path, directory)
                        )
                        
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating zip from directory: {e}")
            return None
            
    def _process_page_for_knowledge_graph(
        self,
        notebook_id,
        notebook_name,
        notebook_path,
        kg_page,
        all_pages
    ):
        """Process a page for knowledge graph extraction.
        
        Args:
            notebook_id: ID of the notebook
            notebook_name: Name of the notebook
            notebook_path: Path to downloaded notebook
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
                    query_page=kg_page,
                    response_text=f"Error: {error_msg}\n\nKnowledge graph processing is not available.",
                    all_pages=all_pages
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
            
            structured_data_text = self._process_with_claude(f"{prompt}\n\n{page_text}")
            
            # Parse the JSON response
            try:
                # Try to extract JSON from the response
                json_match = re.search(r'```json\n(.*?)\n```', structured_data_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find JSON without markdown code blocks
                    json_match = re.search(r'(\{.*\})', structured_data_text, re.DOTALL)
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
                        entities_to_add.append({
                            "name": entity["name"],
                            "entityType": entity["type"],
                            "observations": [
                                f"From notebook: {notebook_name} ({notebook_id})",
                                page_text  # Add the full text as an observation
                            ]
                        })
                    
                    if entities_to_add:
                        self.kg_service.create_entities(entities_to_add)
                        logger.info(f"Added {len(entities_to_add)} entities to knowledge graph")
                
                # Add relationships to knowledge graph
                if "relationships" in structured_data and structured_data["relationships"]:
                    relations_to_add = []
                    for relation in structured_data["relationships"]:
                        relations_to_add.append({
                            "from": relation["from"],
                            "to": relation["to"],
                            "relationType": relation["type"]
                        })
                    
                    if relations_to_add:
                        self.kg_service.create_relations(relations_to_add)
                        logger.info(f"Added {len(relations_to_add)} relationships to knowledge graph")
                
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
                    query_page=kg_page,
                    response_text=summary,
                    all_pages=all_pages
                )
                
                # Remove tags if configured
                if self.remove_tags_after_processing:
                    self._remove_tags_from_page(
                        notebook_id=notebook_id,
                        notebook_name=notebook_name,
                        page_id=kg_page["id"],
                        tags_to_remove=[self.knowledge_graph_tag]
                    )
                
            except json.JSONDecodeError as je:
                error_msg = f"Failed to parse JSON from Claude response: {je}"
                logger.error(error_msg)
                
                # Insert error response
                self._insert_response_after_query(
                    notebook_id=notebook_id,
                    notebook_name=notebook_name,
                    notebook_path=notebook_path,
                    query_page=kg_page,
                    response_text=f"Error: {error_msg}\n\nCould not process page for knowledge graph.",
                    all_pages=all_pages
                )
                
        except Exception as e:
            logger.error(f"Error processing for knowledge graph: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
    def _remove_tags_from_page(self, notebook_id, notebook_name, page_id, tags_to_remove):
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
                    logger.error(f"Failed to download notebook {notebook_id} for tag removal")
                    return
                    
                # Extract the notebook
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                    
                # Find content file
                content_file_path = None
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.content'):
                            content_file_path = os.path.join(root, file)
                            break
                            
                if not content_file_path:
                    logger.error(f"No content file found in notebook {notebook_id}")
                    return
                    
                # Load content file
                with open(content_file_path, 'r') as f:
                    content = json.load(f)
                    
                # Find the page and remove tags
                pages = content.get("pages", [])
                page_updated = False
                
                for page in pages:
                    if page.get("id") == page_id:
                        # Update explicit tags
                        if "tags" in page:
                            original_tags = page["tags"].copy() if isinstance(page["tags"], list) else []
                            page["tags"] = [tag for tag in original_tags if tag not in tags_to_remove]
                            if original_tags != page["tags"]:
                                page_updated = True
                                
                if page_updated:
                    # Save the updated content file
                    with open(content_file_path, 'w') as f:
                        json.dump(content, f)
                        
                    # Create the modified notebook zip
                    modified_path = os.path.join(self.temp_dir, f"modified_{notebook_id}.zip")
                    self._create_zip_from_directory(temp_dir, modified_path)
                    
                    # Upload the modified notebook
                    success, message = self.rmapi_adapter.upload_file(modified_path, notebook_name)
                    
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