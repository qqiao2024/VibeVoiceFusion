# Preset Voice Feature

This document describes the preset voice feature that allows users to quickly create speakers using pre-provided voice samples instead of uploading their own files.

## Overview

The preset voice feature provides a collection of ready-to-use voice samples that users can select when creating new speakers. This enables rapid prototyping and testing without requiring users to record or upload their own voice files.

### Key Benefits

- **Quick Start**: Users can immediately start generating speech without preparing voice samples
- **Variety**: Multiple languages, genders, and styles available
- **Non-destructive**: Original preset files are never modified; copies are made for each speaker

### Design Principles

1. **Preset files are READ-ONLY** - Backend never modifies files in `backend/preset_voice/`
2. **Copy-on-use** - When a user selects a preset, the file is copied to the project's voices directory
3. **No origin tracking** - Once copied, preset speakers are identical to uploaded speakers
4. **Metadata from filename** - No separate config file; metadata is parsed from filenames

## Preset Voice Files

### Location

Preset voice files are stored in:
```
backend/preset_voice/
├── en-Alice_woman.wav
├── en-Carter_man.wav
├── en-Frank_man.wav
├── en-Mary_woman_bgm.wav
├── en-Maya_woman.wav
├── in-Samuel_man.wav
├── zh-Anchen_man_bgm.wav
├── zh-Bowen_man.wav
└── zh-Xinran_woman.wav
```

### Filename Convention

```
{language}-{name}_{gender}[_bgm].wav
```

| Component | Description | Values |
|-----------|-------------|--------|
| `language` | 2-letter language code | `en`, `zh`, `in` |
| `name` | Voice name (capitalized) | `Alice`, `Bowen`, etc. |
| `gender` | Speaker gender | `man`, `woman` |
| `_bgm` | Optional BGM indicator | Present or absent |

### Examples

| Filename | Language | Name | Gender | BGM |
|----------|----------|------|--------|-----|
| `en-Alice_woman.wav` | English | Alice | Female | No |
| `zh-Bowen_man.wav` | Chinese | Bowen | Male | No |
| `en-Mary_woman_bgm.wav` | English | Mary | Female | Yes |

### Adding New Preset Voices

To add a new preset voice:

1. Prepare a WAV audio file (10-30 seconds recommended)
2. Name the file following the convention: `{lang}-{Name}_{gender}[_bgm].wav`
3. Place the file in `backend/preset_voice/`
4. The preset will be automatically discovered on next API request

## Architecture

### Backend Components

#### PresetVoiceService

**File**: `backend/services/preset_voice_service.py`

```python
@dataclass
class PresetVoice:
    filename: str       # "en-Alice_woman.wav"
    language: str       # "en", "zh", "in"
    name: str           # "Alice"
    gender: str         # "man", "woman"
    has_bgm: bool       # True/False
    display_name: str   # "Alice (English, Female)"

class PresetVoiceService:
    def list_presets(language?, gender?, has_bgm?, locale?) -> List[PresetVoice]
    def get_preset(filename, locale?) -> Optional[PresetVoice]
    def get_preset_path(filename) -> Optional[Path]
    def get_available_languages(locale?) -> List[Dict]
```

#### SpeakerService Extension

**File**: `backend/services/speaker_service.py`

```python
def add_speaker_from_preset(
    self,
    description: str,
    preset_file_path: Path
) -> SpeakerRole:
    """
    Creates a new speaker by copying a preset voice file.

    1. Generates UUID-based filename for the copy
    2. Copies preset file to project's voices directory
    3. Creates SpeakerRole metadata
    4. Saves metadata atomically
    5. Returns created speaker
    """
```

### API Endpoints

#### List Preset Voices

```http
GET /api/v1/preset-voices
```

Query parameters:
- `language` (optional): Filter by language code (`en`, `zh`, `in`)
- `gender` (optional): Filter by gender (`man`, `woman`)
- `has_bgm` (optional): Filter by BGM presence (`true`, `false`)

Response:
```json
{
  "presets": [
    {
      "filename": "en-Alice_woman.wav",
      "language": "en",
      "name": "Alice",
      "gender": "woman",
      "has_bgm": false,
      "display_name": "Alice (English, Female)"
    }
  ],
  "count": 9
}
```

#### List Available Languages

```http
GET /api/v1/preset-voices/languages
```

Response:
```json
{
  "languages": [
    {"code": "en", "name": "English", "count": 5},
    {"code": "zh", "name": "Chinese", "count": 3},
    {"code": "in", "name": "Indian English", "count": 1}
  ]
}
```

#### Preview Preset Audio

```http
GET /api/v1/preset-voices/{filename}/preview
```

Returns: Audio file stream (audio/wav)

#### Create Speaker from Preset

```http
POST /api/v1/projects/{project_id}/speakers/from-preset
Content-Type: application/json

{
  "preset_filename": "en-Alice_woman.wav",
  "description": "Main character voice"
}
```

