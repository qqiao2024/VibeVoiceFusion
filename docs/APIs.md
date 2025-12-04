# VibeVoice API Documentation

This document provides complete API documentation for VibeVoice backend services.

## Base URL

```
http://localhost:9527/api/v1
```

## Table of Contents

1. [Projects API](#projects-api)
2. [Speakers API](#speakers-api)
3. [Dialog Sessions API](#dialog-sessions-api)
4. [Generation API](#generation-api)
5. [Dataset Management API](#dataset-management-api)
6. [Training Management API](#training-management-api)

---

# Projects API

## Overview

The Projects API provides endpoints for managing projects. Each project is a workspace containing speakers, dialog sessions, datasets, and training jobs.

## Endpoints

### 1. List Projects

**GET** `/api/v1/projects`

Get all projects.

**Response (200 OK):**
```json
{
  "projects": [
    {
      "id": "my-project",
      "name": "My Project",
      "created_at": "2025-12-02T10:00:00Z"
    }
  ]
}
```

### 2. Create Project

**POST** `/api/v1/projects`

Create a new project.

**Request Body:**
```json
{
  "name": "My New Project"
}
```

**Response (201 Created):**
```json
{
  "id": "generated-project-id",
  "name": "My New Project",
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 3. Get Project

**GET** `/api/v1/projects/{project_id}`

Get project details.

**Response (200 OK):**
```json
{
  "id": "my-project",
  "name": "My Project",
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 4. Update Project

**PUT** `/api/v1/projects/{project_id}`

Update project details.

**Request Body:**
```json
{
  "name": "Updated Project Name"
}
```

**Response (200 OK):**
```json
{
  "id": "my-project",
  "name": "Updated Project Name",
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 5. Delete Project

**DELETE** `/api/v1/projects/{project_id}`

Delete a project and all its data.

**Response (200 OK):**
```json
{
  "message": "Project deleted successfully"
}
```

---

# Speakers API

## Overview

The Speakers API manages speaker voice samples within a project. Each speaker has a unique ID and one or more voice samples.

## Endpoints

### 1. List Speakers

**GET** `/api/v1/projects/{project_id}/speakers`

Get all speakers for a project.

**Response (200 OK):**
```json
{
  "speakers": [
    {
      "id": "speaker-1-id",
      "name": "Speaker 1",
      "voice_file": "uuid.wav",
      "created_at": "2025-12-02T10:00:00Z"
    }
  ]
}
```

### 2. Create Speaker

**POST** `/api/v1/projects/{project_id}/speakers`

Upload a new speaker voice sample.

**Form Data:**
- `name` (required) - Speaker name
- `voice_file` (required) - Audio file (WAV, MP3, M4A, FLAC, WEBM)

**Response (201 Created):**
```json
{
  "id": "speaker-1-id",
  "name": "Speaker 1",
  "voice_file": "uuid.wav",
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 3. Update Speaker

**PUT** `/api/v1/projects/{project_id}/speakers/{speaker_id}`

Update speaker details or voice sample.

**Form Data:**
- `name` (optional) - New speaker name
- `voice_file` (optional) - New audio file

**Response (200 OK):**
```json
{
  "id": "speaker-1-id",
  "name": "Updated Speaker Name",
  "voice_file": "new-uuid.wav",
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 4. Delete Speaker

**DELETE** `/api/v1/projects/{project_id}/speakers/{speaker_id}`

Delete a speaker and its voice sample.

**Response (200 OK):**
```json
{
  "message": "Speaker deleted successfully"
}
```

### 5. Get Speaker Voice File

**GET** `/api/v1/projects/{project_id}/speakers/{speaker_id}/voice`

Download the speaker's voice file.

**Response (200 OK):**
- Content-Type: `audio/wav` (or appropriate audio type)
- Binary audio data

---

# Dialog Sessions API

## Overview

The Dialog Sessions API manages dialog scripts within a project. Each session contains a multi-speaker dialog script.

## Dialog Format

```
Speaker 1: First line

Speaker 2: Second line

Speaker 1: Can appear multiple times
```

**Critical**: Speaker names must match exactly with uploaded speakers.

## Endpoints

### 1. List Sessions

**GET** `/api/v1/projects/{project_id}/sessions`

Get all dialog sessions for a project.

**Response (200 OK):**
```json
{
  "sessions": [
    {
      "id": "session-id",
      "name": "My Dialog",
      "script_file": "uuid.txt",
      "created_at": "2025-12-02T10:00:00Z"
    }
  ]
}
```

### 2. Create Session

**POST** `/api/v1/projects/{project_id}/sessions`

Create a new dialog session.

**Request Body:**
```json
{
  "name": "My Dialog",
  "script": "Speaker 1: Hello\n\nSpeaker 2: Hi there"
}
```

**Response (201 Created):**
```json
{
  "id": "session-id",
  "name": "My Dialog",
  "script_file": "uuid.txt",
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 3. Get Session

**GET** `/api/v1/projects/{project_id}/sessions/{session_id}`

Get session details and script content.

**Response (200 OK):**
```json
{
  "id": "session-id",
  "name": "My Dialog",
  "script": "Speaker 1: Hello\n\nSpeaker 2: Hi there",
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 4. Update Session

**PUT** `/api/v1/projects/{project_id}/sessions/{session_id}`

Update session name or script content.

**Request Body:**
```json
{
  "name": "Updated Dialog Name",
  "script": "Speaker 1: Updated script..."
}
```

**Response (200 OK):**
```json
{
  "id": "session-id",
  "name": "Updated Dialog Name",
  "script_file": "uuid.txt",
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 5. Delete Session

**DELETE** `/api/v1/projects/{project_id}/sessions/{session_id}`

Delete a dialog session.

**Response (200 OK):**
```json
{
  "message": "Session deleted successfully"
}
```

---

# Generation API

## Overview

The Generation API handles voice generation requests. It uses a shared task manager with training (only one task can run at a time).

## Endpoints

### 1. Start Generation

**POST** `/api/v1/projects/{project_id}/generate`

Start a new voice generation task.

**Request Body:**
```json
{
  "session_id": "session-id",
  "number_of_layers": 12,
  "temperature": 0.7,
  "top_k": 50,
  "top_p": 0.95
}
```

**Response (201 Created):**
```json
{
  "message": "Generation started successfully",
  "request_id": "generation-request-id",
  "status": "pending"
}
```

**Response (409 Conflict):**
```json
{
  "error": "Conflict",
  "message": "Task manager is busy"
}
```

### 2. Get Generation Status

**GET** `/api/v1/projects/{project_id}/generate/current`

Get current generation task status with live progress.

**Response (200 OK, generation in progress):**
```json
{
  "request_id": "generation-request-id",
  "status": "processing",
  "progress": 45.5,
  "session_name": "My Dialog",
  "created_at": "2025-12-02T10:00:00Z"
}
```

**Response (200 OK, no active generation):**
```json
{
  "message": "No active generation",
  "status": null
}
```

### 3. List Generation History

**GET** `/api/v1/projects/{project_id}/generate/history`

Get all generation requests for a project.

**Response (200 OK):**
```json
{
  "generations": [
    {
      "request_id": "generation-request-id",
      "session_id": "session-id",
      "status": "completed",
      "output_file": "uuid.wav",
      "created_at": "2025-12-02T10:00:00Z",
      "completed_at": "2025-12-02T10:05:00Z"
    }
  ]
}
```

### 4. Download Generated Audio

**GET** `/api/v1/projects/{project_id}/generate/{request_id}/audio`

Download the generated audio file.

**Response (200 OK):**
- Content-Type: `audio/wav`
- Binary audio data

**Response (404 Not Found):**
```json
{
  "error": "Not Found",
  "message": "Generation not found or not completed"
}
```

### 5. Delete Generation

**DELETE** `/api/v1/projects/{project_id}/generate/{request_id}`

Delete a generation request and its output file.

**Response (200 OK):**
```json
{
  "message": "Generation deleted successfully"
}
```

## Generation Status Values

| Status | Description |
|--------|-------------|
| `pending` | Task created, waiting to start |
| `processing` | Generation in progress |
| `completed` | Generation finished successfully |
| `failed` | Generation failed with error |

---

# Dataset Management API

## Overview

The Dataset Management API provides endpoints for managing datasets and dataset items. Datasets contain collections of text-audio pairs used for training. All endpoints are project-scoped.

## Endpoints

### 1. List Datasets

**GET** `/api/v1/projects/{project_id}/datasets`

Get all datasets for a project.

**Response (200 OK):**
```json
{
  "datasets": [
    {
      "id": "dataset-id",
      "name": "My Dataset",
      "item_count": 150,
      "created_at": "2025-12-02T10:00:00Z"
    }
  ]
}
```

### 2. Create Dataset

**POST** `/api/v1/projects/{project_id}/datasets`

Create a new dataset.

**Request Body:**
```json
{
  "name": "My New Dataset"
}
```

**Response (201 Created):**
```json
{
  "id": "dataset-id",
  "name": "My New Dataset",
  "item_count": 0,
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 3. Update Dataset

**PUT** `/api/v1/projects/{project_id}/datasets/{dataset_id}`

Update dataset name.

**Request Body:**
```json
{
  "name": "Updated Dataset Name"
}
```

**Response (200 OK):**
```json
{
  "id": "dataset-id",
  "name": "Updated Dataset Name",
  "item_count": 150,
  "created_at": "2025-12-02T10:00:00Z"
}
```

### 4. Delete Dataset

**DELETE** `/api/v1/projects/{project_id}/datasets/{dataset_id}`

Delete a dataset and all its items.

**Response (200 OK):**
```json
{
  "message": "Dataset deleted successfully"
}
```

### 5. Export Dataset

**GET** `/api/v1/projects/{project_id}/datasets/{dataset_id}/export`

Export dataset as ZIP file.

**Response (200 OK):**
- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename="{dataset-name}.zip"`
- Binary ZIP data

**ZIP Structure:**
```
datasets.jsonl              # JSONL file with all items
audio/                      # Audio files directory
  ├── {uuid}.wav
  └── ...
voice_prompts/              # Voice prompt files directory
  ├── {uuid}.wav
  └── ...
```

### 6. Import Dataset

**POST** `/api/v1/projects/{project_id}/datasets/import`

Import dataset from ZIP file.

**Form Data:**
- `file` (required) - ZIP file with dataset structure
- `dataset_id` (required) - Target dataset ID to import into

**Response (200 OK):**
```json
{
  "message": "Dataset imported successfully",
  "item_count": 150
}
```

**Status Codes:**
- `200 OK` - Import successful
- `400 Bad Request` - Invalid ZIP structure or missing dataset
- `404 Not Found` - Project or dataset not found
- `500 Internal Server Error` - Server error

---

## Dataset Item Management

Dataset items contain text-audio pairs with voice prompts for training.

### Base URL

```
http://localhost:9527/api/v1/projects/{project_id}/datasets/{dataset_id}/items
```

## Data Models

### DatasetItem

```json
{
  "text": "string",
  "audio": "filename.wav",
  "voice_prompts": ["prompt1.wav", "prompt2.wav"]
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

See detailed endpoint documentation below starting with "### 1. List Dataset Items".

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

Create and start a new training job. Returns 409 if task manager is busy or job name is duplicate.

**IMPORTANT**: The backend automatically calculates the `output_dir` field based on the job name:
- Path format: `{workspace}/{project}/training/lora_output/{job_name}`
- Job names must be unique within a project
- Any `output_dir` value in the request will be overwritten

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
    "output_dir": "ignored-will-be-overwritten"
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

**Response (409 Conflict - Duplicate Job Name):**
```json
{
  "error": "Conflict",
  "message": "Job name already exists. Please choose a unique name for your training job"
}
```

**Status Codes:**
- `201 Created` - Training job created and started
- `400 Bad Request` - Invalid configuration or missing fields
- `404 Not Found` - Project not found
- `409 Conflict` - Task manager is busy OR job name already exists
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


