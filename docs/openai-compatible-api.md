# OpenAI-Compatible TTS API Design Document

## Overview

This document describes the design of an OpenAI-compatible Text-to-Speech API endpoint for VibeVoice, allowing existing OpenAI TTS clients and SDKs to use VibeVoice as a drop-in replacement.

## API Comparison: OpenAI TTS vs VibeVoice

### Architecture Difference

```
OpenAI TTS (Synchronous):
  Client → POST /v1/audio/speech (JSON) → Binary audio response

VibeVoice Quick Generate (Asynchronous):
  Client → POST /api/v1/quick-generate (multipart) → JSON {request_id}
  Client → GET  /api/v1/quick-generate/{id} (poll) → JSON {status}
  Client → GET  /api/v1/quick-generate/{id}/download → Binary audio

VibeVoice OpenAI-Compat (Synchronous wrapper):
  Client → POST /v1/audio/speech (JSON) → [blocks until done] → Binary audio
```

### Parameter Comparison

| OpenAI Parameter | Type | VibeVoice Equivalent | Notes |
|-----------------|------|---------------------|-------|
| `model` | string (required) | `model_dtype` | `tts-1`→bf16, `tts-1-hd`→float8 |
| `input` | string (required) | `text` | Max 4096 chars in OpenAI, no limit in VibeVoice |
| `voice` | string (required) | Preset voice name | OpenAI has fixed set; VibeVoice uses preset voices |
| `response_format` | string | N/A (wav only) | Need conversion for mp3/flac |
| `speed` | number | N/A | Not supported by VibeVoice engine |
| `instructions` | string | N/A | GPT-4o-mini-tts only, not applicable |
| N/A | | `seeds` | VibeVoice-specific: random seed |
| N/A | | `cfg_scale` | VibeVoice-specific: classifier-free guidance |
| N/A | | `batch_size` | VibeVoice-specific: multi-generation |
| N/A | | `offloading` | VibeVoice-specific: VRAM optimization |
| N/A | | `voice_file` (upload) | VibeVoice supports custom voice upload |

### Voice Mapping

OpenAI provides fixed voice names (`alloy`, `echo`, `coral`, etc.). VibeVoice uses **preset voices** with names like `Alice`, `Bowen`, etc.

**Strategy**: Map the `voice` parameter to VibeVoice preset voice names (case-insensitive).

```
voice: "Alice"  →  Finds preset voice named "Alice"  →  Uses its .wav file
voice: "Bowen"  →  Finds preset voice named "Bowen"  →  Uses its .wav file
```

### Model Mapping

| OpenAI-compat Name | VibeVoice model_dtype | Description |
|-------------------|----------------------|-------------|
| `vibevoice-7b` | `bf16` | Standard quality (recommended) |
| `vibevoice-7b-hd` | `float8_e4m3fn` | Higher precision |
| `tts-1` | `bf16` | OpenAI alias for compatibility |
| `tts-1-hd` | `float8_e4m3fn` | OpenAI alias for compatibility |

### Response Format

| Format | OpenAI | VibeVoice Compat | Notes |
|--------|--------|-----------------|-------|
| `mp3` | Default | Supported (via ffmpeg) | Requires ffmpeg |
| `wav` | Supported | Native output | No conversion needed |
| `flac` | Supported | Supported (via soundfile) | |
| `opus` | Supported | Not supported | Return 400 |
| `aac` | Supported | Not supported | Return 400 |
| `pcm` | Supported | Not supported | Return 400 |

### Error Format

OpenAI error format:
```json
{
  "error": {
    "message": "Description of what went wrong",
    "type": "invalid_request_error",
    "code": "specific_error_code"
  }
}
```

### Key Behavioral Differences

1. **Latency**: OpenAI TTS responds in ~1-3 seconds. VibeVoice generation takes 10-60+ seconds depending on text length and hardware. Clients should expect longer response times.

2. **Concurrency**: OpenAI handles concurrent requests. VibeVoice has a single-thread GPU task queue — only one generation runs at a time. Concurrent requests get 503.

3. **Streaming**: OpenAI supports chunked transfer encoding for real-time streaming. VibeVoice does not support streaming — the full audio is returned after generation completes.

4. **Voice cloning**: VibeVoice's unique advantage is voice cloning from audio samples. The OpenAI-compat API uses preset voices, but the native Quick Generate API supports custom voice upload.

5. **Multi-speaker**: VibeVoice supports multi-speaker dialogue in a single request. The OpenAI-compat API only exposes single-speaker narration mode.

## VibeVoice Extension Parameters

The API accepts additional VibeVoice-specific parameters that OpenAI clients will simply ignore:

```json
{
  "model": "vibevoice-7b",
  "input": "Hello world",
  "voice": "Alice",
  "response_format": "wav",

  // VibeVoice extensions (optional)
  "seeds": 42,
  "cfg_scale": 1.3,
  "offloading": "balanced"
}
```

## Usage Examples

### curl
```bash
curl http://localhost:9527/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "vibevoice-7b",
    "input": "Hello, this is VibeVoice speaking.",
    "voice": "Alice"
  }' \
  --output speech.wav
```

### OpenAI Python SDK
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9527/v1",
    api_key="unused"  # Required by SDK but not validated
)

response = client.audio.speech.create(
    model="vibevoice-7b",
    voice="Alice",
    input="Hello, this is VibeVoice speaking."
)

response.stream_to_file("output.wav")
```

### OpenAI Node.js SDK
```javascript
import OpenAI from "openai";

const client = new OpenAI({
    baseURL: "http://localhost:9527/v1",
    apiKey: "unused"
});

const response = await client.audio.speech.create({
    model: "vibevoice-7b",
    voice: "Alice",
    input: "Hello, this is VibeVoice speaking."
});

const buffer = Buffer.from(await response.arrayBuffer());
await fs.promises.writeFile("output.wav", buffer);
```

## Limitations

- No streaming support (full audio returned after generation)
- Single concurrent request (503 if queue busy)
- Higher latency than OpenAI (~10-60s vs ~1-3s)
- Limited output formats (wav, mp3, flac only)
- Speed parameter accepted but ignored
- Instructions parameter not supported
- No billing/usage tracking
