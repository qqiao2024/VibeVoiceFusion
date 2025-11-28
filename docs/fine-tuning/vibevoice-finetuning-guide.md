# Comprehensive VibeVoice Fine-Tuning Guide

**Last Updated:** November 2025  
**Model Versions:** VibeVoice-1.5B, VibeVoice-7B  
**Based on:** vibevoice-community/VibeVoice implementation

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Understanding the Actual Components](#understanding-the-actual-components)
3. [Loss Functions](#loss-functions)
4. [Fine-tuning Strategy](#fine-tuning-strategy)
5. [Emotion Control Implementation](#emotion-control-implementation)
6. [Training Configuration](#training-configuration)
7. [Data Preparation](#data-preparation)
8. [Complete Implementation](#complete-implementation)
9. [Hardware Requirements](#hardware-requirements)
10. [Troubleshooting](#troubleshooting)

---

## 1. Architecture Overview

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                      VibeVoice Model                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────┐  ┌──────────────────────┐         │
│  │ Acoustic Tokenizer   │  │ Semantic Tokenizer   │         │
│  │ (σ-VAE, 7.5 Hz)     │  │ (ASR-based)          │         │
│  │ FROZEN ❄️            │  │ FROZEN ❄️             │         │
│  └──────────────────────┘  └──────────────────────┘         │
│           ▼                          ▼                        │
│  ┌─────────────────────────────────────────────────┐         │
│  │        Language Model (Qwen2.5)                 │         │
│  │        1.5B or 7B parameters                     │         │
│  │        TRAINABLE ✓ (LoRA or Full)               │         │
│  └─────────────────────────────────────────────────┘         │
│           │                                                   │
│           │ Hidden States (emotion-encoded)                  │
│           ▼                                                   │
│  ┌─────────────────────────────────────────────────┐         │
│  │    Prediction Head (NOT "diffusion_head")       │         │
│  │    VibeVoiceDiffusionHead (123M params)         │         │
│  │    TRAINABLE ✓                                  │         │
│  └─────────────────────────────────────────────────┘         │
│           ▼                                                   │
│    Acoustic Latents → Acoustic Decoder → Audio               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Facts

- **Tokenizers are FROZEN**: Acoustic and semantic tokenizers are pre-trained and remain frozen during VibeVoice training
- **LLM + Prediction Head are TRAINABLE**: Only these two components learn during training
- **Attribute name**: The diffusion component is called `model.prediction_head`, NOT `model.diffusion_head`
- **No cross-attention**: Uses Adaptive Layer Normalization (AdaLN) for conditioning, not cross-attention layers

---

## 2. Understanding the Actual Components

### 2.1 Acoustic Tokenizer (FROZEN ❄️)

**Purpose:** Compresses 24kHz audio to 7.5 Hz tokens (3200x compression)

```python
# Located at: model.model.acoustic_codec
# Architecture: σ-VAE with 340M parameters
# Input: 24kHz waveform
# Output: 64-dimensional latent vectors at 7.5 Hz
```

**DO NOT TRAIN THIS COMPONENT**

### 2.2 Semantic Tokenizer (FROZEN ❄️)

**Purpose:** Extracts content-focused features using ASR proxy task

```python
# Located at: model.model.semantic_codec
# Architecture: Encoder-only Transformer
# Training: ASR task (frozen during VibeVoice training)
```

**DO NOT TRAIN THIS COMPONENT**

### 2.3 Language Model (TRAINABLE ✓)

**Purpose:** Understands text, dialogue structure, and generates emotion-encoded hidden states

```python
# Located at: model.model.language_model
# Architecture: Qwen2.5-1.5B or Qwen2.5-7B
# Layers: Transformer with self-attention

# Key attention layers for LoRA:
- self_attn.q_proj
- self_attn.k_proj
- self_attn.v_proj
- self_attn.o_proj

# Feed-forward layers:
- mlp.gate_proj
- mlp.up_proj
- mlp.down_proj
```

### 2.4 Prediction Head (TRAINABLE ✓)

**CORRECT Architecture** (verified from actual code):

```python
VibeVoiceDiffusionHead(
  # Input projections
  (noisy_images_proj): Linear(64 → 1536, bias=False)
  (cond_proj): Linear(1536 → 1536, bias=False)  # 🔥 CRITICAL FOR EMOTION
  
  # Timestep embedding
  (t_embedder): TimestepEmbedder(
    (mlp): Sequential(
      (0): Linear(256 → 1536, bias=False)
      (1): SiLU()
      (2): Linear(1536 → 1536, bias=False)
    )
  )
  
  # Core denoising layers (4 layers)
  (layers): ModuleList(
    (0-3): 4 x HeadLayer(
      (ffn): FeedForwardNetwork(
        (gate_proj): Linear(1536 → 4608, bias=False)
        (up_proj): Linear(1536 → 4608, bias=False)
        (down_proj): Linear(4608 → 1536, bias=False)
        (act_fn): SiLU()
      )
      (norm): RMSNorm(dim=1536, eps=1e-05)
      (adaLN_modulation): Sequential(           # 🔥 CRITICAL FOR EMOTION
        (0): SiLU()
        (1): Linear(1536 → 4608, bias=False)
      )
    )
  )
  
  # Output layer
  (final_layer): FinalLayer(
    (norm_final): RMSNorm(dim=1536, eps=1e-05)
    (linear): Linear(1536 → 64, bias=False)
    (adaLN_modulation): Sequential(             # 🔥 CRITICAL FOR EMOTION
      (0): SiLU()
      (1): Linear(1536 → 3072, bias=False)
    )
  )
)
```

**Forward Pass (How Emotion Flows):**

```python
def forward(self, noisy_images, timesteps, condition):
    """
    Args:
        noisy_images: Noisy acoustic latents (64-dim)
        timesteps: Diffusion timesteps
        condition: LLM hidden states (1536-dim) ← CONTAINS EMOTION!
    """
    x = self.noisy_images_proj(noisy_images)    # Project acoustics
    t = self.t_embedder(timesteps)              # Embed timestep
    condition = self.cond_proj(condition)       # Project LLM states 🔥
    c = condition + t                            # Combine: c = emotion + time
    
    # Pass through 4 HeadLayers with AdaLN modulation
    for layer in self.layers:
        x = layer(x, c)  # c modulates each layer 🔥
    
    # Final output
    x = self.final_layer(x, c)  # Final modulation 🔥
    return x
```

**Key Insight:** Emotion information flows through **AdaLN modulation**, not cross-attention!

---

## 3. Loss Functions

### 3.1 Dual Loss Architecture

VibeVoice uses **two losses trained simultaneously**:

```python
total_loss = ce_loss_weight * CE_loss + diffusion_loss_weight * diffusion_loss
```

### 3.2 Cross-Entropy Loss (Language Model)

**Purpose:** Teaches LLM to predict next tokens (text + acoustic placeholders)

```python
def compute_masked_ce_loss(logits, labels, attention_mask):
    """
    Masked cross-entropy: only compute loss on valid tokens
    
    Args:
        logits: Model predictions [batch, seq_len, vocab_size]
        labels: Ground truth tokens [batch, seq_len]
        attention_mask: Valid token mask [batch, seq_len]
    """
    # Shift for next-token prediction
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()
    loss_mask = attention_mask[..., 1:].contiguous()
    
    # Compute cross-entropy
    loss_fct = nn.CrossEntropyLoss(reduction='none')
    loss = loss_fct(
        shift_logits.view(-1, shift_logits.size(-1)),
        shift_labels.view(-1)
    )
    
    # Apply mask and average
    loss = (loss * loss_mask.view(-1)).sum() / loss_mask.sum()
    return loss
```

**Typical Weight:** 0.04 (low - LLM already knows text)

### 3.3 Diffusion MSE Loss (Prediction Head)

**Purpose:** Teaches prediction head to denoise acoustic latents

```python
def compute_diffusion_loss(predicted_noise, target_noise):
    """
    Mean Squared Error for diffusion denoising
    
    Args:
        predicted_noise: Model's noise prediction [batch, seq_len, 64]
        target_noise: Ground truth noise [batch, seq_len, 64]
    """
    loss = F.mse_loss(predicted_noise, target_noise)
    return loss
```

**Typical Weight:** 1.4 (high - primary signal for audio quality)

### 3.4 Complete Loss Computation

```python
def compute_vibevoice_loss(model, batch, ce_weight=0.04, diff_weight=1.4):
    """
    Full VibeVoice training loss
    """
    # 1. Forward through LLM
    lm_outputs = model.model.language_model(
        input_ids=batch['input_ids'],
        attention_mask=batch['attention_mask'],
        output_hidden_states=True
    )
    
    # 2. CE loss on next-token prediction
    ce_loss = compute_masked_ce_loss(
        logits=lm_outputs.logits,
        labels=batch['input_ids'],
        attention_mask=batch['attention_mask']
    )
    
    # 3. Get LLM hidden states (contains emotion encoding!)
    condition = lm_outputs.hidden_states[-1]  # Last layer
    
    # 4. Add noise to acoustic latents (DDPM forward process)
    noise = torch.randn_like(batch['acoustic_latents'])
    timesteps = torch.randint(0, 1000, (batch['acoustic_latents'].shape[0],))
    noisy_latents = add_noise(batch['acoustic_latents'], timesteps, noise)
    
    # 5. Predict noise with prediction head
    predicted_noise = model.model.prediction_head(
        noisy_images=noisy_latents,
        timesteps=timesteps,
        condition=condition
    )
    
    # 6. Diffusion MSE loss
    diffusion_loss = F.mse_loss(predicted_noise, noise)
    
    # 7. Combine losses
    total_loss = ce_weight * ce_loss + diff_weight * diffusion_loss
    
    return {
        'total_loss': total_loss,
        'ce_loss': ce_loss.item(),
        'diffusion_loss': diffusion_loss.item()
    }
```

---

## 4. Fine-tuning Strategy

### 4.1 What to Train

**ALWAYS FROZEN:**
- ✗ `model.model.acoustic_codec` (Acoustic Tokenizer)
- ✗ `model.model.semantic_codec` (Semantic Tokenizer)

**TRAINABLE (Choose Strategy):**
- ✓ `model.model.language_model` (Qwen2.5 LLM)
- ✓ `model.model.prediction_head` (VibeVoiceDiffusionHead)

### 4.2 Training Strategies

#### Strategy A: LoRA on LLM + Full Prediction Head (RECOMMENDED)

**Best for:**
- Limited VRAM (24GB)
- Emotion control
- Language adaptation
- Voice customization

**Configuration:**
```python
# Freeze tokenizers
for param in model.model.acoustic_codec.parameters():
    param.requires_grad = False
for param in model.model.semantic_codec.parameters():
    param.requires_grad = False

# Apply LoRA to LLM
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,                    # Rank
    lora_alpha=32,           # Scaling (typically 2x rank)
    target_modules=[
        "self_attn.q_proj",
        "self_attn.k_proj",
        "self_attn.v_proj",
        "self_attn.o_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model.model.language_model = get_peft_model(
    model.model.language_model,
    lora_config
)

# Full fine-tuning of prediction head
for param in model.model.prediction_head.parameters():
    param.requires_grad = True
```

**Trainable Parameters:** ~130-150M (8-10% of 1.5B model)

#### Strategy B: LoRA on Both LLM and Prediction Head

**Best for:**
- Very limited VRAM (16GB)
- Minimal storage for checkpoints

**Configuration:**
```python
# LoRA on LLM (same as above)
model.model.language_model = get_peft_model(...)

# LoRA on prediction head (target emotion-critical layers)
lora_config_head = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=[
        "cond_proj",                      # Condition projection
        "layers.0.adaLN_modulation.1",    # Layer 0 modulation
        "layers.1.adaLN_modulation.1",    # Layer 1 modulation
        "layers.2.adaLN_modulation.1",    # Layer 2 modulation
        "layers.3.adaLN_modulation.1",    # Layer 3 modulation
        "final_layer.adaLN_modulation.1", # Final layer modulation
    ],
    lora_dropout=0.05,
    bias="none",
)

model.model.prediction_head = get_peft_model(
    model.model.prediction_head,
    lora_config_head
)
```

**Trainable Parameters:** ~50-80M (3-5% of 1.5B model)

#### Strategy C: Full Fine-tuning (Advanced)

**Best for:**
- High-end hardware (48GB+ VRAM)
- Maximum adaptation capacity
- Production use cases

**Configuration:**
```python
# Freeze only tokenizers
for param in model.model.acoustic_codec.parameters():
    param.requires_grad = False
for param in model.model.semantic_codec.parameters():
    param.requires_grad = False

# Train everything else
for param in model.model.language_model.parameters():
    param.requires_grad = True
for param in model.model.prediction_head.parameters():
    param.requires_grad = True
```

---

## 5. Emotion Control Implementation

### 5.1 Understanding Emotion Flow

```
User Input: "[happy] 天王老子来了"
     ↓
Language Model (Qwen2.5)
  - Encodes emotion tag into hidden states
  - Learns: "[happy]" → specific activation pattern
     ↓
LLM Hidden States (1536-dim, emotion-encoded)
     ↓
Prediction Head: cond_proj layer
  - Projects LLM states: 1536 → 1536
  - Extracts emotion information
     ↓
c = condition + timestep
     ↓
AdaLN Modulation Layers (5 total)
  - Compute: scale, shift, gate = adaLN_modulation(c)
  - Apply: x_out = norm(x) * (1 + scale) + shift
  - Learns: "happy → scale_happy, shift_happy"
           "sad → scale_sad, shift_sad"
     ↓
Acoustic Latents (with emotional prosody)
```

### 5.2 Critical Layers for Emotion

**Priority Ranking:**

1. **Condition Projection (HIGHEST):**
   ```
   model.prediction_head.cond_proj
   ```
   This is where LLM emotion encoding enters the prediction head.

2. **AdaLN Modulation Layers (VERY HIGH):**
   ```
   model.prediction_head.layers.0.adaLN_modulation.1
   model.prediction_head.layers.1.adaLN_modulation.1
   model.prediction_head.layers.2.adaLN_modulation.1
   model.prediction_head.layers.3.adaLN_modulation.1
   model.prediction_head.final_layer.adaLN_modulation.1
   ```
   These learn emotion-specific feature modulations.

3. **LLM Attention Layers (HIGH):**
   ```
   model.language_model.*.self_attn.q_proj
   model.language_model.*.self_attn.k_proj
   model.language_model.*.self_attn.v_proj
   ```
   These learn to encode emotion tags into hidden states.

### 5.3 Emotion Tag Format

**Recommended Formats:**

**Prefix (Best for Conditioning):**
```
"[happy] Speaker 1: 天王老子来了"
"[sad] Speaker 2: 我很难过"
"[angry] Speaker 1: 这太过分了！"
```

**Inline (Better for Natural Dialogue):**
```
"Speaker 1 [happy]: 天王老子来了"
"Speaker 2 [sad]: 我很难过"
```

**Multiple Emotions:**
```
"Speaker 1 [happy]: 太好了！[surprised] 真的吗？"
```

### 5.4 Emotion Categories

**Recommended Set:**
```python
emotions = {
    "neutral": "baseline, no emotion tag",
    "happy": "[happy]",
    "sad": "[sad]",
    "angry": "[angry]",
    "surprised": "[surprised]",
    "fearful": "[fearful]",
    "excited": "[excited]",
}
```

**Dataset Balance:**
- Neutral: 40-50%
- Each other emotion: 10-15%
- Minimum 300 samples per emotion
- Recommended: 500-1000 samples per emotion

---

## 6. Training Configuration

### 6.1 Recommended Hyperparameters

```python
training_config = {
    # Optimizer
    "learning_rate": 2.5e-5,        # Conservative for fine-tuning
    "lr_scheduler": "cosine",
    "warmup_ratio": 0.03,           # 3% warmup
    "weight_decay": 0.01,
    
    # Batch configuration
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 16,  # Effective batch = 64
    "max_grad_norm": 0.8,               # Gradient clipping
    
    # Training duration
    "num_train_epochs": 10,
    "save_steps": 500,
    "logging_steps": 10,
    "eval_steps": 500,
    
    # Loss weights
    "ce_loss_weight": 0.04,             # Cross-entropy
    "diffusion_loss_weight": 1.4,       # Diffusion MSE
    
    # LoRA configuration
    "lora_r": 16,                       # Rank for LLM
    "lora_alpha": 32,                   # Scaling factor
    "lora_dropout": 0.05,
    
    # Emotion-specific
    "voice_prompt_drop_rate": 0.0,      # Keep voice prompts
    
    # Mixed precision
    "bf16": True,                       # Use bfloat16 if available
    "fp16": False,
}
```

### 6.2 Curriculum Learning (Optional)

For better stability with emotion control:

```python
def get_emotion_curriculum(epoch):
    """
    Gradually increase emotion complexity
    """
    if epoch < 3:
        # Phase 1: Focus on neutral + one clear emotion
        return ["neutral", "happy"]
    elif epoch < 6:
        # Phase 2: Add contrasting emotions
        return ["neutral", "happy", "sad", "angry"]
    else:
        # Phase 3: Full emotion range
        return ["neutral", "happy", "sad", "angry", "surprised", "fearful"]
```

---

## 7. Data Preparation

### 7.1 Dataset Format

**JSONL Format (one JSON object per line):**

```json
{"text": "[happy] Speaker 1: 天王老子来了。", "audio": "path/to/audio1.wav", "voice_prompt": "path/to/speaker1_prompt.wav"}
{"text": "[sad] Speaker 2: 我很难过。", "audio": "path/to/audio2.wav", "voice_prompt": "path/to/speaker2_prompt.wav"}
{"text": "Speaker 1: 这是中性的语气。", "audio": "path/to/audio3.wav", "voice_prompt": "path/to/speaker1_prompt.wav"}
```

**Required Fields:**
- `text`: Transcript with emotion tags
- `audio`: Path to 24kHz mono WAV file
- `voice_prompt`: Path to 3-5 second speaker reference (24kHz mono WAV)

### 7.2 Audio Requirements

```python
import torchaudio

def validate_audio(audio_path):
    """
    Check audio meets VibeVoice requirements
    """
    waveform, sr = torchaudio.load(audio_path)
    
    # Check sample rate
    assert sr == 24000, f"Sample rate must be 24kHz, got {sr}Hz"
    
    # Check channels
    assert waveform.shape[0] == 1, f"Audio must be mono, got {waveform.shape[0]} channels"
    
    # Check duration (for training samples)
    duration = waveform.shape[1] / sr
    assert 0.5 <= duration <= 30, f"Duration should be 0.5-30s, got {duration}s"
    
    return True

def prepare_audio(audio_path, target_sr=24000):
    """
    Convert audio to VibeVoice format
    """
    waveform, sr = torchaudio.load(audio_path)
    
    # Resample if needed
    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(sr, target_sr)
        waveform = resampler(waveform)
    
    # Convert to mono
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)
    
    return waveform
```

### 7.3 Dataset Size Requirements

**Minimum:**
- 300 samples per emotion category
- Total: ~2,000 samples (for 5-6 emotions)

**Recommended:**
- 500-1000 samples per emotion
- Total: ~5,000-8,000 samples

**Optimal:**
- 2000+ samples per emotion
- Total: 10,000+ samples

### 7.4 Data Quality Guidelines

**Audio Quality:**
- Clean recordings (minimal background noise)
- Clear speech (not mumbled or distorted)
- Consistent recording conditions
- Natural emotional expression

**Transcript Quality:**
- Accurate transcription
- Proper punctuation
- Emotion tags placed correctly
- Speaker labels match voice prompts

---

## 8. Complete Implementation

### 8.1 Setup and Installation

```bash
# Clone repository
git clone https://github.com/vibevoice-community/VibeVoice.git
cd VibeVoice

# Create environment
conda create -n vibevoice python=3.10
conda activate vibevoice

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers==4.51.3  # Specific version required
pip install peft accelerate datasets
pip install soundfile librosa
```

### 8.2 Load Model and Apply LoRA

```python
import torch
from vibevoice.modular.modeling_vibevoice_inference import (
    VibeVoiceForConditionalGenerationInference
)
from peft import LoraConfig, get_peft_model

# Load base model
model = VibeVoiceForConditionalGenerationInference.from_pretrained(
    "microsoft/VibeVoice-1.5B",
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

# Freeze tokenizers
for param in model.model.acoustic_codec.parameters():
    param.requires_grad = False
for param in model.model.semantic_codec.parameters():
    param.requires_grad = False

# Apply LoRA to LLM
lora_config_llm = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=[
        "self_attn.q_proj",
        "self_attn.k_proj",
        "self_attn.v_proj",
        "self_attn.o_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model.model.language_model = get_peft_model(
    model.model.language_model,
    lora_config_llm
)

# Full fine-tuning of prediction head
for param in model.model.prediction_head.parameters():
    param.requires_grad = True

# Verify trainable parameters
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total = sum(p.numel() for p in model.parameters())
print(f"Trainable: {trainable:,} ({100*trainable/total:.2f}%)")
print(f"Total: {total:,}")
```

### 8.3 Data Loading

```python
from torch.utils.data import Dataset, DataLoader
import json
import torchaudio

class EmotionTTSDataset(Dataset):
    def __init__(self, jsonl_path, processor):
        self.data = []
        with open(jsonl_path, 'r') as f:
            for line in f:
                self.data.append(json.loads(line))
        self.processor = processor
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        sample = self.data[idx]
        
        # Load audio
        waveform, sr = torchaudio.load(sample['audio'])
        if sr != 24000:
            resampler = torchaudio.transforms.Resample(sr, 24000)
            waveform = resampler(waveform)
        
        # Load voice prompt
        voice_prompt, sr_v = torchaudio.load(sample['voice_prompt'])
        if sr_v != 24000:
            resampler = torchaudio.transforms.Resample(sr_v, 24000)
            voice_prompt = resampler(voice_prompt)
        
        return {
            'text': sample['text'],
            'audio': waveform,
            'voice_prompt': voice_prompt
        }

# Create dataset
from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor

processor = VibeVoiceProcessor.from_pretrained("microsoft/VibeVoice-1.5B")
dataset = EmotionTTSDataset("train.jsonl", processor)
dataloader = DataLoader(dataset, batch_size=4, shuffle=True)
```

### 8.4 Training Loop

```python
from torch.optim import AdamW
from transformers import get_cosine_schedule_with_warmup
import torch.nn.functional as F

# Optimizer
optimizer = AdamW(
    [p for p in model.parameters() if p.requires_grad],
    lr=2.5e-5,
    weight_decay=0.01
)

# Scheduler
total_steps = len(dataloader) * 10  # 10 epochs
scheduler = get_cosine_schedule_with_warmup(
    optimizer,
    num_warmup_steps=int(0.03 * total_steps),
    num_training_steps=total_steps
)

# Training loop
model.train()
ce_weight = 0.04
diff_weight = 1.4

for epoch in range(10):
    epoch_loss = 0
    
    for step, batch in enumerate(dataloader):
        # Process batch with processor
        inputs = processor(
            text=[b['text'] for b in batch],
            audio=[b['audio'] for b in batch],
            voice_samples=[b['voice_prompt'] for b in batch],
            return_tensors="pt",
            padding=True
        )
        
        # Move to device
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # Forward pass through LLM
        lm_outputs = model.model.language_model(
            input_ids=inputs['input_ids'],
            attention_mask=inputs['attention_mask'],
            output_hidden_states=True
        )
        
        # CE loss
        ce_loss = compute_masked_ce_loss(
            lm_outputs.logits,
            inputs['input_ids'],
            inputs['attention_mask']
        )
        
        # Prepare diffusion inputs
        condition = lm_outputs.hidden_states[-1]
        acoustic_latents = model.model.acoustic_codec.encode(inputs['audio'])
        
        # Add noise
        noise = torch.randn_like(acoustic_latents)
        timesteps = torch.randint(0, 1000, (acoustic_latents.shape[0],))
        noisy_latents = add_noise(acoustic_latents, timesteps, noise)
        
        # Predict noise
        predicted_noise = model.model.prediction_head(
            noisy_images=noisy_latents,
            timesteps=timesteps,
            condition=condition
        )
        
        # Diffusion loss
        diffusion_loss = F.mse_loss(predicted_noise, noise)
        
        # Combined loss
        total_loss = ce_weight * ce_loss + diff_weight * diffusion_loss
        
        # Backward
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.8)
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()
        
        epoch_loss += total_loss.item()
        
        if step % 10 == 0:
            print(f"Epoch {epoch}, Step {step}: "
                  f"Loss={total_loss.item():.4f}, "
                  f"CE={ce_loss.item():.4f}, "
                  f"Diff={diffusion_loss.item():.4f}")
    
    # Save checkpoint
    model.save_pretrained(f"checkpoints/epoch_{epoch}")
    processor.save_pretrained(f"checkpoints/epoch_{epoch}")
```

### 8.5 Inference with Fine-tuned Model

```python
# Load fine-tuned model
from peft import PeftModel

base_model = VibeVoiceForConditionalGenerationInference.from_pretrained(
    "microsoft/VibeVoice-1.5B"
)

# Load LoRA adapter
model = PeftModel.from_pretrained(
    base_model,
    "checkpoints/epoch_9"
)

model.eval()

# Generate with emotion control
text = "[happy] Speaker 1: 天王老子来了！"
voice_prompt_path = "speaker1_reference.wav"

# Process
processor = VibeVoiceProcessor.from_pretrained("checkpoints/epoch_9")
voice_prompt, _ = torchaudio.load(voice_prompt_path)

inputs = processor(
    text=[text],
    voice_samples=[voice_prompt],
    return_tensors="pt"
)

# Generate
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_length=2048,
        num_inference_steps=10,  # Diffusion steps
        guidance_scale=1.3
    )

# Save audio
torchaudio.save("output_happy.wav", outputs.audio, 24000)
```

---

## 9. Hardware Requirements

### 9.1 VRAM Requirements

**VibeVoice-1.5B:**

| Configuration | Training VRAM | Inference VRAM |
|--------------|---------------|----------------|
| Full Fine-tuning | 32-40 GB | 8 GB |
| LoRA LLM + Full Head | 24-28 GB | 8 GB |
| LoRA Both | 16-20 GB | 8 GB |

**VibeVoice-7B:**

| Configuration | Training VRAM | Inference VRAM |
|--------------|---------------|----------------|
| Full Fine-tuning | 80+ GB | 19 GB |
| LoRA LLM + Full Head | 48-56 GB | 19 GB |
| LoRA Both | 32-40 GB | 19 GB |

### 9.2 Optimization Techniques

**Gradient Checkpointing:**
```python
model.gradient_checkpointing_enable()
```
Reduces VRAM by ~30-40%, increases training time by ~20%

**Mixed Precision (bfloat16):**
```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

with autocast():
    loss = compute_loss(...)
scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

**Gradient Accumulation:**
```python
# Effective batch size = 4 * 16 = 64
per_device_train_batch_size = 4
gradient_accumulation_steps = 16
```

---

## 10. Troubleshooting

### 10.1 Common Issues

**Issue: AttributeError: 'VibeVoiceConfig' object has no attribute 'diffusion_head'**

**Solution:** The attribute is called `prediction_head`, not `diffusion_head`:
```python
# Wrong
model.model.diffusion_head

# Correct
model.model.prediction_head
```

**Issue: Out of VRAM during training**

**Solutions:**
1. Reduce batch size: `per_device_train_batch_size = 2`
2. Enable gradient checkpointing: `model.gradient_checkpointing_enable()`
3. Use LoRA on both components
4. Reduce sequence length: `max_length = 1024`

**Issue: Model generates robotic/unnatural speech**

**Solutions:**
1. Check diffusion_loss_weight is high enough (1.4+)
2. Increase training epochs (10-15)
3. Ensure audio quality in training data
4. Verify voice prompts are clean and clear

**Issue: Emotion control not working**

**Solutions:**
1. Verify emotion tags are preserved in tokenization
2. Check adaLN_modulation layers are trainable
3. Increase number of emotion-tagged samples (500+ per emotion)
4. Use prefix format: `[happy] text` instead of inline

**Issue: Loss becomes NaN**

**Solutions:**
1. Reduce learning rate: `2e-5` → `1e-5`
2. Enable gradient clipping: `max_grad_norm = 0.8`
3. Check for corrupted audio files
4. Reduce batch size

### 10.2 Verification Checklist

Before training:
- [ ] Tokenizers are frozen
- [ ] LoRA applied to LLM correctly
- [ ] Prediction head is trainable
- [ ] Audio files are 24kHz mono
- [ ] Emotion tags present in text
- [ ] Loss weights configured (0.04 CE, 1.4 diffusion)
- [ ] Gradient clipping enabled

During training:
- [ ] Both CE and diffusion losses decreasing
- [ ] No NaN losses
- [ ] VRAM usage stable
- [ ] Checkpoints saving correctly

After training:
- [ ] Generated audio is clear
- [ ] Emotion control working
- [ ] Speaker identity preserved
- [ ] No degradation from base model

---

## Appendix: Quick Reference

### Layer Names (for LoRA targeting)

**Language Model:**
```
model.language_model.layers.{i}.self_attn.q_proj
model.language_model.layers.{i}.self_attn.k_proj
model.language_model.layers.{i}.self_attn.v_proj
model.language_model.layers.{i}.self_attn.o_proj
model.language_model.layers.{i}.mlp.gate_proj
model.language_model.layers.{i}.mlp.up_proj
model.language_model.layers.{i}.mlp.down_proj
```

**Prediction Head (Emotion Critical):**
```
model.prediction_head.cond_proj
model.prediction_head.layers.0.adaLN_modulation.1
model.prediction_head.layers.1.adaLN_modulation.1
model.prediction_head.layers.2.adaLN_modulation.1
model.prediction_head.layers.3.adaLN_modulation.1
model.prediction_head.final_layer.adaLN_modulation.1
```

### Key Commands

**Inspect model structure:**
```python
print(model.model.prediction_head)
```

**Count parameters:**
```python
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
total = sum(p.numel() for p in model.parameters())
print(f"{trainable:,} / {total:,} ({100*trainable/total:.2f}%)")
```

**Save LoRA checkpoint:**
```python
model.save_pretrained("checkpoint_path")
processor.save_pretrained("checkpoint_path")
```

**Load LoRA checkpoint:**
```python
from peft import PeftModel
model = PeftModel.from_pretrained(base_model, "checkpoint_path")
```

---

## Summary

**Key Takeaways:**

1. **Architecture**: VibeVoice uses frozen tokenizers + trainable LLM + trainable prediction head
2. **Correct naming**: `model.prediction_head`, not `diffusion_head`
3. **No cross-attention**: Uses AdaLN modulation for emotion conditioning
4. **Dual loss**: CE (0.04 weight) + Diffusion MSE (1.4 weight)
5. **Emotion flow**: Text tags → LLM hidden states → cond_proj → AdaLN modulation → acoustic features
6. **Critical layers**: cond_proj + all adaLN_modulation layers (5 total)
7. **Recommended**: LoRA on LLM + full fine-tuning of prediction head

**For emotion control, you CAN:**
- Add emotion tags like `[happy]`, `[sad]` to text
- Fine-tune LLM to encode emotions into hidden states
- Fine-tune prediction head AdaLN layers to translate emotions to prosody

**For singing, you CANNOT:**
- VibeVoice is speech-only, use dedicated SVS models instead

---

**Document Version:** 1.0  
**Last Updated:** November 2025  
**Verified Against:** vibevoice-community/VibeVoice (actual source code inspection)
