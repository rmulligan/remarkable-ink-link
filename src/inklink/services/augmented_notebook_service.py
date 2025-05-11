"""Service for augmenting notebooks with AI processing and knowledge graph integration."""

import logging
import os
import re
import time
import tempfile
from typing import Dict, List, Any, Optional, Tuple

from inklink.services.handwriting_recognition_service import HandwritingRecognitionService
from inklink.services.knowledge_graph_service import KnowledgeGraphService
from inklink.services.knowledge_graph_integration_service import KnowledgeGraphIntegrationService
from inklink.services.ai_service import AIService
from inklink.services.document_service import DocumentService
from inklink.services.remarkable_service import RemarkableService
from inklink.services.web_scraper_service import WebScraperService
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class AugmentedNotebookService:
    """
    Service for augmenting reMarkable notebooks with AI processing, 
    knowledge graph integration, and tag-based actions.
    
    This service provides a comprehensive workflow:
    1. Transcribe handwritten content from reMarkable notebooks
    2. Process content through Claude Code for tag detection and request handling
    3. Categorize all correspondence in the knowledge graph
    4. Generate responses using web search, knowledge graph and Claude
    5. Convert responses back to ink format and append to notebook
    """
    
    def __init__(
        self,
        handwriting_service: Optional[HandwritingRecognitionService] = None,
        knowledge_graph_service: Optional[KnowledgeGraphService] = None,
        kg_integration_service: Optional[KnowledgeGraphIntegrationService] = None,
        ai_service: Optional[AIService] = None,
        document_service: Optional[DocumentService] = None,
        remarkable_service: Optional[RemarkableService] = None,
        web_scraper_service: Optional[WebScraperService] = None,
    ):
        """
        Initialize the augmented notebook service.
        
        Args:
            handwriting_service: Service for handwriting recognition
            knowledge_graph_service: Service for knowledge graph operations
            kg_integration_service: Service for knowledge graph integration
            ai_service: Service for AI processing
            document_service: Service for document creation
            remarkable_service: Service for reMarkable interactions
            web_scraper_service: Service for web scraping
        """
        # Initialize services
        self.handwriting_service = handwriting_service or HandwritingRecognitionService()
        self.knowledge_graph_service = knowledge_graph_service or KnowledgeGraphService()
        self.kg_integration_service = kg_integration_service or KnowledgeGraphIntegrationService(
            handwriting_service=self.handwriting_service,
            knowledge_graph_service=self.knowledge_graph_service
        )
        self.ai_service = ai_service or AIService()
        self.document_service = document_service or DocumentService()
        self.remarkable_service = remarkable_service or RemarkableService()
        self.web_scraper_service = web_scraper_service or WebScraperService()
        
        # Configuration
        self.temp_dir = CONFIG.get("TEMP_DIR", "temp")
        self.claude_model = CONFIG.get("CLAUDE_MODEL", "claude-3-5-sonnet")
        self.tag_pattern = re.compile(r'#([a-zA-Z0-9_\-:]+)')
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def process_notebook_page(
        self, 
        rm_file_path: str,
        append_response: bool = True,
        extract_knowledge: bool = True,
        categorize_correspondence: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a reMarkable notebook page through the complete workflow.
        
        Args:
            rm_file_path: Path to the .rm file
            append_response: Whether to append the response to the notebook
            extract_knowledge: Whether to extract knowledge to the graph
            categorize_correspondence: Whether to categorize the correspondence
            
        Returns:
            Tuple of (success, result dictionary)
        """
        try:
            logger.info(f"Processing notebook page: {rm_file_path}")
            
            # Step 1: Transcribe handwritten content
            recognized_text = self._recognize_text_from_file(rm_file_path)
            if not recognized_text:
                return False, {"error": "Failed to recognize text from notebook page"}
            
            # Step 2: Extract tags and identify requests
            tags = self._extract_tags(recognized_text)
            requests = self._identify_requests(recognized_text)
            
            # Step 3: Extract knowledge to graph if enabled
            knowledge_results = {}
            if extract_knowledge:
                success, extract_result = self.kg_integration_service.extract_knowledge_from_notebook(
                    rm_file_path=rm_file_path
                )
                if success:
                    knowledge_results = {
                        "entities": extract_result.get("created_entities", []),
                        "relationships": extract_result.get("created_relationships", []),
                        "semantic_links": extract_result.get("semantic_links", [])
                    }
            
            # Step 4: Process through Claude Code
            processed_results = self._process_with_claude_code(
                text=recognized_text,
                tags=tags,
                requests=requests,
                knowledge_results=knowledge_results
            )
            
            # Step 5: Categorize correspondence if enabled
            if categorize_correspondence and processed_results.get("response"):
                self._categorize_correspondence(
                    query=recognized_text,
                    response=processed_results.get("response"),
                    context=processed_results.get("context", {})
                )
            
            # Step 6: Append response to notebook if enabled
            append_results = {}
            if append_response and processed_results.get("response"):
                success, append_result = self._append_response_to_notebook(
                    rm_file_path=rm_file_path,
                    response=processed_results.get("response"),
                    include_sources=processed_results.get("sources", [])
                )
                if success:
                    append_results = append_result
            
            # Combine results
            result = {
                "recognized_text": recognized_text,
                "tags": tags,
                "requests": requests,
                "knowledge_extracted": knowledge_results,
                "claude_processing": processed_results,
                "append_results": append_results
            }
            
            return True, result
            
        except Exception as e:
            logger.error(f"Error processing notebook page: {e}")
            return False, {"error": f"Processing failed: {str(e)}"}
    
    def _recognize_text_from_file(self, rm_file_path: str) -> Optional[str]:
        """
        Recognize text from a reMarkable file.
        
        Args:
            rm_file_path: Path to the .rm file
            
        Returns:
            Recognized text or None if recognition failed
        """
        try:
            # Extract strokes from file
            strokes = self.handwriting_service.extract_strokes(rm_file_path)
            if not strokes:
                logger.warning(f"No strokes found in file: {rm_file_path}")
                return None
            
            # Convert to iink format
            iink_data = self.handwriting_service.convert_to_iink_format(strokes)
            
            # Recognize handwriting
            recognition_result = self.handwriting_service.recognize_handwriting(iink_data)
            if not recognition_result.get("success", False):
                logger.warning(f"Recognition failed: {recognition_result.get('error')}")
                return None
            
            # Export as text
            content_id = recognition_result.get("content_id")
            export_result = self.handwriting_service.export_content(content_id, "text")
            if not export_result.get("success", False):
                logger.warning(f"Export failed: {export_result.get('error')}")
                return None
            
            # Extract the recognized text
            recognized_text = export_result.get("content", {}).get("text", "").strip()
            return recognized_text
            
        except Exception as e:
            logger.error(f"Error recognizing text from file: {e}")
            return None
    
    def _extract_tags(self, text: str) -> List[str]:
        """
        Extract tags from text.
        
        Args:
            text: Input text
            
        Returns:
            List of extracted tags
        """
        if not text:
            return []
        
        # Extract tags using regex
        tags = self.tag_pattern.findall(text)
        return tags
    
    def _identify_requests(self, text: str) -> List[Dict[str, Any]]:
        """
        Identify requests in text.
        
        Args:
            text: Input text
            
        Returns:
            List of identified requests
        """
        if not text:
            return []
        
        # Use AI service to identify requests
        prompt = f"""
        Identify any requests or questions in the following text:
        
        {text}
        
        Return a JSON list where each item has these properties:
        - request_text: The actual request or question
        - request_type: The type of request (info, action, clarification, etc.)
        - priority: Estimated priority (high, medium, low)
        
        Only return valid JSON without any explanations.
        """
        
        response = self.ai_service.generate_text(prompt, max_tokens=1000)
        
        try:
            import json
            requests = json.loads(response)
            return requests
        except Exception:
            # If parsing fails, use simple heuristic approach
            lines = text.split('\n')
            requests = []
            
            for line in lines:
                if '?' in line or any(keyword in line.lower() for keyword in ['find', 'search', 'get', 'tell me', 'explain']):
                    requests.append({
                        "request_text": line.strip(),
                        "request_type": "info" if '?' in line else "action",
                        "priority": "medium"
                    })
            
            return requests
    
    def _process_with_claude_code(
        self, 
        text: str,
        tags: List[str],
        requests: List[Dict[str, Any]],
        knowledge_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process text with Claude Code.
        
        Args:
            text: Input text
            tags: Extracted tags
            requests: Identified requests
            knowledge_results: Results from knowledge extraction
            
        Returns:
            Processing results
        """
        # Create context for Claude
        context = {
            "tags": tags,
            "requests": requests,
            "knowledge_graph": {
                "entities": [e.get("name") for e in knowledge_results.get("entities", [])],
                "relationships": knowledge_results.get("relationships", [])
            }
        }
        
        # Determine actions based on tags
        actions = []
        for tag in tags:
            if tag.startswith("tool:"):
                # Extract tool type and action
                parts = tag.split(":")
                if len(parts) >= 3:
                    tool_type = parts[1]
                    action = parts[2]
                    actions.append({"tool": tool_type, "action": action})
        
        # Build search queries based on requests
        search_results = []
        if requests:
            primary_request = requests[0]["request_text"]
            
            # Perform web search if relevant
            if any(keyword in primary_request.lower() for keyword in ["search", "find", "latest", "current", "news"]):
                try:
                    search_query = primary_request.replace("?", "").strip()
                    success, result = self.web_scraper_service.search_web(search_query)
                    
                    if success:
                        search_results = result.get("results", [])
                except Exception as e:
                    logger.warning(f"Web search failed: {e}")
            
            # Perform knowledge graph search
            try:
                success, kg_result = self.knowledge_graph_service.find_semantically_similar_text(
                    text=primary_request,
                    min_similarity=0.6,
                    max_results=5
                )
                
                if success:
                    context["kg_search"] = kg_result.get("results", [])
            except Exception as e:
                logger.warning(f"Knowledge graph search failed: {e}")
        
        # Generate response using Claude
        system_prompt = """
        You are Claude, an AI assistant helping users with their handwritten notes on a reMarkable tablet.
        
        The user's handwritten note has been transcribed and analyzed for you. 
        The text, extracted tags, identified requests, and knowledge graph information are provided.
        
        Your task is to:
        1. Respond to any questions or requests in the user's note
        2. Consider the knowledge graph entities and relationships for context
        3. Incorporate web search information when available
        4. Format your response clearly with headings and list items for readability when converted to ink
        5. Include sources and references for factual information
        
        Your response will be converted back to ink format and appended to the user's notebook.
        """
        
        user_prompt = f"""
        # User's Handwritten Note:
        {text}
        
        # Extracted Tags:
        {', '.join(tags) if tags else 'None'}
        
        # Identified Requests:
        {requests if requests else 'None'}
        
        # Knowledge Graph Information:
        Entities: {', '.join(context["knowledge_graph"]["entities"]) if context["knowledge_graph"]["entities"] else 'None'}
        
        # Web Search Results:
        {search_results if search_results else 'None'}
        
        # Knowledge Graph Search Results:
        {context.get("kg_search", []) if "kg_search" in context else 'None'}
        
        Please provide a helpful response that addresses the user's requests and incorporates relevant knowledge.
        """
        
        response = self.ai_service.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=4000
        )
        
        # Extract sources from response
        sources = self._extract_sources(response)
        
        return {
            "response": response,
            "sources": sources,
            "context": context
        }
    
    def _categorize_correspondence(
        self,
        query: str,
        response: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Categorize correspondence in the knowledge graph.
        
        Args:
            query: User query
            response: AI response
            context: Context information
        """
        try:
            # Create query entity
            success, query_entity = self.knowledge_graph_service.create_entity(
                name=f"Query_{int(time.time())}",
                entity_type="UserQuery",
                observations=[query]
            )
            
            if not success:
                logger.warning("Failed to create query entity")
                return
            
            # Create response entity
            success, response_entity = self.knowledge_graph_service.create_entity(
                name=f"Response_{int(time.time())}",
                entity_type="AIResponse",
                observations=[response]
            )
            
            if not success:
                logger.warning("Failed to create response entity")
                return
                
            # Link query and response
            self.knowledge_graph_service.create_relationship(
                from_entity=query_entity["name"],
                to_entity=response_entity["name"],
                relationship_type="ANSWERED_BY"
            )
            
            # Link to topics from context
            for entity_name in context.get("knowledge_graph", {}).get("entities", []):
                self.knowledge_graph_service.create_relationship(
                    from_entity=query_entity["name"],
                    to_entity=entity_name,
                    relationship_type="REFERENCES"
                )
                
                self.knowledge_graph_service.create_relationship(
                    from_entity=response_entity["name"],
                    to_entity=entity_name,
                    relationship_type="REFERENCES"
                )
                
        except Exception as e:
            logger.error(f"Error categorizing correspondence: {e}")
    
    def _extract_sources(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract sources from response text.
        
        Args:
            text: Response text
            
        Returns:
            List of sources
        """
        sources = []
        
        # Look for source patterns like URLs, citations, etc.
        url_pattern = re.compile(r'https?://[^\s]+')
        urls = url_pattern.findall(text)
        
        for url in urls:
            sources.append({
                "type": "url",
                "value": url
            })
            
        # Look for reference patterns like [1], [2], etc.
        ref_pattern = re.compile(r'\[\d+\]')
        refs = ref_pattern.findall(text)
        
        # Extract referenced content
        for ref in refs:
            ref_num = ref.strip('[]')
            ref_content_pattern = re.compile(rf'\[{ref_num}\]:\s*(.*?)(?:\n\[\d+\]:|$)', re.DOTALL)
            match = ref_content_pattern.search(text)
            
            if match:
                sources.append({
                    "type": "reference",
                    "value": match.group(1).strip()
                })
                
        return sources
    
    def _append_response_to_notebook(
        self,
        rm_file_path: str,
        response: str,
        include_sources: List[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Append response to notebook page.
        
        Args:
            rm_file_path: Path to the .rm file
            response: Response to append
            include_sources: Sources to include
            
        Returns:
            Tuple of (success, result)
        """
        try:
            # Format response with sources
            formatted_response = response
            
            if include_sources:
                formatted_response += "\n\n# Sources\n"
                for i, source in enumerate(include_sources):
                    formatted_response += f"\n{i+1}. {source['value']}"
            
            # Create markdown content
            import time
            timestamp = int(time.time())
            md_filename = f"response_{timestamp}.md"
            md_path = os.path.join(self.temp_dir, md_filename)
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(formatted_response)
            
            # Convert to reMarkable format
            rm_path = self.document_service.create_rmdoc_from_content(
                url="",
                qr_path="",
                content={
                    "title": "AI Response",
                    "structured_content": [
                        {"type": "markdown", "content": formatted_response}
                    ],
                }
            )
            
            if not rm_path:
                return False, {"error": "Failed to create response document"}
                
            # Get original page metadata
            page_info = os.path.basename(rm_file_path)
            
            # Upload to reMarkable with appropriate title
            title = f"Response {timestamp}"
            success, message = self.remarkable_service.upload(rm_path, title)
            
            if not success:
                return False, {"error": f"Upload failed: {message}"}
                
            return True, {
                "response_path": rm_path,
                "title": title,
                "upload_message": message
            }
            
        except Exception as e:
            logger.error(f"Error appending response to notebook: {e}")
            return False, {"error": f"Failed to append response: {str(e)}"}