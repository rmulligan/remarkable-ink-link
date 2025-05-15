#!/usr/bin/env python3
"""
Handwriting Stroke Recognition Module

Uses third-party APIs or libraries to recognize handwriting from stroke data.
"""

import os
import json
import requests
import time
import tempfile
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

# Import our utility functions for stroke extraction
from preprocessing import extract_strokes_from_rm_file, normalize_strokes, save_strokes_to_json


class StrokeRecognizer:
    """
    Base class for stroke-based handwriting recognition.
    """
    
    def __init__(self):
        """Initialize the recognizer."""
        pass
    
    def recognize_strokes(self, strokes: List[Dict[str, Any]]) -> Tuple[str, float, List[Dict]]:
        """
        Recognize text from stroke data.
        
        Args:
            strokes: List of stroke dictionaries
            
        Returns:
            Tuple of (recognized text, confidence score, additional info)
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def recognize_from_file(self, rm_file_path: str) -> Tuple[str, float, List[Dict]]:
        """
        Recognize text from a reMarkable file.
        
        Args:
            rm_file_path: Path to .rm file
            
        Returns:
            Tuple of (recognized text, confidence score, additional info)
        """
        # Extract strokes
        strokes = extract_strokes_from_rm_file(rm_file_path)
        
        if not strokes:
            return "No strokes found", 0.0, []
        
        # Recognize text
        return self.recognize_strokes(strokes)


class OnlineRecognizer(StrokeRecognizer):
    """
    Recognizer that uses the MyScript API for handwriting recognition.
    Fallback option if other methods are not available.
    """
    
    # MyScript API endpoints
    API_URL = "https://cloud.myscript.com/api/v4.0/iink/batch"
    
    def __init__(self, app_key: str, hmac_key: str):
        """
        Initialize with MyScript API credentials.
        
        Args:
            app_key: MyScript application key
            hmac_key: MyScript HMAC key
        """
        super().__init__()
        self.app_key = app_key
        self.hmac_key = hmac_key
        
        if not app_key or not hmac_key:
            raise ValueError("MyScript API keys are required")
    
    def _generate_hmac(self, data: str) -> str:
        """
        Generate HMAC signature for request authentication.
        
        Args:
            data: Data to sign
            
        Returns:
            HMAC signature as base64 encoded string
        """
        import hmac
        import hashlib
        import base64
        
        h = hmac.new(
            bytes(self.hmac_key, "utf-8"),
            data.encode("utf-8"),
            hashlib.sha512
        )
        return base64.b64encode(h.digest()).decode("utf-8")
    
    def recognize_strokes(self, strokes: List[Dict[str, Any]]) -> Tuple[str, float, List[Dict]]:
        """
        Recognize text from stroke data using MyScript API.
        
        Args:
            strokes: List of stroke dictionaries
            
        Returns:
            Tuple of (recognized text, confidence score, additional info)
        """
        # Normalize strokes
        normalized_strokes = normalize_strokes(strokes)
        
        # Create request data in MyScript format
        current_time = int(time.time() * 1000)
        request_data = {
            "configuration": {
                "lang": "en_US",
                "text": {
                    "guides": {"enable": True},
                    "smartGuide": True,
                    "margin": {"top": 20, "left": 10, "right": 10}
                },
                "export": {
                    "jiix": {
                        "bounding-box": True,
                        "strokes": True,
                        "text": {
                            "chars": True,
                            "words": True
                        }
                    }
                }
            },
            "xDPI": 96,
            "yDPI": 96,
            "contentType": "Text",
            "strokeGroups": [
                {
                    "penStyle": "color: #000000;\n-myscript-pen-width: 1;",
                    "strokes": []
                }
            ],
            "height": 500,
            "width": 800,
            "conversionState": "DIGITAL_EDIT"
        }
        
        # Add strokes to request data
        for stroke in normalized_strokes:
            request_data["strokeGroups"][0]["strokes"].append({
                "x": stroke["x"],
                "y": stroke["y"],
                "t": stroke.get("t", [current_time + i * 10 for i in range(len(stroke["x"]))]),
                "p": stroke.get("p", [0.5] * len(stroke["x"])),
                "pointerType": "pen"
            })
        
        # Convert to JSON
        request_json = json.dumps(request_data)
        
        # Generate HMAC signature
        hmac_signature = self._generate_hmac(request_json)
        
        # Set up headers
        headers = {
            "Accept": "application/json,application/vnd.myscript.jiix",
            "Content-Type": "application/json",
            "applicationKey": self.app_key,
            "hmac": hmac_signature
        }
        
        # Send request
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                data=request_json,
                timeout=30  # Reasonable timeout for recognition
            )
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                text = result.get("result", "")
                
                # Extract additional info if available
                jiix = result.get("jiix", {})
                
                return text, 0.8, [jiix]  # Assuming 0.8 confidence for successful recognition
            else:
                error_msg = f"API Error: {response.status_code}"
                try:
                    error_details = response.json()
                    error_msg = f"{error_msg} - {json.dumps(error_details)}"
                except:
                    error_msg = f"{error_msg} - {response.text}"
                
                print(f"Recognition failed: {error_msg}")
                return "", 0.0, [{"error": error_msg}]
                
        except Exception as e:
            print(f"Error during API call: {e}")
            return "", 0.0, [{"error": str(e)}]


class OfflineRecognizer(StrokeRecognizer):
    """
    Offline handwriting recognizer using ML models.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize with optional model path.
        
        Args:
            model_path: Path to model file (if None, uses default)
        """
        super().__init__()
        self.model_path = model_path
        
        # Load model here if offline recognition is implemented
        print("Offline recognizer initialized")
    
    def recognize_strokes(self, strokes: List[Dict[str, Any]]) -> Tuple[str, float, List[Dict]]:
        """
        Recognize text from stroke data using offline model.
        
        Args:
            strokes: List of stroke dictionaries
            
        Returns:
            Tuple of (recognized text, confidence score, additional info)
        """
        # This is a placeholder - in a real system, we'd use the loaded model
        # For now, just return a placeholder
        return "Offline recognition not implemented", 0.0, []


def get_best_available_recognizer() -> StrokeRecognizer:
    """
    Get the best available recognizer based on system setup.
    
    Returns:
        StrokeRecognizer instance
    """
    # Check for MyScript API keys
    app_key = os.environ.get("MYSCRIPT_APP_KEY")
    hmac_key = os.environ.get("MYSCRIPT_HMAC_KEY")
    
    if app_key and hmac_key:
        print("Using MyScript online recognizer")
        return OnlineRecognizer(app_key, hmac_key)
    else:
        print("Using offline recognizer (limited functionality)")
        return OfflineRecognizer()


# Example usage
if __name__ == "__main__":
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Recognize handwriting from strokes")
    parser.add_argument("input", help="Path to .rm file or JSON stroke file")
    parser.add_argument("--app-key", help="MyScript application key")
    parser.add_argument("--hmac-key", help="MyScript HMAC key")
    parser.add_argument("--output", help="Output path for recognized text")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize recognizer
    if args.app_key and args.hmac_key:
        recognizer = OnlineRecognizer(args.app_key, args.hmac_key)
    else:
        recognizer = get_best_available_recognizer()
    
    # Process input file
    if args.input.endswith('.json'):
        # Load strokes from JSON
        with open(args.input, 'r') as f:
            strokes = json.load(f)
        
        # Recognize text
        text, confidence, info = recognizer.recognize_strokes(strokes)
    else:
        # Process .rm file
        text, confidence, info = recognizer.recognize_from_file(args.input)
    
    # Print results
    print(f"\nRecognized text: {text}")
    print(f"Confidence: {confidence:.4f}")
    
    # Save output if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(text)
        print(f"Saved recognized text to {args.output}")