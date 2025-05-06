"""Handwriting recognition service using MyScript iink SDK."""

from typing import List, Dict, Any, Optional
import os
import logging
import json
import hmac
import hashlib
import base64
import time
import requests
from urllib.parse import urljoin

# Import rmscene for .rm file parsing
import rmscene

from inklink.services.interfaces import IHandwritingRecognitionService
from inklink.utils import retry_operation, format_error
from inklink.config import CONFIG

logger = logging.getLogger(__name__)

class HandwritingRecognitionService(IHandwritingRecognitionService):
    """Service for handwriting recognition using MyScript iink SDK."""
    
    # MyScript iink SDK API endpoints
    IINK_BASE_URL = "https://cloud.myscript.com/api/v4.0/"
    RECOGNITION_ENDPOINT = "iink/recognition"
    EXPORT_ENDPOINT = "iink/export"
    
    def __init__(self, 
                 application_key: Optional[str] = None, 
                 hmac_key: Optional[str] = None):
        """Initialize the handwriting recognition service.
        
        Args:
            application_key: MyScript iink SDK Application Key
            hmac_key: MyScript iink SDK HMAC Key
        """
        # Get keys from arguments or environment variables
        self.application_key = application_key or os.environ.get("MYSCRIPT_APP_KEY") or CONFIG.get("MYSCRIPT_APP_KEY", "")
        self.hmac_key = hmac_key or os.environ.get("MYSCRIPT_HMAC_KEY") or CONFIG.get("MYSCRIPT_HMAC_KEY", "")
        
        # Verify keys are available
        if not self.application_key or not self.hmac_key:
            logger.warning("MyScript keys not provided; handwriting recognition not available")
    
    def initialize_iink_sdk(self, application_key: str, hmac_key: str) -> bool:
        """Initialize the MyScript iink SDK with authentication keys.
        
        Args:
            application_key: MyScript Application Key
            hmac_key: MyScript HMAC Key
            
        Returns:
            bool: True if initialization succeeded
        """
        try:
            self.application_key = application_key
            self.hmac_key = hmac_key
            
            # Validate keys by making a simple test request
            test_data = {
                "type": "configuration",
                "configuration": {"lang": "en_US"}
            }
            
            # Generate headers with authentication
            headers = self._generate_headers(test_data)
            
            # Make a test request to validate keys
            response = requests.post(
                urljoin(self.IINK_BASE_URL, "iink/configuration"),
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                logger.info("MyScript iink SDK initialized successfully")
                return True
            else:
                logger.error(f"Failed to initialize MyScript iink SDK: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing MyScript iink SDK: {e}")
            return False
    
    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """Extract strokes from a reMarkable file.
        
        Args:
            rm_file_path: Path to .rm file
            
        Returns:
            List of stroke dictionaries with x, y coordinates and pressure
        """
        try:
            # Use rmscene to parse the .rm file
            scene = rmscene.load(rm_file_path)
            
            strokes = []
            for layer in scene.layers:
                for line in layer.lines:
                    # Convert to iink-compatible format
                    stroke = {
                        "id": str(len(strokes)),
                        "x": [point.x for point in line.points],
                        "y": [point.y for point in line.points],
                        "pressure": [point.pressure for point in line.points],
                        "timestamp": int(time.time() * 1000)  # Current time in ms
                    }
                    strokes.append(stroke)
            
            logger.info(f"Extracted {len(strokes)} strokes from {rm_file_path}")
            return strokes
            
        except Exception as e:
            logger.error(f"Error extracting strokes from {rm_file_path}: {e}")
            return []
    
    def convert_to_iink_format(self, strokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert reMarkable strokes to iink SDK compatible format.
        
        Args:
            strokes: List of stroke dictionaries
            
        Returns:
            iink SDK compatible JSON structure
        """
        try:
            # Create the basic iink data structure
            iink_data = {
                "type": "inkData",
                "width": CONFIG.get("PAGE_WIDTH", 1872),
                "height": CONFIG.get("PAGE_HEIGHT", 2404),
                "strokes": strokes
            }
            
            return iink_data
            
        except Exception as e:
            logger.error(f"Error converting strokes to iink format: {e}")
            return {"type": "inkData", "strokes": []}
    
    def recognize_handwriting(self, iink_data: Dict[str, Any], content_type: str = "Text", language: str = "en_US") -> Dict[str, Any]:
        """Process ink data through the iink SDK and return recognition results.
        
        Args:
            iink_data: Stroke data in iink format
            content_type: Content type (Text, Diagram, Math, etc.)
            language: Language code
            
        Returns:
            Recognition result with content ID
        """
        try:
            if not self.application_key or not self.hmac_key:
                raise ValueError("MyScript keys not available; cannot recognize handwriting")
            
            # Prepare request data
            request_data = {
                "configuration": {
                    "lang": language,
                    "contentType": content_type,
                    "recognition": {
                        "text": {
                            "guides": {
                                "enable": False
                            },
                            "smartGuide": False
                        }
                    }
                },
                **iink_data
            }
            
            # Generate headers with authentication
            headers = self._generate_headers(request_data)
            
            # Send recognition request
            response = requests.post(
                urljoin(self.IINK_BASE_URL, self.RECOGNITION_ENDPOINT),
                json=request_data,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Recognition failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"Recognition failed: {response.text}"}
            
            result = response.json()
            logger.info(f"Recognition successful: {result.get('id')}")
            return {"success": True, "content_id": result.get("id"), "raw_result": result}
            
        except Exception as e:
            error_msg = format_error("recognition", "Handwriting recognition failed", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}
    
    def export_content(self, content_id: str, format_type: str = "text") -> Dict[str, Any]:
        """Export recognized content in the specified format.
        
        Args:
            content_id: Content ID from recognition result
            format_type: Export format (text, JIIX, etc.)
            
        Returns:
            Exported content
        """
        try:
            if not self.application_key or not self.hmac_key:
                raise ValueError("MyScript keys not available; cannot export content")
            
            # Prepare request data
            request_data = {
                "format": format_type
            }
            
            # Generate headers with authentication
            headers = self._generate_headers(request_data)
            
            # Send export request
            export_url = f"{urljoin(self.IINK_BASE_URL, self.EXPORT_ENDPOINT)}/{content_id}"
            response = requests.post(
                export_url,
                json=request_data,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Export failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"Export failed: {response.text}"}
            
            result = response.json()
            logger.info(f"Export successful: {format_type}")
            return {"success": True, "content": result}
            
        except Exception as e:
            error_msg = format_error("export", "Content export failed", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}
    
    def _generate_headers(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Generate headers with HMAC authentication for MyScript API.
        
        Args:
            data: Request payload
            
        Returns:
            Headers dictionary with authentication
        """
        # Convert data to JSON string
        data_json = json.dumps(data)
        
        # Generate timestamp in milliseconds
        timestamp = str(int(time.time() * 1000))
        
        # Create the message to sign: timestamp + data
        message = timestamp + data_json
        
        # Create HMAC-SHA512 signature
        signature_bytes = hmac.new(
            self.hmac_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha512
        ).digest()
        
        # Base64 encode the signature
        signature = base64.b64encode(signature_bytes).decode('utf-8')
        
        # Return headers
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'applicationKey': self.application_key,
            'hmacSignature': signature,
            'hmacTimestamp': timestamp
        }
