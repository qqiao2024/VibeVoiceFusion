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
| Voice Source | **Upload or Preset** - support both custom upload and preset voices |
| LoRA Support | **No LoRA** - base model only in quick generate |
| Text Detection | **Auto-detect only** - no manual override |
| Entry Point | **Home page** - primary action alongside projects |
| Generation History | **Persistent history** - stored in history.json |

## User Flow

```text
┌─────────────────────────────────────────────────────────────┐
│                     Quick Generate                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Voice Sample                                          │  │
│  │ [Upload]  [Preset]  ← Tab selection                  │  │
│  │                                                       │  │
│  │ Upload Tab:                                           │  │
│  │ ┌────────────────────────────────────────────────┐   │  │
│  │ │ Drop audio file here or click to browse        │   │  │
│  │ └────────────────────────────────────────────────┘   │  │
│  │ 🎵 sample.wav                        [▶ Preview] [X] │  │
│  │                                                       │  │
│  │ Preset Tab:                                           │  │
│  │ [Language ▼] [Gender ▼] [Type ▼]  ← Filters          │  │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐        │  │
│  │ │ Alice      │ │ Carter     │ │ Frank      │        │  │
│  │ │ EN Female  │ │ EN Male    │ │ EN Male    │        │  │
│  │ │ [▶] [✓]    │ │ [▶] [✓]    │ │ [▶] [✓]    │        │  │
│  │ └────────────┘ └────────────┘ └────────────┘        │  │
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
│  │ [Download]                                            │  │
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

    Dialogue format: Lines starting with "Speaker N:" pattern (case-insensitive)
    Narration format: Plain text without speaker prefixes
    """
    import re

    lines = text.strip().split('\n')
    # Only match "Speaker N:" pattern specifically to avoid false positives
    # from text containing colons (URLs, timestamps, error logs, etc.)
    speaker_pattern = re.compile(r'^Speaker\s+\d+\s*:', re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if line and speaker_pattern.match(line):
            return "dialogue"

    return "narration"
```

**Important**: The pattern specifically matches `Speaker N:` format only (case-insensitive). Earlier versions used `^[^:]+:\s*\S` which incorrectly detected any text with colons (error logs, timestamps, URLs) as dialogue.

**Behavior:**

- **Dialogue detected**: Text contains lines like "Speaker 1: Hello"
  - All speakers use the same uploaded voice sample
  - Useful for testing dialogue flow with single voice

- **Narration detected**: Plain text without speaker prefixes
  - Single speaker reads all content
  - Text is automatically converted to dialogue format with "Speaker 1:" prefix for each paragraph
  - Standard narration mode

### Narration Mode Conversion

For narration mode, the backend automatically converts plain text to the required dialogue format:

```python
def _convert_narration_to_script(self, text: str) -> str:
    """Convert narration text to script format with Speaker 1: prefix."""
    lines = text.strip().split('\n')
    paragraphs = []
    current_paragraph = []

    for line in lines:
        stripped = line.strip()
        if stripped:
            current_paragraph.append(stripped)
        elif current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
            current_paragraph = []

    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))

    # Add Speaker 1: prefix to each paragraph
    scripts = [f"Speaker 1: {paragraph}" for paragraph in paragraphs]
    return '\n'.join(scripts).replace("'", "'")
```

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

### Frontend Components

#### New Page

- `app/quick-generate/page.tsx` - Quick Generate page with two-column layout (history left, form right)

#### Components

- `QuickGenerateNavigation.tsx` - Dedicated sidebar navigation for Quick Generate page (no project switching, only generate menu item)
- `QuickGenerateHistory.tsx` - Left panel history list with:
  - Pagination support
  - Multi-select with bulk delete
  - Expandable details showing voice preview, full text, generated audio
  - Status badges and mode indicators
  - Fetches full generation data on expand (history API returns subset)
- `QuickGenerateForm.tsx` - Main form with voice upload/preset selection, text input, settings (integrated in page.tsx)
  - Voice source tabs: Upload (drag & drop with preview) and Preset (grid with filters)
  - Audio preview for both uploaded files and preset voices
- `QuickGenerateProgress.tsx` - Generation progress display (integrated in page.tsx)
- `QuickGenerateResult.tsx` - Audio player, download button (integrated in page.tsx)

#### Layout Integration

- `LayoutWrapper.tsx` - Routes to `QuickGenerateNavigation` when pathname is `/quick-generate`, otherwise uses standard `Navigation`

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

### Voice Source Options

The Quick Generate page supports two voice source options:

