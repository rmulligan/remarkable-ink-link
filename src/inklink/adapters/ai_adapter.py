"""AI Adapter for InkLink.

This module provides adapters for AI service APIs (OpenAI, etc).
"""

import os
import logging
import requests
from typing import Dict, Any, List, Optional, Union, Tuple

from inklink.adapters.adapter import Adapter
from inklink.utils import retry_operation, format_error

logger = logging.getLogger(__name__)


class AIAdapter(Adapter):
    """Adapter for AI APIs like OpenAI."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        system_prompt: Optional[str] = None,
        provider: str = "openai"
    ):
        """
        Initialize AIAdapter.
        
        Args:
            api_key: API key for the AI provider
            model: Model name to use (e.g., 'gpt-3.5-turbo')
            api_base: Base URL for API requests
            system_prompt: Default system prompt
            provider: AI provider ('openai', 'anthropic', etc.)
        """
        self.provider = provider.lower()
        
        # Set up API key, falling back to environment variables
        self.api_key = api_key or os.environ.get(f"{self.provider.upper()}_API_KEY")
        if not self.api_key:
            # General fallbacks
            self.api_key = os.environ.get("AI_API_KEY") or os.environ.get("LLM_API_KEY")
            if not self.api_key:
                logger.warning(f"No API key found for {self.provider}, AI features may not work")
        
        # Set up model, API base, and system prompt
        self.model = model or os.environ.get(f"{self.provider.upper()}_MODEL")
        if not self.model:
            # Default models by provider
            if self.provider == "openai":
                self.model = "gpt-3.5-turbo"
            elif self.provider == "anthropic":
                self.model = "claude-3-sonnet-20240229"
            
        # API base URL
        self.api_base = api_base or os.environ.get(f"{self.provider.upper()}_API_BASE")
        if not self.api_base:
            if self.provider == "openai":
                self.api_base = "https://api.openai.com/v1"
            elif self.provider == "anthropic":
                self.api_base = "https://api.anthropic.com/v1"
        
        # System prompt
        self.system_prompt = system_prompt or os.environ.get(f"{self.provider.upper()}_SYSTEM_PROMPT")
        if not self.system_prompt:
            self.system_prompt = "You are a helpful assistant."
            
    def ping(self) -> bool:
        """
        Check if the AI service is available.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try a minimal API call to check availability
            if self.provider == "openai":
                url = f"{self.api_base}/models"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.get(url, headers=headers, timeout=5)
                return response.status_code == 200
                
            # Add other provider checks as needed
            return False
            
        except Exception as e:
            logger.error(f"AI API not available: {e}")
            return False
    
    def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[bool, str]:
        """
        Generate completion from the AI model.
        
        Args:
            prompt: User prompt text
            system_prompt: System prompt to override default
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0.0-1.0)
            messages: Optional pre-formatted messages list
            
        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        try:
            if self.provider == "openai":
                return self._generate_openai_completion(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages
                )
            elif self.provider == "anthropic":
                return self._generate_anthropic_completion(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            else:
                return False, f"Unsupported AI provider: {self.provider}"
                
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            return False, str(e)
            
    def _generate_openai_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[bool, str]:
        """
        Generate completion using OpenAI API.
        
        Args:
            prompt: User prompt text
            system_prompt: System prompt to override default
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0.0-1.0)
            messages: Optional pre-formatted messages list
            
        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Use provided messages or create new ones
        if not messages:
            messages = []
            # Add system message if provided
            if system_prompt or self.system_prompt:
                messages.append({"role": "system", "content": system_prompt or self.system_prompt})
            # Add user message
            messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        def call_api():
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            # OpenAI returns choices[0].message.content
            return result["choices"][0]["message"]["content"].strip()
            
        try:
            completion = retry_operation(call_api, operation_name="AIAdapter.openai_completion")
            return True, completion
        except Exception as e:
            logger.error(format_error("ai", "Failed to get OpenAI response", e))
            return False, str(e)
            
    def _generate_anthropic_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Tuple[bool, str]:
        """
        Generate completion using Anthropic API.
        
        Args:
            prompt: User prompt text
            system_prompt: System prompt to override default
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0.0-1.0)
            
        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        url = f"{self.api_base}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Create Anthropic-style request
        data = {
            "model": self.model,
            "system": system_prompt or self.system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        def call_api():
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            # Anthropic returns content from the assistant's message
            return result["content"][0]["text"]
            
        try:
            completion = retry_operation(call_api, operation_name="AIAdapter.anthropic_completion")
            return True, completion
        except Exception as e:
            logger.error(format_error("ai", "Failed to get Anthropic response", e))
            return False, str(e)
            
    def generate_structured_completion(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None,
        structured_content: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
        context_window: Optional[int] = None,
        selected_pages: Optional[List[Union[int, str]]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Tuple[bool, str]:
        """
        Process a text query with document context and return an AI response.
        
        Args:
            query_text: The user's query
            context: Additional context as a dictionary
            structured_content: Structured document content
            context_window: Number of most recent pages to include
            selected_pages: Specific pages to include as context
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling (0.0-1.0)
            
        Returns:
            Tuple of (success: bool, completion_or_error: str)
        """
        # Build system prompt with context
        system_prompt = self._build_system_prompt_with_context(
            context=context,
            structured_content=structured_content,
            context_window=context_window,
            selected_pages=selected_pages
        )
        
        # Generate completion with the enhanced system prompt
        return self.generate_completion(
            prompt=query_text,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def _build_system_prompt_with_context(
        self,
        context: Optional[Dict[str, Any]] = None,
        structured_content: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
        context_window: Optional[int] = None,
        selected_pages: Optional[List[Union[int, str]]] = None
    ) -> str:
        """
        Build a system prompt that includes document context.
        
        Args:
            context: Dictionary of context variables
            structured_content: Document content as structured data
            context_window: Number of recent pages to include
            selected_pages: Specific pages to include
            
        Returns:
            Enhanced system prompt with context
        """
        if structured_content:
            context_snippets = []
            pages = []
            
            # Extract pages from structured_content
            if isinstance(structured_content, dict):
                pages = structured_content.get("pages", [])
            elif isinstance(structured_content, list):
                pages = structured_content
                
            # Filter pages based on selection criteria
            if selected_pages:
                filtered = [
                    p for p in pages 
                    if (p.get("id") in selected_pages or p.get("number") in selected_pages)
                ]
            elif context_window:
                filtered = pages[-context_window:]
            else:
                filtered = pages
                
            # Format each page's content
            for page in filtered:
                title = page.get("title", f"Page {page.get('number', '')}")
                content = page.get("content", "")
                links = page.get("links", [])
                
                # Format links if present
                link_str = ""
                if links:
                    link_str = "Links: " + ", ".join([
                        f"{link.get('label', link.get('target', ''))} (to page {link.get('target', '')})"
                        for link in links
                    ])
                    
                context_snippets.append(f"{title}:\n{content}\n{link_str}".strip())
                
            # Create system prompt with document context
            return "Relevant document context:\n" + "\n\n".join(context_snippets)
            
        elif context:
            # Format context dictionary
            context_str = ", ".join([f"{k}: {v}" for k, v in context.items() if v])
            return f"Document context: {context_str}"
            
        else:
            # Use default system prompt
            return self.system_prompt