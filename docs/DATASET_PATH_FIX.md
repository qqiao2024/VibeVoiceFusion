# Dataset Path Format Fix

## Problem
The dataset management system was storing bare filenames in the `audio` and `voice_prompts` fields of `datasets.jsonl` files, but the training code expects relative paths.

### Before (Incorrect)
```json
{
  "text": "Sample text",
  "audio": "file.wav",
  "voice_prompts": ["prompt1.wav", "prompt2.wav"]
}
```

### After (Correct)
```json
{
  "text": "Sample text",
  "audio": "./audio/file.wav",
  "voice_prompts": ["./voice_prompts/prompt1.wav", "./voice_prompts/prompt2.wav"]
}
```

## Changes Made

### 1. Backend Service (`backend/services/dataset_service.py`)

#### Added Helper Method
- `_extract_filename_from_path()`: Extracts just the filename from a relative or absolute path

#### Updated Methods
- **`add_item()`** (lines 436-441): Now stores relative paths instead of filenames
- **`update_item()`** (lines 513, 544): Now stores relative paths for updated files
- **`delete_item()`** (lines 620-631): Extracts filename from relative path before deletion
- **`update_item()` cleanup** (lines 572-585): Extracts filename from old paths before deletion

### 2. Model Documentation (`backend/models/dataset.py`)
Updated DatasetItem docstrings to reflect the new relative path format.

### 3. Frontend Fix (`frontend/app/dataset/detail/page.tsx`)

#### Added Helper Function
- `extractFilename()`: Extracts just the filename from relative paths like `"./audio/file.wav"` → `"file.wav"`

#### Updated Functions
- **`getAudioUrl()`**: Now accepts path string and extracts filename before constructing API URL
- **`getVoicePromptUrl()`**: Now accepts path string and extracts filename before constructing API URL
- **DatasetItemRow rendering**: Passes extracted filenames for display instead of full paths

This fix resolves the audio player error: `NotSupportedError: The element has no supported sources`

### 4. Migration Script (`backend/scripts/migrate_dataset_paths.py`)
Created migration script that:
- Finds all `datasets.jsonl` files in the workspace
- Converts bare filenames to relative paths
- Performs atomic file updates (writes to temp file, then replaces)
- Reports migration results

## Migration

To migrate existing datasets, run:
```bash
python backend/scripts/migrate_dataset_paths.py
```

The script will automatically:
1. Find all datasets in `workspace/*/datasets/*/datasets.jsonl`
2. Convert filenames to relative paths
3. Report how many items were migrated in each dataset

## Why This Fix Is Important

The training code (`vibevoice/training/dataset.py`, lines 232-233 and 251-252) expects relative paths and prepends `dataset_root_path`:

```python
if self.dataset_root_path is not None and voice_prompts is not None:
    voice_prompts = [f"{self.dataset_root_path}/{str(vp)}" if not str(vp).startswith('/') else str(vp) for vp in voice_prompts]
```

With bare filenames, this would result in incorrect paths like:
- `dataset_root/file.wav` ❌

With relative paths, this correctly produces:
- `dataset_root/./audio/file.wav` ✓

## Backward Compatibility

The fix maintains backward compatibility:
- The `_extract_filename_from_path()` helper works with both formats
- Old datasets with bare filenames will continue to work after migration
- New datasets will automatically use the correct format

## Testing

All tests passed:
- ✓ Path format validation
- ✓ File existence verification
- ✓ Backend list_items operation
- ✓ Backend delete_item path extraction
- ✓ 20 dataset items migrated successfully (2 datasets)

## Files Modified

1. `backend/services/dataset_service.py` - Core backend fix
2. `backend/models/dataset.py` - Documentation update
3. `backend/scripts/migrate_dataset_paths.py` - New migration script
4. `frontend/app/dataset/detail/page.tsx` - Frontend fix to extract filenames from paths
5. `DATASET_PATH_FIX.md` - This documentation

## Notes

- The migration is idempotent - running it multiple times is safe
- Only paths that don't already start with `./` are modified
- Atomic file operations ensure no data loss during migration
- All existing dataset operations (add, update, delete, list) continue to work correctly