1. **Upload**: User uploads their own audio file (WAV, MP3, M4A, FLAC, WEBM)
   - Drag and drop or click to browse
   - Preview uploaded audio before generation
   - Remove and re-upload as needed

2. **Preset**: Select from pre-provided voice samples
   - Filter by language (English, Chinese, Indian English)
   - Filter by gender (Male, Female)
   - Filter by type (With/Without BGM)
   - Preview any preset before selection
   - Uses existing preset voice API endpoints

## Implementation Phases

### Phase 1: Core MVP ✅ Completed

- [x] Backend: Quick generate API endpoints
- [x] Backend: Dedicated storage structure (`workspace/_quick-generate/`)
- [x] Backend: Mode detection logic (fixed pattern to `^Speaker\s+\d+\s*:`)
- [x] Backend: Narration mode conversion (adds "Speaker 1:" prefix)
- [x] Frontend: Quick Generate page with form
- [x] Frontend: Progress display and audio playback
- [x] Frontend: Download functionality

### Phase 2: History & UI Redesign ✅ Completed

- [x] Backend: History API endpoints (list, get, delete)
- [x] Backend: Voice preview endpoint
- [x] Frontend: Generation history list with pagination
- [x] Frontend: Dedicated navigation (`QuickGenerateNavigation.tsx`)
- [x] Frontend: Two-column layout (history left, form right)
- [x] Frontend: Expandable history items with full details
- [x] Frontend: Multi-select and bulk delete
- [x] Frontend: Home page integration with Quick Generate button
- [x] i18n: Bilingual support for all new strings

### Phase 3: Preset Voice Selection ✅ Completed

- [x] Frontend: Voice source tabs (Upload / Preset)
- [x] Frontend: Audio preview for uploaded voice files
- [x] Frontend: Preset voice selection with filters (language, gender, BGM)
- [x] Frontend: Preset voice preview playback
- [x] i18n: Translations for preset voice UI

## API Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/quick-generate` | Start quick generation |
| GET | `/api/v1/quick-generate/{id}` | Get generation status |
| GET | `/api/v1/quick-generate/{id}/download` | Download audio |
| GET | `/api/v1/quick-generate/{id}/items/{n}/download` | Download batch item |
| GET | `/api/v1/quick-generate/history` | List history |
| DELETE | `/api/v1/quick-generate/{id}` | Delete generation |
| GET | `/api/v1/preset-voices` | List preset voices (with filters) |
| GET | `/api/v1/preset-voices/{filename}/preview` | Preview preset audio |

## Notes

- Quick Generate uses the same task manager as regular generation (only one task at a time)
- No LoRA support in quick generate - users must use full workflow for LoRA
- All speakers in dialogue mode use the same uploaded voice
- Preset voices can be used as voice sample source

---

## Work Log

### 2025-01-07: Bug Fixes and UI Redesign

**Bug Fixes:**

1. **InferencePhase Error** (`backend/models/quick_generate.py`)
   - Issue: `InferencePhase()` takes no arguments - was trying to instantiate a class with string constants
   - Fix: Changed `status: InferencePhase` to `status: str` in dataclass, simplified `to_dict()` and `from_dict()` methods

2. **Mode Detection False Positives** (`backend/models/quick_generate.py`, `frontend/app/quick-generate/page.tsx`)
   - Issue: Regex `^[^:]+:\s*\S` matched any text with colons (error logs, timestamps, URLs)
   - Fix: Changed to `^Speaker\s+\d+\s*:` (case-insensitive) to only match "Speaker N:" format

3. **Narration Mode Missing Speaker Prefix** (`backend/inference/quick_generate_inference.py`)
   - Issue: Narration mode passed raw text to inference without required "Speaker 1:" prefix
   - Fix: Added `_convert_narration_to_script()` method that converts paragraphs to "Speaker 1: {paragraph}" format

**UI Redesign:**

1. **Dedicated Navigation** (`frontend/components/QuickGenerateNavigation.tsx`)
   - Created simplified sidebar with only "Generate Voice" menu item
   - Removed project switching and other menu items
   - Added "Back to Projects" button

2. **Two-Column Layout** (`frontend/app/quick-generate/page.tsx`)
   - Left column: Generation history list
   - Right column: Generation form and current progress/result
   - Similar layout to project generate-voice page

3. **History Component** (`frontend/components/QuickGenerateHistory.tsx`)
   - Pagination support (10 items per page)
   - Multi-select with bulk delete functionality
   - Expandable details showing voice preview, full text, generated audio
   - Fixed TypeScript type mismatch: `QuickGenerateHistoryItem` (list) vs `QuickGenerate` (full data)
   - Fetches full generation data via API when expanding or selecting

