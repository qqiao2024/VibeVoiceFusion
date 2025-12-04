#!/usr/bin/env python3
"""
Migration script to fix audio and voice_prompts paths in existing datasets.jsonl files.

This script converts bare filenames to relative paths:
- "file.wav" -> "./audio/file.wav"
- ["prompt1.wav", "prompt2.wav"] -> ["./voice_prompts/prompt1.wav", "./voice_prompts/prompt2.wav"]
"""

import json
import sys
from pathlib import Path


def migrate_dataset_file(jsonl_path: Path) -> None:
    """
    Migrate a single datasets.jsonl file to use relative paths.

    Args:
        jsonl_path: Path to datasets.jsonl file
    """
    if not jsonl_path.exists():
        print(f"  ✗ File not found: {jsonl_path}")
        return

    # Read all lines
    lines = []
    modified_count = 0

    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    lines.append('')
                    continue

                try:
                    item = json.loads(line)
                    modified = False

                    # Fix audio path if it's just a filename
                    if 'audio' in item:
                        audio = item['audio']
                        if isinstance(audio, str) and not audio.startswith('./') and '/' not in audio:
                            item['audio'] = f"./audio/{audio}"
                            modified = True

                    # Fix voice_prompts paths if they're just filenames
                    if 'voice_prompts' in item:
                        voice_prompts = item['voice_prompts']
                        if isinstance(voice_prompts, list):
                            new_prompts = []
                            for vp in voice_prompts:
                                if isinstance(vp, str) and not vp.startswith('./') and '/' not in vp:
                                    new_prompts.append(f"./voice_prompts/{vp}")
                                    modified = True
                                else:
                                    new_prompts.append(vp)
                            item['voice_prompts'] = new_prompts

                    if modified:
                        modified_count += 1

                    lines.append(json.dumps(item, ensure_ascii=False))

                except json.JSONDecodeError as e:
                    print(f"  ✗ Invalid JSON at line {line_num}: {e}")
                    lines.append(line)

        # Write back atomically
        if modified_count > 0:
            temp_path = jsonl_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(line + '\n')
            temp_path.replace(jsonl_path)
            print(f"  ✓ Migrated {modified_count} items in {jsonl_path.parent.name}/datasets.jsonl")
        else:
            print(f"  ✓ No migration needed for {jsonl_path.parent.name}/datasets.jsonl")

    except Exception as e:
        print(f"  ✗ Error migrating {jsonl_path}: {e}")


def main():
    """Main migration function"""
    print("=== Dataset Path Migration Script ===\n")

    # Find workspace directory
    script_dir = Path(__file__).parent
    workspace_dir = script_dir.parent.parent / 'workspace'

    if not workspace_dir.exists():
        print(f"✗ Workspace directory not found: {workspace_dir}")
        return 1

    print(f"Searching for datasets in: {workspace_dir}\n")

    # Find all datasets.jsonl files
    jsonl_files = list(workspace_dir.glob('*/datasets/*/datasets.jsonl'))

    if not jsonl_files:
        print("No datasets.jsonl files found.")
        return 0

    print(f"Found {len(jsonl_files)} dataset(s) to migrate:\n")

    # Migrate each file
    for jsonl_path in jsonl_files:
        migrate_dataset_file(jsonl_path)

    print("\n=== Migration Complete ===")
    return 0


if __name__ == '__main__':
    sys.exit(main())
