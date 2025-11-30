# Dataset Item Management API Documentation

## Overview

The Dataset Item Management API provides endpoints for managing dataset items (text, audio, and voice prompts) within datasets. All endpoints are project-scoped and support full CRUD operations.

## Base URL

```
http://localhost:9527/api/v1/projects/{project_id}/datasets/{dataset_id}/items
```

## Data Models

### DatasetItem

```json
{
  "text": "string",           // Text content of the item
  "audio": "filename.wav",   // Audio filename (stored in dataset's audio directory)
  "voice_prompts": [         // Array of voice prompt filenames
    "prompt1.wav",
    "prompt2.wav"
  ]
}
```

### Storage Structure

```
workspace/{project_id}/datasets/{dataset_id}/
├── datasets.jsonl              # JSONL file with one item per line
├── audio/                      # Audio files referenced in items
│   └── {uuid}.wav
└── voice_prompts/              # Voice prompt files
    └── {uuid}.wav
```

## API Endpoints

### 1. List Dataset Items (with Pagination)

**GET** `/api/v1/projects/{project_id}/datasets/{dataset_id}/items`

Get items in a dataset with optional pagination support.

**Query Parameters:**
- `offset` (optional, integer) - Starting index (0-based, default: 0)
- `limit` (optional, integer) - Maximum number of items to return (default: all items)

**Response:**
```json
{
  "items": [
    {
      "text": "Example text",
      "audio": "abc123.wav",
      "voice_prompts": ["def456.wav", "ghi789.wav"]
    }
  ],
  "count": 1,
  "total": 100,
  "offset": 0,
  "limit": 10
}
```

**Response Fields:**
- `items` - Array of dataset items in the requested page
- `count` - Number of items in current response
- `total` - Total number of items in the dataset
- `offset` - Starting index used for this request
- `limit` - Limit used for this request (null if not specified)

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid pagination parameters (negative offset, zero/negative limit)
- `404 Not Found` - Project or dataset not found
- `500 Internal Server Error` - Server error

**Examples:**

Get all items:
```bash
curl "http://localhost:9527/api/v1/projects/my-voice-test/datasets/abc/items"
```

Get first 10 items:
```bash
curl "http://localhost:9527/api/v1/projects/my-voice-test/datasets/abc/items?limit=10"
```

Get items 20-29 (for scrolling):
```bash
curl "http://localhost:9527/api/v1/projects/my-voice-test/datasets/abc/items?offset=20&limit=10"
```

**Pagination Behavior:**
- If `offset` exceeds total items, returns empty array with `count: 0`
- If `offset + limit` exceeds total, returns remaining items
- Both parameters are optional - omit for all items
- Validation errors return 400 status code

---

### 2. Add Dataset Item

**POST** `/api/v1/projects/{project_id}/datasets/{dataset_id}/items`

Add a new item to the dataset with audio file and voice prompts.

**Form Data:**
- `text` (required) - Text content
- `audio_file` (required) - Audio file (WAV, MP3, M4A, FLAC, WEBM)
- `voice_prompt_files` (required, multiple) - One or more voice prompt files

**Response:**
```json
{
  "text": "Example text",
  "audio": "e1bc908c.wav",
  "voice_prompts": ["bb78de05.wav", "df8dfe8e.wav"]
}
```

**Status Codes:**
- `201 Created` - Item created successfully
- `400 Bad Request` - Validation error (missing fields, invalid file type)
- `404 Not Found` - Project or dataset not found
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X POST "http://localhost:9527/api/v1/projects/my-voice-test/datasets/abc/items" \
  -F "text=This is a test sentence" \
  -F "audio_file=@/path/to/audio.wav" \
  -F "voice_prompt_files=@/path/to/prompt1.wav" \
  -F "voice_prompt_files=@/path/to/prompt2.wav"
```

**Validation:**
- Text cannot be empty
- Audio file is required and must be valid audio format
- At least one voice prompt file is required
- All voice prompt files must be valid audio format

---

### 3. Update Dataset Item

**PUT** `/api/v1/projects/{project_id}/datasets/{dataset_id}/items/{item_index}`

Update an existing dataset item. All fields are optional - only provided fields will be updated.

**Parameters:**
- `item_index` (path) - Zero-based index of the item to update

**Form Data:**
- `text` (optional) - New text content
- `audio_file` (optional) - New audio file
- `voice_prompt_files` (optional, multiple) - New voice prompt files

**Response:**
```json
{
  "text": "Updated text",
  "audio": "c8af33e5.wav",
  "voice_prompts": ["f822eef0.wav"]
}
```

**Status Codes:**
- `200 OK` - Item updated successfully
- `400 Bad Request` - Validation error
- `404 Not Found` - Project, dataset, or item not found
- `500 Internal Server Error` - Server error

**Examples:**

Update text only:
```bash
curl -X PUT "http://localhost:9527/api/v1/projects/my-voice-test/datasets/abc/items/0" \
  -F "text=Updated text content"