Response:
```json
{
  "speaker_id": "Speaker 1",
  "description": "Main character voice",
  "voice_filename": "a1b2c3d4e5f6.wav",
  "created_at": "2025-12-19T10:00:00Z",
  "updated_at": "2025-12-19T10:00:00Z"
}
```

### Frontend Components

#### PresetVoiceSelector

**File**: `frontend/components/PresetVoiceSelector.tsx`

A React component that provides:
- Filter dropdowns for language, gender, and BGM
- Grid layout of preset voice cards
- Audio preview functionality (play/stop)
- Selection button to create speaker

```typescript
interface PresetVoiceSelectorProps {
  onSelect: (preset: PresetVoice) => Promise<void>;
}
```

#### Integration in SpeakerRoleManager

The preset tab is added as the third tab alongside "Upload" and "Record":

```
[Upload] [Record] [Preset]
```

When a user selects a preset:
1. `handleSelectPreset()` is called with the preset info
2. API call to `/speakers/from-preset` creates the speaker
3. Page reloads to sync state with backend

### TypeScript Types

**File**: `frontend/types/preset.ts`

```typescript
interface PresetVoice {
  filename: string;
  language: string;
  name: string;
  gender: 'man' | 'woman';
  has_bgm: boolean;
  display_name: string;
}

interface PresetLanguage {
  code: string;
  name: string;
  count: number;
}
```

### API Client Methods

**File**: `frontend/lib/api.ts`

```typescript
// List preset voices with optional filters
listPresetVoices(filters?: {
  language?: string;
  gender?: 'man' | 'woman';
  has_bgm?: boolean;
}): Promise<{ presets: PresetVoice[]; count: number }>

// Get available languages
listPresetLanguages(): Promise<{ languages: PresetLanguage[] }>

// Get preview audio URL
getPresetPreviewUrl(filename: string): string

// Create speaker from preset
createSpeakerFromPreset(projectId: string, data: {
  preset_filename: string;
  description?: string;
}): Promise<Speaker>
```

## Internationalization

### Backend i18n Keys

**Files**: `backend/i18n/en.json`, `backend/i18n/zh.json`

```json
{
  "errors": {
    "preset_voice_not_found": "Preset voice not found",
    "preset_filename_required": "Preset filename is required"
  }
}
```

### Frontend i18n Keys

**Files**: `frontend/lib/i18n/locales/en.json`, `frontend/lib/i18n/locales/zh.json`

```json
{
  "speaker": {
    "preset": "Preset",
    "presetVoices": "Preset Voices",
    "selectPreset": "Select a preset voice"
  },
  "preset": {
    "allLanguages": "All Languages",
    "allGenders": "All Genders",
    "allTypes": "All Types",
    "withBgm": "With BGM",
    "withoutBgm": "Without BGM",
    "female": "Female",
    "male": "Male",
    "preview": "Preview",
    "stop": "Stop",
    "select": "Select",
    "noPresetsFound": "No preset voices found matching your filters",
    "selectPresetToCreate": "Select a preset voice to create a new speaker"
  }
}
```

## Configuration

### Backend Configuration

**File**: `backend/config.py`

```python
PRESET_VOICE_DIR = Path(os.environ.get('PRESET_VOICE_DIR',
    os.path.join(os.path.dirname(__file__), 'preset_voice'))).resolve()
```

Environment variable: `PRESET_VOICE_DIR` - Override default preset voice directory

## Future Enhancements

Potential improvements for future development:

1. **User-uploaded presets**: Allow admins to upload new preset voices via UI
2. **Preset categories**: Add categories like "Narration", "Character", "Commercial"
3. **Preset metadata file**: Optional `presets.json` for additional metadata (description, tags)
4. **Favorite presets**: Allow users to mark frequently-used presets
5. **Preset quality ratings**: User ratings for preset voice quality
6. **Dynamic language detection**: Auto-detect language from audio content
7. **Preset voice cloning**: Generate variations of existing presets

## File Summary

### New Files Created

| File | Purpose |
|------|---------|
| `backend/services/preset_voice_service.py` | Preset voice business logic |
| `backend/api/preset_voices.py` | REST API endpoints |
| `frontend/types/preset.ts` | TypeScript type definitions |
| `frontend/components/PresetVoiceSelector.tsx` | UI component |

### Modified Files

| File | Changes |
|------|---------|
| `backend/config.py` | Added `PRESET_VOICE_DIR` |
| `backend/api/__init__.py` | Registered preset_voices routes |
| `backend/services/speaker_service.py` | Added `add_speaker_from_preset()` |
| `backend/api/speakers.py` | Added `/from-preset` endpoint |
| `backend/i18n/en.json` | Added error messages |
| `backend/i18n/zh.json` | Added Chinese error messages |
| `frontend/lib/api.ts` | Added preset API methods |
| `frontend/lib/i18n/locales/en.json` | Added UI translations |
| `frontend/lib/i18n/locales/zh.json` | Added Chinese UI translations |
| `frontend/components/SpeakerRoleManager.tsx` | Added Preset tab |
