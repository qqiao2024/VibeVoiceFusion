# Multi-Generation Frontend UI Design

This document outlines the frontend UI design for supporting multiple voice generations with one click.

## Overview

The multi-generation feature allows users to generate multiple audio outputs from the same dialog session with different random seeds in a single request. This is useful for:
- Comparing different voice variations
- Finding the best result among multiple attempts
- Batch production of voice content

### Key Design Principle

**Backend handles seed generation automatically.** The frontend:
1. Sends `batch_size` (number of generations) and initial `seeds` value
2. Backend uses the initial seed for the first generation
3. Backend generates new random seeds for subsequent generations (`random.randint(0, 2**64 - 1)`)
4. Frontend displays the actual seed from `GenerationItem.seeds` for each item

## Data Model Reference

### Backend Generation Model

```python
@dataclass
class GenerationItem:
    epoch_idx: int              # Batch index (0, 1, 2, ...)
    audio_path: str             # Path to generated audio file
    seeds: int                  # Random seed used for this item
    generation_time: float      # Time taken for generation in seconds
    prefilling_tokens: int      # Number of prefilling tokens
    total_tokens: int           # Total number of tokens generated
    generated_tokens: int       # Number of tokens generated
    audio_duration_seconds: float   # Duration of generated audio
    real_time_factor: float     # Real-time factor for generation speed
    current_step: int           # Current step in generation process
    total_steps: int            # Total steps in generation process

@dataclass
class GenerationDetails:
    scripts: List[str]
    unique_speaker_names: List[str]
    voice_sample: List[str]
    max_speaker_id: int
    preprocessing_duration: float
    generation_items: List[GenerationItem]  # List of all generation items

@dataclass
class Generation:
    # ... existing fields ...
    is_multi_generation: bool = False       # Flag for multi-generation
    fix_seed: bool = False                  # Flag to fix the random seed
    current_batch_index: int = None         # Current batch index (0-based)
    batch_size: int = None                  # Total number of batches
```

---

## 1. Generation Form Changes

### New Form Fields

Add a new section between the Seeds field and Offloading Configuration:

```
+------------------------------------------------------------------+
| Multi-Generation Settings                                         |
+------------------------------------------------------------------+
| [ ] Enable Multi-Generation                                       |
|                                                                   |
| (When enabled:)                                                   |
|                                                                   |
| Number of Generations: [____5____] (1-20)                        |
|   Generate multiple audio variations with different random seeds  |
|                                                                   |
| Initial Seed: [____42____] [Dice Icon]                           |
|   The first generation uses this seed. Backend automatically      |
|   generates new random seeds for subsequent generations.          |
+------------------------------------------------------------------+
```

### Form Field Specifications

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `enable_multi_generation` | boolean | false | - | Toggle multi-generation mode |
| `batch_size` | number | 5 | 1-20 | Number of audio files to generate |
| `seeds` | number | random | 0-2^64 | Initial seed for first generation |

### Seed Generation Logic (Backend)

The backend handles seed generation automatically:
- First generation uses the `seeds` value from the request
- After each generation, backend generates a new random seed: `random.randint(0, 2**64 - 1)`
- Each `GenerationItem.seeds` stores the actual seed used for that item
- Frontend simply displays the `seeds` value from each `GenerationItem`

```python
# Backend logic (inference.py:214)
for batch_idx in range(batch_size):
    # Generate with current self.seeds
    ...
    # After generation, create new random seed for next batch
    self.seeds = random.randint(0, 2**64 - 1)
```

---

## 2. Current Generation Progress Display

### Single Generation (Current Behavior)

No changes to existing single-generation progress display.

### Multi-Generation Progress

```
+------------------------------------------------------------------+
| Current Generation                                    [Spinner]   |
+------------------------------------------------------------------+
| Status: Inferencing                                               |
| Session: dialogue-session-1                                       |
| Request ID: abc123...                                             |
+------------------------------------------------------------------+
| Overall Progress                                                  |
|                                                                   |
| Generation 2 of 5                                                 |
| [========================================--------------------] 40% |
|                                                                   |
| Current Item Progress                                             |
| [====================------------------------------] Step 45/100  |
+------------------------------------------------------------------+
| Generated Items                                       [Collapse]  |
+------------------------------------------------------------------+
| #1  Seed: 42     Duration: 12.5s   RTF: 0.85x     [Play] [Save]  |
|     audio_abc123_0.wav                                            |
+------------------------------------------------------------------+
| #2  Seed: 43     [Generating... Step 45/100]                     |
|     [====================--------------------------] 45%          |
+------------------------------------------------------------------+
| #3  Seed: 44     [Pending]                                        |
| #4  Seed: 45     [Pending]                                        |
| #5  Seed: 46     [Pending]                                        |
+------------------------------------------------------------------+
| Model Settings                                                    |
| Model: bf16  |  CFG: 1.3  |  Attention: sdpa                     |
+------------------------------------------------------------------+
```

### Progress Component Breakdown