```

Update audio file only:
```bash
curl -X PUT "http://localhost:9527/api/v1/projects/my-voice-test/datasets/abc/items/0" \
  -F "audio_file=@/path/to/new_audio.wav"
```

Update all fields:
```bash
curl -X PUT "http://localhost:9527/api/v1/projects/my-voice-test/datasets/abc/items/0" \
  -F "text=Completely updated item" \
  -F "audio_file=@/path/to/audio.wav" \
  -F "voice_prompt_files=@/path/to/prompt1.wav" \
  -F "voice_prompt_files=@/path/to/prompt2.wav"
```

**Behavior:**
- Old files are automatically deleted after successful update
- If update fails, new files are cleaned up and old files remain
- Atomic operation ensures data consistency

---

### 4. Delete Dataset Item

**DELETE** `/api/v1/projects/{project_id}/datasets/{dataset_id}/items/{item_index}`

Delete a dataset item and its associated files.

**Parameters:**
- `item_index` (path) - Zero-based index of the item to delete

**Response:**
```json
{
  "message": "Item deleted successfully",
  "item_index": 0
}
```

**Status Codes:**
- `200 OK` - Item deleted successfully
- `404 Not Found` - Project, dataset, or item not found
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X DELETE "http://localhost:9527/api/v1/projects/my-voice-test/datasets/abc/items/0"
```

**Behavior:**
- Deletes the item from the JSONL file
- Removes associated audio file from `audio/` directory
- Removes all associated voice prompt files from `voice_prompts/` directory
- Updates dataset item count

---

## File Management

### Supported Audio Formats

- `.wav` - WAV audio
- `.mp3` - MP3 audio
- `.m4a` - M4A audio
- `.flac` - FLAC audio
- `.webm` - WebM audio

### File Naming

All uploaded files are renamed with UUID-based filenames to ensure uniqueness:
- Format: `{uuid}.{extension}`
- Example: `e1bc908ca37b48e096259b8e8219fd9f.wav`

### File Cleanup

The API implements automatic file cleanup:
- **On successful update:** Old files are deleted
- **On failed operation:** New files are deleted, old files preserved
- **On item deletion:** All associated files are removed
- **On dataset deletion:** Entire dataset directory is removed

### Atomic Operations

All write operations use atomic file operations:
1. Changes written to temporary file
2. Temporary file replaces original on success
3. Cleanup on failure ensures consistency

---

## Dataset Metadata Synchronization

The dataset's `item_count` field is automatically synchronized:
- Updated after adding an item
- Updated after deleting an item
- Recalculated by counting lines in JSONL file

---

## Error Handling

### Common Error Responses

**Validation Error (400):**
```json
{
  "error": "Validation error",
  "message": "Text is required"
}
```

**Not Found Error (404):**
```json
{
  "error": "Not Found",
  "message": "Dataset not found"
}
```

**Internal Server Error (500):**
```json
{
  "error": "Internal Server Error",
  "message": "Failed to save dataset items: ..."
}
```

### Validation Rules

**Text Field:**
- Cannot be empty or whitespace-only
- Required when creating item
- Optional when updating item

**Audio File:**
- Required when creating item
- Optional when updating item
- Must be one of supported formats
- File must have valid filename

**Voice Prompt Files:**
- At least one required when creating item
- Optional when updating item
- All files must be valid audio formats
- Multiple files supported

---

## Translation Support

All error messages and success messages support bilingual translation (English/Chinese):

**Language Detection:**
- Via `X-Language` header (`en` or `zh`)
- Via `Accept-Language` header
- Defaults to English if not specified

**Example with Language Header:**
```bash
curl -H "X-Language: zh" \
  "http://localhost:9527/api/v1/projects/my-voice-test/datasets/abc/items"
```

---

## Testing Examples

### Complete Workflow

