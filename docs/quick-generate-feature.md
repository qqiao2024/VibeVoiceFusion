# Quick Generate Feature Design

## Problem Statement

The current VibeVoice workflow requires users to:

1. Create a project
2. Upload speaker voice samples
3. Create a dialog session with proper formatting
4. Configure generation parameters and start generation

This multi-step process is too complex for users who simply want to try voice generation quickly. They need to understand the project structure, speaker naming conventions, and dialog formatting before they can generate their first audio.

## Proposed Solution

Implement a "Quick Generate" feature that allows users to generate voice audio in a single step:

1. Upload a voice sample (reference audio)
2. Enter text (dialogue or narration - auto-detected)
3. Set seed and batch size
4. Click generate

No project creation, no speaker setup, no session management required.

## Design Decisions

| Question | Decision |
|----------|----------|
| Storage Strategy | **Dedicated storage** (`workspace/_quick-generate/`) |
| Multi-Speaker | **Single voice sample** - same voice for all detected speakers |
| Save to Project | **Full save** - can convert quick-generate to full project |
| LoRA Support | **No LoRA** - base model only in quick generate |
| Text Detection | **Auto-detect only** - no manual override |
| Entry Point | **Home page** - primary action alongside projects |
| Generation History | **Persistent history** - stored with cleanup policy |

## User Flow

```text
┌─────────────────────────────────────────────────────────────┐
│                     Quick Generate                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Voice Sample                                          │  │
│  │ [Upload audio file] or [Select from presets]         │  │
│  │                                                       │  │
│  │ 🎵 sample.wav                           [Preview] [X] │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Text to Generate                                      │  │
│  │ ┌──────────────────────────────────────────────────┐ │  │
│  │ │ Enter your text here...                          │ │  │
│  │ │                                                   │ │  │
│  │ │ For dialogue, use format:                        │ │  │
│  │ │ Speaker 1: Hello!                                │ │  │
│  │ │                                                   │ │  │
│  │ │ For narration, just enter plain text.            │ │  │
│  │ └──────────────────────────────────────────────────┘ │  │
│  │ Detected: [Narration] ⓘ                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Generation Settings                                   │  │
│  │                                                       │  │
│  │ Seed: [____________] [🎲 Random]                     │  │
│  │                                                       │  │
│  │ Generate multiple versions:  [ ] Enable              │  │
│  │ Count: [====●======] 5                               │  │
│  │                                                       │  │
│  │ [Advanced Settings ▼]                                │  │
│  │   - CFG Scale                                        │  │
│  │   - Model dtype                                      │  │
│  │   - Offloading                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    [Generate Voice]                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Generated Audio                                       │  │
│  │                                                       │  │
│  │ 🔊 ▶ ━━━━━━━━━━●━━━━━━━━━━━━━━━━ 0:15 / 0:45         │  │
│  │                                                       │  │
│  │ [Download] [Save to Project ▼]                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Mode Detection Logic

Auto-detect dialogue vs narration based on text content:

```python
def detect_mode(text: str) -> str:
    """
    Detect if text is dialogue or narration format.

    Dialogue format: Lines starting with "Speaker X:" pattern
    Narration format: Plain text without speaker prefixes
    """
    import re

    lines = text.strip().split('\n')
    # Check if any non-empty line starts with "Speaker X:" pattern
    speaker_pattern = re.compile(r'^[^:]+:\s*\S')

    for line in lines:
        line = line.strip()
        if line and speaker_pattern.match(line):
            return "dialogue"

    return "narration"
```

**Behavior:**

- **Dialogue detected**: Text contains lines like "Speaker 1: Hello"
  - All speakers use the same uploaded voice sample
  - Useful for testing dialogue flow with single voice

- **Narration detected**: Plain text without speaker prefixes
  - Single speaker reads all content
  - Standard narration mode

## Technical Design

### Storage Structure

```text
workspace/_quick-generate/
├── voices/
│   └── {uuid}.wav              # Uploaded voice samples
├── outputs/
│   └── {request_id}/
│       ├── output.wav          # Single generation
│       └── item_{n}.wav        # Multi-generation items
├── history.json                # Generation history metadata
└── cleanup.json                # Cleanup tracking (retention policy)
```

### Data Models

#### QuickGenerateRequest

```python
@dataclass
class QuickGenerateRequest:
    request_id: str                    # UUID
    voice_file: str                    # Path to uploaded voice
    text: str                          # User's input text
    detected_mode: str                 # "dialogue" or "narration"
    seeds: int                         # Random seed
    batch_size: int                    # 1-20
    cfg_scale: float                   # Default 1.3
    model_dtype: str                   # Default "bf16"
    offloading: Optional[dict]         # Offloading config
    created_at: str                    # ISO timestamp
```

#### QuickGenerateResult

```python
@dataclass
class QuickGenerateResult:
    request_id: str
    status: str                        # pending, inferencing, completed, failed
    voice_file: str                    # Reference to uploaded voice
    text: str                          # Original text
    detected_mode: str                 # dialogue or narration
    output_files: List[str]            # Generated audio paths
    details: Optional[dict]            # Progress details
    error: Optional[str]               # Error message if failed
    created_at: str
    completed_at: Optional[str]
