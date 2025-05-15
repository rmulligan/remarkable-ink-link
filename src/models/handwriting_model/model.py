"""
Handwriting Recognition Transformer Model

This module implements a transformer-based model for online handwriting recognition
that works directly with stroke data extracted from reMarkable files.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from einops import rearrange, repeat
from typing import List, Dict, Any, Optional, Tuple

# Define special tokens
PAD_TOKEN = 0  # Padding token
SOS_TOKEN = 1  # Start of sequence token
EOS_TOKEN = 2  # End of sequence token

class PositionalEncoding(nn.Module):
    """
    Positional encoding for transformer model
    """
    def __init__(self, d_model: int, max_seq_length: int = 2000):
        super(PositionalEncoding, self).__init__()
        
        # Create positional encoding matrix
        pe = torch.zeros(max_seq_length, d_model)
        position = torch.arange(0, max_seq_length, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-torch.log(torch.tensor(10000.0)) / d_model))
        
        # Apply sine to even indices
        pe[:, 0::2] = torch.sin(position * div_term)
        # Apply cosine to odd indices
        pe[:, 1::2] = torch.cos(position * div_term)
        
        # Register as buffer (not a parameter)
        self.register_buffer('pe', pe.unsqueeze(0))
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Add positional encoding to input tensor
        
        Args:
            x: Input tensor of shape [batch_size, seq_length, d_model]
            
        Returns:
            Tensor with positional encoding added
        """
        return x + self.pe[:, :x.size(1)]

class StrokeEmbedding(nn.Module):
    """
    Embedding layer for stroke points
    """
    def __init__(self, d_model: int = 256):
        super(StrokeEmbedding, self).__init__()
        
        # Five features: (x, y, pressure, dx, dy) per point
        self.point_projection = nn.Linear(5, d_model)
        self.norm = nn.LayerNorm(d_model)
        
    def forward(self, strokes: torch.Tensor) -> torch.Tensor:
        """
        Project stroke points to embedding space
        
        Args:
            strokes: Tensor of shape [batch_size, seq_length, 5] containing
                     (x, y, pressure, dx, dy) for each point
                     
        Returns:
            Embedded tensor of shape [batch_size, seq_length, d_model]
        """
        # Project each point to the embedding dimension
        embedded = self.point_projection(strokes)
        # Apply layer normalization
        embedded = self.norm(embedded)
        
        return embedded

