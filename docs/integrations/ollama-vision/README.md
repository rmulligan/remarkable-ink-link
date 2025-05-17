# Ollama Vision Integration

This directory contains documentation for InkLink's Ollama vision model integration, which enables local handwriting recognition using state-of-the-art vision-language models.

## Contents

- [Overview](overview.md) - Introduction and configuration guide
- Implementation details (coming soon)
- Performance benchmarks (coming soon)

## Quick Start

1. Install Ollama and pull a vision model:
   ```bash
   ollama pull qwen2.5vl:32b-q4_K_M
   ```

2. Set the handwriting backend:
   ```bash
   export HANDWRITING_BACKEND=ollama_vision
   ```

3. Run a test:
   ```bash
   python scripts/test_ollama_vision.py path/to/handwriting.png
   ```

## Model Recommendations

Based on extensive testing with RTX 4090:

| Model | Size | VRAM | Accuracy | Speed |
|-------|------|------|----------|-------|
| Qwen 2.5 VL | 32B | 21GB | Excellent | Good |
| MiniCPM-V 2.6 | 8B | 5-16GB | Very Good | Fast |
| Llama 3.2 Vision | 11B | ~12GB | Good | Good |

## See Also

- [InkLink Documentation](../../README.md)
- [Handwriting Recognition Guide](../../guides/handwriting_recognition.md)
- [Model Comparison Study](../../Local Vision model comparison .pdf)