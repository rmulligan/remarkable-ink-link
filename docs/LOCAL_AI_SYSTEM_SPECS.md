# Local AI System Specifications Report
*Generated: January 2025*

## System Overview

This report provides detailed specifications of the current system for evaluating local AI additions to the InkLink project.

### Host Information
- **Hostname**: ai-lab
- **Operating System**: Ubuntu 24.04.2 LTS
- **Kernel**: Linux 6.8.0-59-generic #61-Ubuntu SMP PREEMPT_DYNAMIC (x86_64)

## Hardware Specifications

### CPU
- **Model**: AMD Ryzen 7 5800X3D 8-Core Processor
- **Architecture**: x86_64
- **Cores**: 8 physical cores
- **Threads**: 16 threads (2 per core, SMT enabled)
- **Base Frequency**: ~3.4 GHz
- **Max Frequency**: 4.55 GHz
- **CPU Scaling**: Currently at 81%
- **BogoMIPS**: 6786.83

### Memory
- **Total RAM**: 62 GiB (64 GB)
- **Available Memory**: ~53 GiB free
- **Swap**: 2.0 GiB
- **Memory Usage**: ~8.8 GiB currently used

### GPU
- **Model**: NVIDIA GeForce RTX 4090
- **VRAM**: 24 GiB (24,564 MiB)
- **Driver Version**: 535.230.02
- **Compute Capability**: 8.9 (Ada Lovelace architecture)

### Storage
- **Primary Drive**: NVMe SSD (1.8 TB total)
- **Available Space**: 1004 GB free (43% used)
- **Filesystem**: /dev/nvme0n1p2

## Software Environment

### Base Software
- **Docker**: Version 28.1.1
- **Python**: 3.12.3
- **Network**: Ethernet connection (192.168.0.48/24)

### AI/ML Infrastructure
- **CUDA**: Not currently installed (nvcc not found)
- **PyTorch**: Not currently installed
- **Ollama**: Service is active and running (for local LLM inference)

## Recommendations for Local AI Implementation

### Strengths
1. **Powerful CPU**: The Ryzen 7 5800X3D with 16 threads is excellent for CPU-based inference
2. **High-end GPU**: RTX 4090 with 24GB VRAM can handle large language models (up to 70B parameters)
3. **Ample Memory**: 64GB RAM allows for loading large models and handling batches
4. **Fast Storage**: NVMe SSD ensures quick model loading
5. **Ollama Ready**: Service already installed for easy LLM deployment

### Current Limitations
1. **CUDA Not Installed**: Need to install CUDA toolkit for GPU acceleration
2. **No PyTorch**: Required for most modern AI/ML frameworks
3. **No Deep Learning Libraries**: Missing cudnn, TensorRT optimizations

### Recommended Setup for InkLink Local AI

#### 1. Essential Software Installation
```bash
# Install CUDA 12.1+ toolkit
wget https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda_12.1.0_530.30.02_linux.run
sudo sh cuda_12.1.0_530.30.02_linux.run

# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install Hugging Face Transformers
pip install transformers accelerate bitsandbytes
```

#### 2. Recommended Local Models

Given the RTX 4090's 24GB VRAM, these models are suitable:

**For General AI Tasks:**
- Llama 3.1 70B (4-bit quantized) via Ollama
- Mixtral 8x7B (full precision)
- CodeLlama 34B for code-specific tasks

**For Vision Tasks (handwriting recognition):**
- LLaVA 13B/34B models
- CogVLM for document understanding
- TrOCR for handwriting OCR

**For InkLink Specific Features:**
- Embedding models: all-MiniLM-L6-v2 for vector search
- Whisper Large V3 for potential audio transcription
- Stable Diffusion XL for image generation

#### 3. Ollama Configuration for InkLink

```bash
# Install recommended models
ollama pull llama3.1:70b-q4_K_M  # 4-bit quantized Llama for general tasks
ollama pull mixtral:8x7b         # For high-quality responses
ollama pull llava:34b            # For vision tasks

# Configure Ollama for InkLink
export OLLAMA_NUM_GPU=1
export OLLAMA_GPU_MEMORY=20G    # Leave some VRAM for other processes
```

#### 4. Python Configuration

Create a local AI service for InkLink:

```python
# src/inklink/services/local_ai_service.py
from transformers import pipeline
import torch
from ollama import Client

class LocalAIService:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.ollama_client = Client()
        
    def generate_text(self, prompt, model="llama3.1:70b-q4_K_M"):
        response = self.ollama_client.generate(
            model=model,
            prompt=prompt,
            stream=False
        )
        return response['response']
    
    def process_vision(self, image_path, prompt):
        response = self.ollama_client.generate(
            model="llava:34b",
            prompt=prompt,
            images=[image_path]
        )
        return response['response']
```

### Performance Expectations

With this hardware configuration:

1. **Inference Speed**: 
   - 70B models (4-bit): ~15-25 tokens/second
   - 34B models: ~30-50 tokens/second
   - 7B models: ~100+ tokens/second

2. **Batch Processing**: Can handle 10-20 concurrent requests for smaller models

3. **Vision Processing**: Real-time handwriting recognition with LLaVA models

4. **Memory Usage**: 
   - 70B 4-bit model: ~35GB VRAM
   - 34B model: ~20GB VRAM
   - Leaves headroom for other processes

### Integration with InkLink

1. **Handwriting Recognition**: Replace/supplement Claude Vision with local LLaVA
2. **Knowledge Graph**: Use local embeddings for entity extraction
3. **AI Responses**: Generate responses locally instead of API calls
4. **Cost Reduction**: Eliminate API costs for AI services
5. **Privacy**: Keep all data processing local

## Next Steps

1. Install CUDA toolkit and PyTorch
2. Set up Ollama with recommended models
3. Create LocalAIService adapter
4. Add configuration options to switch between cloud/local
5. Benchmark performance vs cloud solutions
6. Implement graceful fallback to cloud if local fails

This system is exceptionally well-suited for running local AI models for the InkLink project, requiring only software installation to unlock its full potential.