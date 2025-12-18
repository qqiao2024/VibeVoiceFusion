# Audio Denoising Tools

This directory contains two audio denoising scripts using state-of-the-art deep learning models.

## Quick Comparison

| Feature | SpeechBrain SepFormer | DeepFilterNet3 |
|---------|----------------------|----------------|
| **Best For** | Source separation, general audio | **Speech enhancement** |
| **Quality** | Good | **Excellent** |
| **Speed** | Slower | **Real-time capable** |
| **Sample Rate** | 16kHz | 48kHz |
| **Recognition** | Research model | **ICASSP 2022 DNS Challenge Winner** |

**Recommendation**: Use **DeepFilterNet** for speech denoising tasks.

---

## 1. DeepFilterNet (Recommended)

**File**: `audio_denoise_deepfilter.py`

DeepFilterNet is the state-of-the-art model for real-time speech enhancement, winner of the ICASSP 2022 DNS Challenge.

### Installation

```bash
# CPU only
pip install deepfilternet

# With CUDA support
pip install deepfilternet[cuda]
```

### Basic Usage

```bash
# Simple denoising
python audio_denoise_deepfilter.py -i noisy_audio.wav -o clean_audio.wav

# With verbose output
python audio_denoise_deepfilter.py -i noisy_audio.wav -o clean_audio.wav -v
```

### Controlling Noise Reduction Strength

Use `--atten-lim` to control how aggressively noise is removed (in dB):

```bash
# Gentle denoising (preserves natural sound)
python audio_denoise_deepfilter.py -i noisy.wav -o clean.wav --atten-lim 15

# Moderate denoising (balanced)
python audio_denoise_deepfilter.py -i noisy.wav -o clean.wav --atten-lim 40

# Aggressive denoising (maximum noise removal)
python audio_denoise_deepfilter.py -i noisy.wav -o clean.wav --atten-lim 80
```

### Model Versions

```bash
# DeepFilterNet3 (default) - Best quality
python audio_denoise_deepfilter.py -i noisy.wav -o clean.wav --model DeepFilterNet3

# DeepFilterNet2 - Good balance of speed and quality
python audio_denoise_deepfilter.py -i noisy.wav -o clean.wav --model DeepFilterNet2

# DeepFilterNet - Fastest
python audio_denoise_deepfilter.py -i noisy.wav -o clean.wav --model DeepFilterNet
```

### Batch Processing

Process all audio files in a directory:

```bash
python audio_denoise_deepfilter.py -i ./noisy_folder/ -o ./clean_folder/
```

### All Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `-i, --input` | Required | Input audio file or directory |
| `-o, --output` | Required | Output audio file or directory |
| `--device` | `auto` | Device: `auto`, `cpu`, or `cuda` |
| `--model` | `DeepFilterNet3` | Model version |
| `--atten-lim` | ~40 | Noise attenuation limit in dB (0-100) |
| `--no-post-filter` | False | Disable post-filtering |
| `--compensate-delay` | False | Compensate algorithmic delay |
| `--keep-original-sr` | False | Resample output to original sample rate |
| `--no-normalize` | False | Disable output normalization |
| `-v, --verbose` | False | Enable verbose output |

---

## 2. SpeechBrain SepFormer

**File**: `audio_denose.py`

SpeechBrain's SepFormer model, originally designed for source separation, can also be used for speech enhancement.

### Installation

```bash
pip install speechbrain
```

### Basic Usage

```bash
# Simple denoising
python audio_denose.py -i noisy_audio.wav -o clean_audio.wav

# With GPU
python audio_denose.py -i noisy_audio.wav -o clean_audio.wav --device cuda

# With verbose output
python audio_denose.py -i noisy_audio.wav -o clean_audio.wav -v
```

### Handling Sample Rate

The model expects 16kHz audio. Use `--resample` for other sample rates:

```bash
# Auto-resample input to 16kHz
python audio_denose.py -i noisy_audio.wav -o clean_audio.wav --resample

# Resample back to original sample rate in output
python audio_denose.py -i noisy_audio.wav -o clean_audio.wav --resample --keep-original-sr
```

### Custom Model Cache

```bash
# Save model to specific directory
python audio_denose.py -i noisy.wav -o clean.wav --savedir ./models/sepformer
```

### All Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `-i, --input` | Required | Input audio file path |
| `-o, --output` | Required | Output audio file path |
| `--device` | `auto` | Device: `auto`, `cpu`, or `cuda` |
| `--model` | `speechbrain/sepformer-wham16k-enhancement` | HuggingFace model ID |
| `--savedir` | None | Directory to cache the model |
| `--resample` | False | Auto-resample to 16kHz |
| `--keep-original-sr` | False | Resample output to original sample rate |
| `--no-normalize` | False | Disable output normalization |
| `-v, --verbose` | False | Enable verbose output |

---

## Supported Audio Formats

Both scripts support common audio formats:
- WAV (recommended)
- MP3
- FLAC
- OGG
- M4A
- AAC

---

## Examples

### Example 1: Clean up a podcast recording

```bash
# Use DeepFilterNet with moderate noise reduction
python audio_denoise_deepfilter.py \
    -i podcast_raw.wav \
    -o podcast_clean.wav \
    --atten-lim 30 \
    -v
```

### Example 2: Remove background noise from voice recording

```bash
# Aggressive denoising for very noisy environment
python audio_denoise_deepfilter.py \
    -i voice_noisy.wav \
    -o voice_clean.wav \
    --atten-lim 60
```

### Example 3: Batch process interview recordings

```bash
# Process all files in a directory
python audio_denoise_deepfilter.py \
    -i ./raw_interviews/ \
    -o ./clean_interviews/ \
    --device cuda \
    -v
```

### Example 4: Gentle enhancement preserving natural sound

```bash
# Minimal processing, just reduce obvious noise
python audio_denoise_deepfilter.py \
    -i meeting.wav \
    -o meeting_enhanced.wav \
    --atten-lim 12 \
    --no-post-filter
```

---

## Troubleshooting

### CUDA Out of Memory

If you run out of GPU memory, use CPU:
```bash
python audio_denoise_deepfilter.py -i input.wav -o output.wav --device cpu
```

### Audio Sounds Unnatural

Try reducing the attenuation limit:
```bash
python audio_denoise_deepfilter.py -i input.wav -o output.wav --atten-lim 15
```

Or disable post-filtering:
```bash
python audio_denoise_deepfilter.py -i input.wav -o output.wav --no-post-filter
```

### Sample Rate Mismatch (SpeechBrain)

If you see a warning about sample rate, use the resample flag:
```bash
python audio_denose.py -i input.wav -o output.wav --resample
```

---

## References

- **DeepFilterNet**: [GitHub](https://github.com/Rikorose/DeepFilterNet) | [Paper](https://arxiv.org/abs/2305.08227)
- **SpeechBrain SepFormer**: [HuggingFace](https://huggingface.co/speechbrain/sepformer-wham16k-enhancement) | [Paper](https://arxiv.org/abs/2010.13154)