#### Overall Progress Bar
- Shows `current_batch_index + 1` of `batch_size`
- Percentage: `((current_batch_index + completed_percentage_of_current) / batch_size) * 100`

#### Generated Items List
- Collapsible section showing all generation items
- Completed items: Show audio player, download button, metrics
- Current item: Show step progress bar
- Pending items: Show "Pending" badge with seed number

#### Item States

| State | Visual | Actions Available |
|-------|--------|-------------------|
| Pending | Gray badge, seed number | None |
| Generating | Blue progress bar, step X/Y | None |
| Completed | Green checkmark, metrics | Play, Download |
| Failed | Red badge, error message | Retry (future) |

---

## 3. Generation History Page Design

### List View Item (Collapsed)

#### Single Generation (No Change)
```
+------------------------------------------------------------------+
| [x] | [Completed] [bf16]                                          |
|     | Session: dialogue-session-1                                 |
|     | Created: 2025-12-16 10:30:00                                |
|     | [========================================] 100%              |
|     |                                    [Details] [Download] [X] |
+------------------------------------------------------------------+
```

#### Multi-Generation (New Design)
```
+------------------------------------------------------------------+
| [x] | [Completed] [bf16] [Multi: 5 items]                         |
|     | Session: dialogue-session-1                                 |
|     | Created: 2025-12-16 10:30:00                                |
|     | Total Duration: 62.5s | Avg RTF: 0.82x | Total Time: 51.2s  |
|     |                                    [Details] [Download All] |
+------------------------------------------------------------------+
```

### Multi-Generation Badge

```html
<span class="px-2 py-1 rounded text-xs font-medium bg-indigo-100 text-indigo-800">
  Multi: {batch_size} items
</span>
```

### Expanded Details View

#### Summary Section
```
+------------------------------------------------------------------+
| Multi-Generation Summary                                          |
+------------------------------------------------------------------+
| Items Generated: 5/5                                              |
| Seed Mode: Different Seeds (Base: 42)                             |
| Seeds Used: 42, 43, 44, 45, 46                                    |
+------------------------------------------------------------------+
| Aggregate Statistics                                              |
+------------------------------------------------------------------+
|  Total Audio     |  Total Gen Time  |  Avg RTF   |  Avg Duration |
|     62.5s        |      51.2s       |   0.82x    |    12.5s      |
+------------------------------------------------------------------+
```

#### Individual Items Grid
```
+------------------------------------------------------------------+
| Generated Audio Files                                [Expand All] |
+------------------------------------------------------------------+
| #1 | Seed: 42 | Duration: 12.3s | RTF: 0.85x | Time: 10.5s       |
|    | [Audio Player ===============================]  [Download]   |
+------------------------------------------------------------------+
| #2 | Seed: 43 | Duration: 12.8s | RTF: 0.78x | Time: 10.0s       |
|    | [Audio Player ===============================]  [Download]   |
+------------------------------------------------------------------+
| #3 | Seed: 44 | Duration: 12.1s | RTF: 0.83x | Time: 10.1s       |
|    | [Audio Player ===============================]  [Download]   |
+------------------------------------------------------------------+
| #4 | Seed: 45 | Duration: 12.5s | RTF: 0.81x | Time: 10.3s       |
|    | [Audio Player ===============================]  [Download]   |
+------------------------------------------------------------------+
| #5 | Seed: 46 | Duration: 12.8s | RTF: 0.84x | Time: 10.3s       |
|    | [Audio Player ===============================]  [Download]   |
+------------------------------------------------------------------+
```

### Download Options for Multi-Generation

| Action | Behavior |
|--------|----------|
| Download All | Downloads a ZIP file containing all audio files |
| Download Individual | Downloads single audio file |

---

## 4. Component Architecture

### New Components

```
frontend/components/
├── GenerationForm.tsx           # Modified: Add multi-gen settings
├── CurrentGeneration.tsx        # Modified: Support multi-gen progress
├── GenerationHistory.tsx        # Modified: Support multi-gen display
├── MultiGenerationProgress.tsx  # NEW: Progress for multi-generation
├── GenerationItemCard.tsx       # NEW: Individual item display
└── GenerationSummary.tsx        # NEW: Aggregate statistics
```

### Component Hierarchy

```
GenerateVoicePage
├── GenerationHistory
│   └── GenerationHistoryItem
│       ├── (single) GenerationDetails
│       └── (multi) MultiGenerationDetails
│           ├── GenerationSummary
│           └── GenerationItemCard[]
└── CurrentGeneration / GenerationForm
    └── (if multi) MultiGenerationProgress
        └── GenerationItemCard[]
```

---

## 5. TypeScript Type Updates

### Updated Generation Interface

