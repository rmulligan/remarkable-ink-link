# Ollama Vision Integration for InkLink

## Overview

InkLink now supports Ollama vision models for handwriting recognition, providing a powerful local alternative to cloud-based solutions. This integration leverages state-of-the-art vision-language models (VLMs) that can run entirely on your local machine.

## Supported Models

Based on the research document, the following models are recommended for handwriting recognition on NVIDIA RTX 4090:

1. **Qwen 2.5 VL (32B)** - Best overall performance
   - Model: `qwen2.5vl:32b-q4_K_M`
   - Excellent OCR/HTR accuracy
   - Requires ~21GB VRAM

2. **MiniCPM-V 2.6 (8B)** - Lightweight alternative
   - Model: `minicpm-v:8b-2.6-fp16`
   - Good performance in smaller footprint
   - Requires ~5-16GB VRAM

3. **Llama 3.2 Vision (11B)** - Balanced option
   - Model: `llama3.2-vision:11b`
   - ~80% accuracy on handwriting
   - Good for English documents

## Installation

1. Install Ollama:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. Pull a vision model:
   ```bash
   ollama pull qwen2.5vl:32b-q4_K_M
   ```

3. Verify the model is available:
   ```bash
   ollama list
   ```

## Configuration

Configure InkLink to use Ollama vision models by setting environment variables:

```bash
# Use Ollama as the handwriting recognition backend
export HANDWRITING_BACKEND=ollama_vision

# Specify the vision model (default: qwen2.5vl:32b-q4_K_M)
export OLLAMA_VISION_MODEL=qwen2.5vl:32b-q4_K_M

# Ollama API endpoint (default: http://localhost:11434)
export OLLAMA_BASE_URL=http://localhost:11434

# Timeout for model inference (default: 300 seconds)
export OLLAMA_TIMEOUT=300
```

Or use auto mode to try Ollama first with Claude as fallback:
```bash
export HANDWRITING_BACKEND=auto
```

## Usage

### Basic Handwriting Recognition

```python
from inklink.services.handwriting_recognition_service_v2 import (
    HandwritingRecognitionServiceV2,
    RecognitionBackend
)

# Initialize service with Ollama backend
service = HandwritingRecognitionServiceV2(
    backend=RecognitionBackend.OLLAMA_VISION
)

# Recognize handwriting from an image
text = await service.recognize_handwriting("path/to/handwriting.png")
print(text)
```

### Testing the Integration

Test the Ollama vision integration:
```bash
python scripts/test_ollama_vision.py path/to/handwriting/image.png
```

Compare different backends:
```bash
python scripts/test_handwriting_backends.py path/to/handwriting/image.png
```

## Performance Considerations

### VRAM Requirements
- RTX 4090 (24GB VRAM) can handle all recommended models
- Quantized models (Q4_K_M) reduce memory usage significantly
- Leave headroom for context processing

### Optimization Tips
1. Use lower temperature (0.3) for better OCR accuracy
2. Adjust max_tokens based on expected text length
3. Consider batch processing for multiple images
4. Use preprocessing for low-quality images

## Advantages over Cloud Solutions

1. **Privacy**: All data stays local
2. **Offline**: No internet connection required
3. **Cost**: No API fees or usage limits
4. **Speed**: Low latency, especially for batch processing
5. **Customization**: Can fine-tune models for specific use cases

## Troubleshooting

### Common Issues

1. **Model not found**:
   ```bash
   ollama pull qwen2.5vl:32b-q4_K_M
   ```

2. **Out of memory**:
   - Use smaller model or more aggressive quantization
   - Close other GPU applications
   - Consider MiniCPM-V for lower VRAM usage

3. **Slow inference**:
   - Ensure GPU acceleration is enabled
   - Check model quantization level
   - Reduce max_tokens if appropriate

## API Reference

See the `OllamaVisionAdapter` class for detailed API documentation:
- `query_vision()`: General vision model query
- `query_handwriting()`: Specialized handwriting recognition
- `stream_query_vision()`: Streaming responses
- `list_models()`: List available vision models