class HandwritingTransformer(nn.Module):
    """
    Transformer model for handwriting recognition
    """
    def __init__(
        self,
        vocab_size: int,
        d_model: int = 256,
        nhead: int = 8,
        num_encoder_layers: int = 6,
        num_decoder_layers: int = 6,
        dim_feedforward: int = 2048,
        dropout: float = 0.1,
        max_seq_length: int = 2000
    ):
        super(HandwritingTransformer, self).__init__()
        
        # Store parameters
        self.d_model = d_model
        self.vocab_size = vocab_size
        
        # Stroke embedding
        self.stroke_embedding = StrokeEmbedding(d_model)
        
        # Positional encoding
        self.positional_encoding = PositionalEncoding(d_model, max_seq_length)
        
        # Token embedding for decoder
        self.token_embedding = nn.Embedding(vocab_size, d_model)
        
        # Transformer
        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        
        # Output projection
        self.output_projection = nn.Linear(d_model, vocab_size)
        
    def create_padding_mask(self, seq: torch.Tensor, padding_value: int = 0) -> torch.Tensor:
        """
        Create padding mask for transformer
        
        Args:
            seq: Input sequence
            padding_value: Value used for padding
            
        Returns:
            Boolean mask where True values indicate padding positions
        """
        # For stroke data, we identify padding by checking if all values are 0
        if seq.dim() > 2 and seq.shape[-1] > 1:  # For stroke points (x, y, pressure, etc.)
            mask = torch.sum(torch.abs(seq), dim=-1) == 0
        else:  # For token IDs
            mask = seq == padding_value
            
        return mask
    
    def encode_strokes(
        self, 
        strokes: torch.Tensor, 
        stroke_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Encode stroke data
        
        Args:
            strokes: Tensor of shape [batch_size, seq_length, 5]
            stroke_mask: Optional mask for strokes
            
        Returns:
            Encoded representation of strokes
        """
        # Embed strokes
        embedded = self.stroke_embedding(strokes)
        
        # Add positional encoding
        embedded = self.positional_encoding(embedded)
        
        # If no mask provided, create one based on padding
        if stroke_mask is None:
            stroke_mask = self.create_padding_mask(strokes)
            
        # Create transformer src_key_padding_mask
        src_key_padding_mask = stroke_mask
        
        # Pass through encoder
        memory = self.transformer.encoder(
            embedded, 
            src_key_padding_mask=src_key_padding_mask
        )
        
        return memory
    
    def decode(
        self,
        memory: torch.Tensor,
        targets: torch.Tensor,
        memory_mask: Optional[torch.Tensor] = None,
        target_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Decode encoded stroke data to text
        
        Args:
            memory: Encoded stroke data from encoder
            targets: Target token IDs
            memory_mask: Mask for memory
            target_mask: Mask for targets
            
        Returns:
            Logits for next token predictions
        """
        # Create causal mask for decoder
        tgt_len = targets.size(1)
        causal_mask = self.transformer.generate_square_subsequent_mask(tgt_len).to(targets.device)
        
        # If no target mask provided, create one based on padding
        if target_mask is None:
            target_mask = self.create_padding_mask(targets)
            
        # If no memory mask provided, create zeros (no mask)
        if memory_mask is None:
            memory_mask = torch.zeros((memory.size(0), memory.size(1)), dtype=torch.bool, device=memory.device)
            
        # Embed target tokens
        embedded_targets = self.token_embedding(targets) * (self.d_model ** 0.5)
        
        # Add positional encoding
        embedded_targets = self.positional_encoding(embedded_targets)
        
        # Pass through decoder
        output = self.transformer.decoder(
            embedded_targets,
            memory,
            tgt_mask=causal_mask,
            tgt_key_padding_mask=target_mask,
            memory_key_padding_mask=memory_mask
        )
        
        # Project to vocabulary
        logits = self.output_projection(output)
        
        return logits
    
    def forward(
        self,
        strokes: torch.Tensor,
        targets: torch.Tensor,
        stroke_mask: Optional[torch.Tensor] = None,
        target_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass of the model
        
        Args:
            strokes: Stroke data [batch_size, seq_length, 5]
            targets: Target token IDs [batch_size, seq_length]
            stroke_mask: Optional mask for strokes
            target_mask: Optional mask for targets
            
        Returns:
            Logits for next token predictions
        """
        # Encode strokes
        memory = self.encode_strokes(strokes, stroke_mask)
        
        # Decode to get logits
        logits = self.decode(memory, targets, stroke_mask, target_mask)
        
        return logits
    
    @torch.no_grad()
    def generate(
        self,
        strokes: torch.Tensor,
        max_length: int = 100,
        temperature: float = 1.0
    ) -> Tuple[List[int], torch.Tensor]:
        """
        Generate text from stroke data
        
        Args:
            strokes: Stroke data [1, seq_length, 5]
            max_length: Maximum length of generated sequence
            temperature: Sampling temperature (higher = more random)
            
        Returns:
            Tuple of (token IDs, probabilities)
        """
        self.eval()
        
        # Ensure batch dimension
        if strokes.dim() == 2:
            strokes = strokes.unsqueeze(0)
            
        # Encode strokes
        memory = self.encode_strokes(strokes)
        
        # Start with SOS token
        current_output = torch.tensor([[SOS_TOKEN]], device=strokes.device)
        
        # Store predictions and probabilities
        predictions = [SOS_TOKEN]
        probabilities = []
        
        # Generate tokens one by one
        for _ in range(max_length):
            # Get logits for next token
            logits = self.decode(memory, current_output)
            
            # Get logits for the last token
            next_token_logits = logits[:, -1, :] / temperature
            
            # Apply softmax to get probabilities
            probs = F.softmax(next_token_logits, dim=-1)
            
            # Sample next token
            next_token = torch.multinomial(probs, 1)
            
            # Store prediction and probability
            token_id = next_token.item()
            predictions.append(token_id)
            probabilities.append(probs[0, token_id].item())
            
            # Stop if EOS token is generated
            if token_id == EOS_TOKEN:
                break
                
            # Add new token to current output
            current_output = torch.cat([current_output, next_token], dim=1)
        
        return predictions, torch.tensor(probabilities)


class HandwritingRecognitionSystem:
    """
    Complete system for handwriting recognition
    """
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        max_seq_length: int = 2000,
        vocab_size: int = 128  # ASCII characters by default
    ):
        self.device = device
        self.max_seq_length = max_seq_length
        
        # Create character mapping (default to ASCII)
        self.idx2char = {i: chr(i) for i in range(32, 127)}
        # Add special tokens
        self.idx2char[PAD_TOKEN] = "[PAD]"
        self.idx2char[SOS_TOKEN] = "[SOS]"
        self.idx2char[EOS_TOKEN] = "[EOS]"
        
        # Create reverse mapping
        self.char2idx = {v: k for k, v in self.idx2char.items()}
        
        # Initialize model
        self.model = HandwritingTransformer(
            vocab_size=vocab_size,
            d_model=256,
            nhead=8,
            num_encoder_layers=6,
            num_decoder_layers=6
        ).to(device)
        
        # Load pretrained model if path provided
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """
        Load pretrained model from path
        
        Args:
            model_path: Path to model checkpoint
        """
        checkpoint = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        print(f"Loaded model from {model_path}")
    
    def preprocess_strokes(self, strokes: List[Dict[str, Any]]) -> torch.Tensor:
        """
        Preprocess stroke data to model input format
        
        Args:
            strokes: List of stroke dictionaries from reMarkable
            
        Returns:
            Tensor of shape [1, seq_length, 5] containing
            (x, y, pressure, dx, dy) for each point
        """
        points = []
        
        # Process each stroke
        for stroke in strokes:
            x_points = stroke.get('x', [])
            y_points = stroke.get('y', [])
            pressures = stroke.get('p', [])
            
            # Ensure all arrays have the same length
            min_len = min(len(x_points), len(y_points), len(pressures))
            
            # Process points in the stroke
            for i in range(min_len):
                x = x_points[i]
                y = y_points[i]
                p = pressures[i]
                
                # Calculate deltas (set to 0 for first point)
                dx = 0 if i == 0 else x - x_points[i-1]
                dy = 0 if i == 0 else y - y_points[i-1]
                
                # Add point features
                points.append([x, y, p, dx, dy])
        
        # Convert to tensor
        if not points:
            return torch.zeros((1, 1, 5), device=self.device)
        
        # Create tensor and normalize
        stroke_tensor = torch.tensor(points, dtype=torch.float32, device=self.device)
        
        # Normalize coordinates and pressures to [0, 1] range
        stroke_tensor[:, 0] /= 1404.0  # reMarkable width
        stroke_tensor[:, 1] /= 1872.0  # reMarkable height
        # Pressure should already be in [0, 1]
        
        # Normalize deltas based on their typical range
        max_delta = 20.0
        stroke_tensor[:, 3] = torch.clamp(stroke_tensor[:, 3] / max_delta, -1.0, 1.0)
        stroke_tensor[:, 4] = torch.clamp(stroke_tensor[:, 4] / max_delta, -1.0, 1.0)
        
        # Add batch dimension
        stroke_tensor = stroke_tensor.unsqueeze(0)
        
        # Pad or truncate sequence
        if stroke_tensor.size(1) > self.max_seq_length:
            stroke_tensor = stroke_tensor[:, :self.max_seq_length, :]
        elif stroke_tensor.size(1) < self.max_seq_length:
            padding = torch.zeros(
                (1, self.max_seq_length - stroke_tensor.size(1), 5),
                device=self.device
            )
            stroke_tensor = torch.cat([stroke_tensor, padding], dim=1)
            
        return stroke_tensor
    
    def tokens_to_text(self, tokens: List[int]) -> str:
        """
        Convert token IDs to text
        
        Args:
            tokens: List of token IDs
            
        Returns:
            Recognized text
        """
        # Convert tokens to characters, stopping at EOS token
        chars = []
        for token in tokens:
            if token == EOS_TOKEN:
                break
            if token == SOS_TOKEN:
                continue
            if token in self.idx2char:
                chars.append(self.idx2char[token])
                
        return ''.join(chars)
    
    def recognize(self, strokes: List[Dict[str, Any]]) -> Tuple[str, float]:
        """
        Recognize text from stroke data
        
        Args:
            strokes: List of stroke dictionaries from reMarkable
            
        Returns:
            Tuple of (recognized text, confidence score)
        """
        self.model.eval()
        
        # Preprocess strokes
        stroke_tensor = self.preprocess_strokes(strokes)
        
        # Generate text
        with torch.no_grad():
            predictions, probs = self.model.generate(stroke_tensor)
            
        # Convert to text
        text = self.tokens_to_text(predictions)
        
        # Calculate confidence as mean of token probabilities
        confidence = probs.mean().item() if len(probs) > 0 else 0.0
        
        return text, confidence


# Example usage
if __name__ == "__main__":
    import json
    import sys
    
    # Check if a stroke file is provided
    if len(sys.argv) > 1:
        stroke_file = sys.argv[1]
        
        # Load strokes from file
        with open(stroke_file, 'r') as f:
            strokes = json.load(f)
            
        # Initialize recognition system
        recognizer = HandwritingRecognitionSystem()
        
        # Recognize text
        text, confidence = recognizer.recognize(strokes)
        
        print(f"Recognized text: {text}")
        print(f"Confidence: {confidence:.4f}")
    else:
        print("Usage: python model.py <stroke_file.json>")