```typescript
// frontend/types/generation.ts

export interface GenerationItem {
  epoch_idx: number;
  audio_path: string;
  seeds: number;
  generation_time: number;
  prefilling_tokens?: number;
  total_tokens?: number;
  generated_tokens?: number;
  audio_duration_seconds?: number;
  real_time_factor?: number;
  current_step?: number;
  total_steps?: number;
}

export interface GenerationDetails {
  scripts?: string[];
  unique_speaker_names?: string[];
  voice_sample?: string[];
  max_speaker_id?: number;
  preprocessing_duration?: number;
  generation_items?: GenerationItem[];
  // ... existing fields
}

export interface Generation {
  // ... existing fields
  is_multi_generation: boolean;
  fix_seed: boolean;
  current_batch_index: number | null;
  batch_size: number | null;
}

export interface CreateGenerationRequest {
  // ... existing fields
  batch_size?: number;        // Number of generations (1-20), default 1
}
```

---

## 6. API Changes Required

### Create Generation Request

```typescript
// POST /api/v1/projects/{project_id}/generation/current
{
  "dialog_session_id": "uuid",
  "seeds": 42,              // Initial seed for first generation
  "cfg_scale": 1.3,
  "model_dtype": "bf16",
  "batch_size": 5           // NEW: Number of generations (default: 1)
}
```

**Note:** The backend automatically generates new random seeds for each subsequent generation after the first one. The actual seed used for each item is stored in `GenerationItem.seeds`.

### Download All Endpoint

```
GET /api/v1/projects/{project_id}/generations/{request_id}/download-all
Response: ZIP file containing all audio files
```

---

## 7. i18n Keys Required

```json
{
  "generation": {
    "multiGeneration": "Multi-Generation",
    "enableMultiGeneration": "Enable Multi-Generation",
    "numberOfGenerations": "Number of Generations",
    "numberOfGenerationsDescription": "Generate multiple audio variations with different random seeds",
    "initialSeed": "Initial Seed",
    "initialSeedDescription": "The first generation uses this seed. Backend automatically generates new random seeds for subsequent generations.",
    "multiGenerationBadge": "Multi: {count} items",
    "overallProgress": "Overall Progress",
    "generationXOfY": "Generation {current} of {total}",
    "currentItemProgress": "Current Item Progress",
    "generatedItems": "Generated Items",
    "pending": "Pending",
    "generating": "Generating...",
    "aggregateStatistics": "Aggregate Statistics",
    "totalAudioDuration": "Total Audio Duration",
    "totalGenerationTime": "Total Generation Time",
    "averageRTF": "Average RTF",
    "averageDuration": "Average Duration",
    "seedsUsed": "Seeds Used",
    "downloadAll": "Download All",
    "expandAll": "Expand All",
    "collapseAll": "Collapse All",
    "itemNumber": "#{number}",
    "seedLabel": "Seed: {seed}"
  }
}
```

---

## 8. Visual Design Guidelines

### Color Coding

| Element | Color | Usage |
|---------|-------|-------|
| Multi-gen badge | Indigo (`bg-indigo-100 text-indigo-800`) | Identify multi-generation entries |
| Pending items | Gray (`bg-gray-100 text-gray-600`) | Items waiting to be processed |
| Current item | Blue (`bg-blue-100 text-blue-800`) | Item currently being generated |
| Completed items | Green (`bg-green-50 border-green-200`) | Successfully generated items |
| Failed items | Red (`bg-red-50 border-red-200`) | Items that failed |

### Layout Guidelines

1. **Information Hierarchy**
   - Overall progress first (most important during generation)
   - Individual items collapsible (detail on demand)
   - Summary statistics prominent for completed generations

2. **Progressive Disclosure**
   - List view: Show only essential info (count, total duration, avg RTF)
   - Expanded view: Show all items with full details
   - Each item expandable for detailed metrics

3. **Consistent Spacing**
   - Card padding: `p-4`
   - Item gaps: `gap-2` or `gap-4`
   - Section dividers: `border-t border-gray-200`

---

## 9. Implementation Priority

### Phase 1: Core Functionality
1. Update TypeScript types for multi-generation
2. Modify GenerationForm to add multi-gen settings
3. Update CurrentGeneration to show multi-gen progress
4. Update GenerationHistory for multi-gen list items

### Phase 2: Enhanced Display
5. Create GenerationItemCard component
6. Create GenerationSummary component
7. Implement collapsible items list
8. Add aggregate statistics calculation

### Phase 3: Download & Polish
9. Implement "Download All" functionality
10. Add i18n translations
11. Testing and edge case handling
12. Performance optimization for large batch sizes

---

## 10. Edge Cases & Considerations

### Edge Cases to Handle

1. **Partial Completion**: Some items succeed, some fail
   - Show mixed status in summary
   - Allow download of completed items

2. **Large Batch Sizes**: 15-20 items
   - Implement virtual scrolling for item list
   - Show "Show more" button instead of all items

3. **OOM Failure Mid-Generation**
   - Save completed items
   - Show clear error state
   - Allow download of completed items

4. **Page Navigation During Generation**
   - Polling continues for active generation
   - State persisted in context

### Performance Considerations

1. **Audio Player Memory**: Don't load all audio files at once
   - Load on demand when expanded
   - Dispose when collapsed

2. **Progress Updates**: Throttle UI updates
   - Update progress bar at most every 500ms
   - Batch state updates

3. **Download All**: Use streaming for large files
   - Show download progress
   - Handle large ZIP files gracefully
