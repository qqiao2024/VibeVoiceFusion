# VibeVoice API Documentation

This document provides complete API documentation for VibeVoice backend services.

## Table of Contents

1. [Training Management API](#training-management-api)
2. [Dataset Management API](#dataset-management-api)

---

# Training Management API

## Overview

The Training Management API provides endpoints for managing LoRA fine-tuning training jobs. All endpoints are project-scoped and work with **TrainingState** objects directly. Training and inference share a global task queue (only one runs at a time).

## Base URL

```
http://localhost:9527/api/v1/projects/{project_id}/training
```

## Data Models

### TrainingState

The complete training state object that includes both job metadata and live metrics:

```json
{
  // Job Metadata
  "task_id": "abc123",
  "job_name": "My LoRA Training",
  "project_id": "my-project",
  "config": { /* TrainConfig object */ },
  "created_at": "2025-12-02T10:30:00Z",

  // Progress
  "current_step": 150,
  "estimated_total_steps": 1000,
  "current_epoch": 5,
  "total_epochs": 10,

  // Training Parameters
  "learning_rate": 0.0001,
  "batch_size": 1,
  "accumlate_grad_steps": 16,

  // Loss Metrics
  "current_loss": 0.245,
  "current_diffusion_loss": 0.21,
  "current_ce_loss": 0.035,
  "average_epoch_loss": 0.28,
  "average_epoch_diffusion_loss": 0.24,
  "average_epoch_ce_loss": 0.04,

  // Timing
  "start_time": "2025-12-02T10:35:00Z",
  "current_timestamp": "2025-12-02T10:45:00Z",
  "estimated_total_elpase": 3600.0,
  "latest_epoch_elapsed": 120.5,
  "latest_step_elapsed": 1.2,
  "average_step_time": 1.15,
  "steps_per_second": 0.87,

  // Status
  "status": "Training",  // Prepare, Training, Completed, Failed

  // TensorBoard
  "tensorboard_logdir": "./tensorboard_logs/my_lora_abc123_20251202",

  // Output Files
  "lora_files": ["checkpoint_epoch_5.pt", "checkpoint_epoch_10.pt"],
  "final_lora_file": "final_model.pt"
}
```

### TrainConfig

Training configuration object (matches `vibevoice/training/trainer.py`):

```json
{
  "lora_name": "vibevoice_lora",
  "epochs": 10,
  "batch_size": 1,
  "learning_rate": 0.0001,
  "dataset_path": "workspace/project-id/datasets/dataset-id/datasets.jsonl",
  "output_dir": "./lora_output",
  "multiplier": 1.0,
  "lora_dim": 4,
  "lora_alpha": null,
  "lora_dropout": null,
  "model_path": null,
  "number_of_layers": 0,
  "dtype": "bfloat16",
  "model_config_path": null,
  "optimizer_type": "AdamW8bit",
  "optimizer_args": null,
  "seeds": 42,
  "dataset_repeats": 1,
  "speech_compress_ratio": 3200,
  "semantic_dim": 128,
  "diffusion_loss_weight": 10.4,
  "ce_loss_weight": 0.004,
  "device": "cuda",
  "gradient_accumulation_steps": 16,
  "dataload_workers": 2,
  "save_model_per_num_epoch": 10
}
```

## API Endpoints

### 1. Create Training Job

**POST** `/api/v1/projects/{project_id}/training`

Create and start a new training job. Returns 409 if task manager is busy.

**Request Body:**
```json
{
  "job_name": "My LoRA Training",
  "config": {
    "lora_name": "my_lora",
    "epochs": 10,
    "batch_size": 1,
    "learning_rate": 0.0001,
    "dataset_path": "workspace/project-id/datasets/dataset-id/datasets.jsonl",
    ...
  }
}
```

**Response (201 Created):**
```json
{
  "message": "Training started successfully",
  "task_id": "abc123def456",
  "state": { /* TrainingState object */ }
}
```

**Status Codes:**
- `201 Created` - Training job created and started
- `400 Bad Request` - Invalid configuration or missing fields
- `404 Not Found` - Project not found
- `409 Conflict` - Task manager is busy (another task is running)
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X POST "http://localhost:9527/api/v1/projects/my-project/training" \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "LoRA Fine-tuning v1",
    "config": {
      "lora_name": "my_lora",
      "epochs": 10,
      "batch_size": 1,
      "learning_rate": 0.0001,
      "dataset_path": "workspace/my-project/datasets/dataset-abc/datasets.jsonl"
    }
  }'
```

---

### 2. List Training Jobs

**GET** `/api/v1/projects/{project_id}/training`

Get all training jobs for a project, sorted by created_at (newest first).

**Response (200 OK):**
```json
{
  "states": [
    { /* TrainingState object 1 */ },
    { /* TrainingState object 2 */ }
  ],
  "count": 2
}
```

**Status Codes:**
- `200 OK` - Success
- `404 Not Found` - Project not found
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl "http://localhost:9527/api/v1/projects/my-project/training"
```

---

### 3. Get Current Training Job

**GET** `/api/v1/projects/{project_id}/training/current`

Get the currently running training job with live metrics from task manager.

**Response (200 OK):**
```json
{
  "message": "Current training job retrieved successfully",
  "state": { /* Live TrainingState object */ }
}
```

**Response (200 OK, no active training):**
```json
{
  "message": "No active training job at the moment",
  "state": null
}
```

**Status Codes:**
- `200 OK` - Success (state may be null if no active training)
- `404 Not Found` - Project not found
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl "http://localhost:9527/api/v1/projects/my-project/training/current"
```

**Note:** This endpoint reads live state from the training engine in memory, providing real-time metrics updates.

---

### 4. Get Specific Training Job

**GET** `/api/v1/projects/{project_id}/training/{job_id}`

Get details of a specific training job by task_id.

**Response (200 OK):**
```json
{
  "state": { /* TrainingState object */ }
}
```

**Status Codes:**
- `200 OK` - Success
- `404 Not Found` - Job or project not found
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl "http://localhost:9527/api/v1/projects/my-project/training/abc123def456"
```

---

### 5. Delete Training Job

**DELETE** `/api/v1/projects/{project_id}/training/{job_id}`

Delete a training job. Cannot delete a currently running job.

**Response (200 OK):**
```json
{
  "message": "Training job deleted successfully",
  "job_id": "abc123def456"
}
```

**Status Codes:**
- `200 OK` - Job deleted successfully
- `400 Bad Request` - Cannot delete running job
- `404 Not Found` - Job or project not found
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X DELETE "http://localhost:9527/api/v1/projects/my-project/training/abc123def456"
```

**Behavior:**
- Deletes job from `training_history.json`
- Cannot delete if job is currently running
- LoRA files are not automatically deleted (TODO)

---

### 6. Batch Delete Training Jobs

**POST** `/api/v1/projects/{project_id}/training/batch-delete`

Delete multiple training jobs in one request.

**Request Body:**
```json
{
  "job_ids": ["job1", "job2", "job3"]
}
```

**Response (200 OK):**
```json
{
  "message": "Training jobs deleted successfully",
  "deleted_count": 2,
  "failed_count": 1,
  "deleted_ids": ["job1", "job2"],
  "failed_ids": ["job3"]
}
```

**Status Codes:**
- `200 OK` - Batch deletion completed (check counts for details)
- `400 Bad Request` - Invalid request body
- `404 Not Found` - Project not found
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X POST "http://localhost:9527/api/v1/projects/my-project/training/batch-delete" \
  -H "Content-Type: application/json" \
  -d '{"job_ids": ["abc123", "def456", "ghi789"]}'
```

---

## Training Status Values

| Backend Status | Frontend Mapping | Description |
|---------------|-----------------|-------------|
| `Prepare` | `pending` | Job created, waiting to start |
| `Training` | `training` | Training in progress |
| `Completed` | `completed` | Training finished successfully |
| `Failed` | `failed` | Training failed with error |

---

## Architecture Notes

### Shared Task Manager

- Inference and training share a **global task queue** (`task_manager.task.gm`)
- Only **one task** (inference OR training) can run at a time
- Starting a training job when queue is busy returns **409 Conflict**

### Storage Model

- **Single file**: `workspace/{project-id}/training/training_history.json`
- Structure: `{ "task_id": TrainingState, ... }`
- No separate job metadata file - all data in TrainingState

### Live Metrics

**Get current training:**
```python
task = gm.get_current_task()
engine = task.unwrap()
if isinstance(engine, BaseTrainingEngine):
    live_state = engine.get_state()  # Returns live TrainingState
```

**Get historical training:**
```python
# Read from training_history.json
states_meta = json.load(open("training_history.json"))
state = TrainingState.from_dict(states_meta[task_id])
```

### Engine Types

- **TrainingEngine**: Production with GPU, integrates with VibeVoiceTrainer
- **FakeTrainingEngine**: Development/testing, simulates realistic metrics
- Both engines update TrainingState via `TrainingStateWriter`

---

## Translation Support

All messages support bilingual translation (English/Chinese):

**Language Detection:**
- Via `X-Language` header (`en` or `zh`)
- Via `Accept-Language` header
- Defaults to English

**Example:**
```bash
curl -H "X-Language: zh" \
  "http://localhost:9527/api/v1/projects/my-project/training"
```

---

## Error Handling

### Common Error Responses

**Task Manager Busy (409):**
```json
{
  "error": "Conflict",
  "message": "Task manager is busy. Please wait for the current task to complete"
}
```

**Training Job Not Found (404):**
```json
{
  "error": "Not Found",
  "message": "Training job not found"
}
```

**Cannot Delete Running Job (400):**
```json
{
  "error": "Bad Request",
  "message": "Cannot delete a currently running training job"
}
```

---

## Workspace Structure

```
workspace/{project-id}/training/
├── training_history.json  # { "task_id": TrainingState, ... }
└── lora_output/           # LoRA checkpoints (created by trainer)
    └── {lora-name}/
        ├── checkpoint_epoch_5.pt
        ├── checkpoint_epoch_10.pt
        └── final_model.pt
```

---

## Implementation Notes

### Service Layer

Backend follows service layer architecture:

- **API Layer** (`backend/api/training.py`) - HTTP endpoint handlers
- **Service Layer** (`backend/services/training_service.py`) - Business logic with TrainingState
- **Training Layer** (`backend/training/state.py`, `backend/training/engine.py`) - Core training logic

### Key Features

1. **TrainingState-based** - Single dataclass for all job data
2. **Live metrics** - Real-time state from running engine
3. **Atomic operations** - Ensures data consistency
4. **409 on conflict** - Clear feedback when queue is busy
5. **i18n support** - Full bilingual support
6. **FakeTrainingEngine** - Development without GPU

---

# Dataset Management API

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