```bash
# 1. Create test audio files
python3 -c "
import numpy as np
import wave

sample_rate = 16000
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration))
audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

for name in ['audio', 'prompt1', 'prompt2']:
    with wave.open(f'/tmp/{name}.wav', 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(audio_data.tobytes())
"

# 2. Add item
curl -X POST "http://localhost:9527/api/v1/projects/my-project/datasets/my-dataset/items" \
  -F "text=Example sentence" \
  -F "audio_file=@/tmp/audio.wav" \
  -F "voice_prompt_files=@/tmp/prompt1.wav" \
  -F "voice_prompt_files=@/tmp/prompt2.wav"

# 3. List items
curl "http://localhost:9527/api/v1/projects/my-project/datasets/my-dataset/items"

# 4. Update item text
curl -X PUT "http://localhost:9527/api/v1/projects/my-project/datasets/my-dataset/items/0" \
  -F "text=Updated example sentence"

# 5. Delete item
curl -X DELETE "http://localhost:9527/api/v1/projects/my-project/datasets/my-dataset/items/0"
```

### Testing Validation

```bash
# Empty text (should fail)
curl -X POST "http://localhost:9527/api/v1/projects/my-project/datasets/my-dataset/items" \
  -F "text=" \
  -F "audio_file=@/tmp/audio.wav" \
  -F "voice_prompt_files=@/tmp/prompt1.wav"

# Missing audio (should fail)
curl -X POST "http://localhost:9527/api/v1/projects/my-project/datasets/my-dataset/items" \
  -F "text=Test"

# Missing voice prompts (should fail)
curl -X POST "http://localhost:9527/api/v1/projects/my-project/datasets/my-dataset/items" \
  -F "text=Test" \
  -F "audio_file=@/tmp/audio.wav"

# Invalid index (should fail)
curl -X DELETE "http://localhost:9527/api/v1/projects/my-project/datasets/my-dataset/items/999"
```

---

## Implementation Notes

### Service Layer

Backend implementation follows a service layer architecture:

- **API Layer** (`backend/api/datasets.py`) - HTTP endpoint handlers
- **Service Layer** (`backend/services/dataset_service.py`) - Business logic
- **Model Layer** (`backend/models/dataset.py`) - Data models

### Key Features

1. **JSONL Storage** - Efficient line-by-line operations for large datasets
2. **UUID Filenames** - Prevents naming conflicts
3. **Atomic Operations** - Ensures data consistency
4. **Automatic Cleanup** - Manages file lifecycle
5. **Validation** - Comprehensive input validation
6. **i18n Support** - Full bilingual support
7. **Item Count Sync** - Automatic metadata updates

### Performance Considerations

- JSONL format allows efficient append operations
- Item updates require rewriting entire JSONL file
- Large datasets (>10k items) may have slower update/delete operations
- **Pagination support** enables efficient handling of large datasets in frontend

---

## Virtual Scrolling Integration

The pagination API is designed to work seamlessly with virtual scrolling in the frontend.

### Recommended Implementation Pattern

For virtual scrolling with ~50 visible items + 5 buffer items:

```typescript
// Calculate visible range based on scroll position
const startIndex = Math.floor(scrollTop / itemHeight);
const endIndex = startIndex + visibleCount + bufferCount;

// Fetch only the needed items
const response = await fetch(
  `/api/v1/projects/${projectId}/datasets/${datasetId}/items?offset=${startIndex}&limit=${endIndex - startIndex}`
);

const { items, total } = await response.json();
```

### Key Benefits

1. **Efficient Memory Usage** - Only loads items currently visible or near viewport
2. **Fast Initial Load** - First render only fetches ~55 items instead of all
3. **Smooth Scrolling** - Buffer zone prevents flickering during scroll
4. **Scalable** - Works well with datasets of any size (100 to 100k+ items)

### Scroll Event Handling

```typescript
const handleScroll = useCallback((scrollTop: number) => {
  const newStartIndex = Math.floor(scrollTop / ITEM_HEIGHT);

  // Only fetch if scrolled beyond buffer zone
  if (Math.abs(newStartIndex - currentStartIndex) > BUFFER_SIZE) {
    fetchItems(newStartIndex);
  }
}, [currentStartIndex]);
```

### Caching Strategy

Consider implementing a cache layer to avoid refetching:

- Cache fetched pages in memory
- Invalidate cache on item add/update/delete
- Use Map or object keyed by offset for fast lookup

---

## Related APIs

- **Dataset Management** - CRUD operations for datasets
- **Dataset Import/Export** - ZIP-based import/export
- **Project Management** - Project-level operations

See `backend/api/datasets.py` for complete implementation.