4. **Layout Integration** (`frontend/components/LayoutWrapper.tsx`)
   - Routes to `QuickGenerateNavigation` when pathname is `/quick-generate`
   - Uses standard `Navigation` for all other pages

5. **i18n Updates** (`frontend/lib/i18n/locales/en.json`, `zh.json`)
   - Added translations for history, delete, select actions
   - Added translations for expanded detail labels

### 2026-01-08: Multi-Voice Support & UI Improvements

**Multi-Voice Prompt Support:**

1. **Up to 4 Voice Prompts** (`frontend/app/quick-generate/page.tsx`, `backend/models/quick_generate.py`)
   - Extended voice source to support 1-4 voice files
   - Changed `voice_file` (single) to `voice_files` (array) with backward compatibility
   - Added voice slot management UI with preview and remove buttons
   - Backend converts preset voices to files before generation

2. **History Detail View Fix** (`frontend/components/QuickGenerateHistory.tsx`, `frontend/lib/api.ts`)
   - Added `getQuickGenerationVoicePreviewByIndexUrl()` API method
   - History detail now displays multiple audio players for each voice file
   - Updated `QuickGenerate` type to include `voice_files: string[]`

**UI Consistency Improvements:**

3. **Delete Confirmation Dialog** (`frontend/components/QuickGenerateHistory.tsx`)
   - Replaced browser `confirm()` with modal dialog matching normal generation style
   - Consistent button styling with normal generation delete functionality
   - Added i18n translations for confirmation messages

4. **History Refresh Fix** (`frontend/components/QuickGenerateHistory.tsx`)
   - Added `currentGenerationStatus` prop to track generation state
   - History auto-refreshes when status becomes 'completed' or 'failed'
   - Fixed stuck "pending" status display issue

5. **Generation Display Improvements** (`frontend/app/quick-generate/page.tsx`)
   - Completely rewrote `renderGenerationResult()` to match normal generation page
   - Status-colored borders/backgrounds based on generation state
   - Overall progress bar with batch progress info
   - Generated items list with individual status badges
   - Performance statistics grid (total duration, generation time, average RTF)
   - Model settings display and timestamps

6. **Individual Progress Bars** (`frontend/app/quick-generate/page.tsx`, `frontend/types/quickGenerate.ts`, `backend/models/quick_generate.py`, `backend/inference/quick_generate_inference.py`)
   - Added `current_step` and `total_steps` fields to `QuickGenerateItem`
   - Backend visitor now updates step progress on current generation item
   - Each generating voice shows individual progress bar with "Step X/Y" display
   - Completed items show duration, RTF, and generation time stats

7. **New Generation Button Position** (`frontend/app/quick-generate/page.tsx`)
   - Moved button outside the generation card for better visibility
   - Appears only when generation is completed or failed

**Task Indicator & Navigation:**

8. **Task Indicator Support** (`backend/api/tasks.py`, `frontend/components/QuickGenerateNavigation.tsx`, `frontend/types/task.ts`)
   - Backend `/api/v1/tasks/current` now returns `type: 'quick_generation'` for quick gen tasks
   - Added `isQuickGenerationTask()` type guard
   - QuickGenerateNavigation now shows task indicator matching normal navigation

9. **Navigation Improvements** (`frontend/components/Navigation.tsx`, `frontend/components/QuickGenerateNavigation.tsx`)
   - Made VibeVoice logo clickable to return to home page
   - Removed "Back to Projects" button from quick generate navigation
   - Added `navigation.goToHome` i18n translations

10. **Home Page Quick Generate Card** (`frontend/components/ProjectSelector.tsx`)
    - Changed Quick Generate from horizontal bar to card layout
    - Matches "Create New Project" card style with emerald/teal gradient
    - Consistent hover effects and sizing

**Data Model Updates:**

```python
# backend/models/quick_generate.py
@dataclass
class QuickGenerateItem:
    audio_path: str
    seeds: int
    generation_time: float
    batch_index: int = 0
    audio_duration_seconds: Optional[float] = None
    real_time_factor: Optional[float] = None
    current_step: Optional[int] = None   # NEW: Current step in generation
    total_steps: Optional[int] = None    # NEW: Total steps in generation
```

```typescript
// frontend/types/quickGenerate.ts
interface QuickGenerateItem {
  batch_index: number;
  audio_path: string;
  seeds: number;
  generation_time: number;
  audio_duration_seconds?: number;
  real_time_factor?: number;
  current_step?: number;   // NEW
  total_steps?: number;    // NEW
}
```