```

### Backend API

#### Start Quick Generation

```http
POST /api/v1/quick-generate
Content-Type: multipart/form-data
```

**Form Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `voice_file` | File | Yes | Audio file (WAV, MP3, M4A, FLAC, WEBM) |
| `text` | String | Yes | Text to generate |
| `seeds` | Integer | No | Random seed (default: random) |
| `batch_size` | Integer | No | 1-20 (default: 1) |
| `cfg_scale` | Float | No | CFG scale (default: 1.3) |
| `model_dtype` | String | No | Model dtype (default: "bf16") |
| `offloading` | JSON | No | Offloading configuration |

**Response (200 OK):**

```json
{
  "message": "Quick generation started",
  "request_id": "abc123-def456",
  "detected_mode": "narration",
  "status": "pending"
}
```

**Response (409 Conflict - Task Manager Busy):**

```json
{
  "error": "Conflict",
  "message": "A generation task is already running"
}
```

#### Get Quick Generation Status

```http
GET /api/v1/quick-generate/{request_id}
```

**Response (200 OK - In Progress):**

```json
{
  "request_id": "abc123-def456",
  "status": "inferencing",
  "detected_mode": "narration",
  "details": {
    "current": 45,
    "total_step": 100,
    "percentage": 45.0,
    "current_batch_index": 0,
    "batch_size": 3
  }
}
```

**Response (200 OK - Completed):**

```json
{
  "request_id": "abc123-def456",
  "status": "completed",
  "detected_mode": "narration",
  "output_files": ["output.wav"],
  "created_at": "2025-01-07T10:00:00Z",
  "completed_at": "2025-01-07T10:01:30Z"
}
```

#### Download Generated Audio

```http
GET /api/v1/quick-generate/{request_id}/download
GET /api/v1/quick-generate/{request_id}/items/{index}/download
```

**Response:** Binary audio data (audio/wav)

#### List Quick Generation History

```http
GET /api/v1/quick-generate/history?limit=20&offset=0
```

**Response (200 OK):**

```json
{
  "generations": [
    {
      "request_id": "abc123",
      "status": "completed",
      "detected_mode": "narration",
      "text_preview": "Hello, this is a test...",
      "created_at": "2025-01-07T10:00:00Z"
    }
  ],
  "count": 1,
  "total": 15
}
```

#### Delete Quick Generation

```http
DELETE /api/v1/quick-generate/{request_id}
```

#### Save to Project

```http
POST /api/v1/quick-generate/{request_id}/save-to-project
```

**Request Body:**

```json
{
  "project_id": "existing-project-id",
  "speaker_name": "My Speaker",
  "session_name": "My Dialog"
}
```

Or create new project:

```json
{
  "project_name": "New Project Name",
  "speaker_name": "My Speaker",
  "session_name": "My Dialog"
}
```

**Response (200 OK):**

```json
{
  "message": "Saved to project successfully",
  "project_id": "project-id",
  "speaker_id": "speaker-id",
  "session_id": "session-id",
  "generation_id": "generation-id"
}
```

### Frontend Components

#### New Page

- `app/quick-generate/page.tsx` - Quick Generate page

#### Components

- `QuickGenerateForm.tsx` - Main form with voice upload, text input, settings
- `QuickGenerateProgress.tsx` - Generation progress display
- `QuickGenerateResult.tsx` - Audio player, download button, save to project
- `QuickGenerateHistory.tsx` - List of previous quick generations
- `SaveToProjectModal.tsx` - Modal for saving to existing/new project

#### Home Page Update

Update `components/ProjectSelector.tsx` to include Quick Generate button:

```text
┌─────────────────────────────────────────────────────────────┐
│  VibeVoice                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │                     │  │                     │          │
│  │   ⚡ Quick Generate │  │   📁 Your Projects │          │
│  │                     │  │                     │          │
│  │   Generate voice    │  │   Manage projects   │          │
│  │   in one step       │  │   and workflows     │          │
│  │                     │  │                     │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  Recent Projects                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Project A        │ Project B        │ Project C      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Cleanup Policy

Automatic cleanup of old quick-generate data:

- **Voice samples**: Delete after 7 days of no use
- **Generated audio**: Delete after 30 days
- **History entries**: Keep metadata for 90 days, then archive

Cleanup runs on server startup and daily via background task.

## Implementation Phases

### Phase 1: Core MVP

- [ ] Backend: Quick generate API endpoints
- [ ] Backend: Dedicated storage structure
- [ ] Backend: Mode detection logic
- [ ] Frontend: Quick Generate page with form
- [ ] Frontend: Progress display and audio playback
- [ ] Frontend: Download functionality

### Phase 2: History & Polish

- [ ] Backend: History API endpoints
- [ ] Backend: Cleanup policy implementation
- [ ] Frontend: Generation history list
- [ ] Frontend: Home page integration with Quick Generate button
- [ ] i18n: Bilingual support for all new strings

### Phase 3: Save to Project

- [ ] Backend: Save to project API
- [ ] Frontend: Save to Project modal
- [ ] Frontend: Project selector (existing or new)
- [ ] Integration testing

## API Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/quick-generate` | Start quick generation |
| GET | `/api/v1/quick-generate/{id}` | Get generation status |
| GET | `/api/v1/quick-generate/{id}/download` | Download audio |
| GET | `/api/v1/quick-generate/{id}/items/{n}/download` | Download batch item |
| GET | `/api/v1/quick-generate/history` | List history |
| DELETE | `/api/v1/quick-generate/{id}` | Delete generation |
| POST | `/api/v1/quick-generate/{id}/save-to-project` | Save to project |

## Notes

- Quick Generate uses the same task manager as regular generation (only one task at a time)
- No LoRA support in quick generate - users must use full workflow for LoRA
- All speakers in dialogue mode use the same uploaded voice
- Preset voices can be used as voice sample source
