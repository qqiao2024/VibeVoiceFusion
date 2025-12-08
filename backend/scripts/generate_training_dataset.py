#!/usr/bin/env python3
"""
Generate training dataset for VibeVoice from audio files and metadata.

This script processes audio files with their metadata (text transcriptions and dialect information)
to generate a dataset.jsonl file and a bash script for copying the selected audio files.
"""

import argparse
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Set, Tuple


def parse_metadata_file(file_path: str, num_columns: int = 2) -> Dict[str, str]:
    """
    Parse a metadata file with two columns separated by whitespace.

    Args:
        file_path: Path to the metadata file
        num_columns: Expected number of columns (default: 2)

    Returns:
        Dictionary mapping first column (category and person id) to second column (text contents or type of dialect )
    """
    metadata = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == num_columns:
                metadata[parts[0]] = parts[1]
    return metadata


def parse_filename(filename: str) -> Tuple[str, str]:
    """
    Parse audio filename to extract category and person ID.

    Args:
        filename: Audio filename (e.g., "1000001_0b1a33a3") 

    Returns:
        Tuple of (category, person_id)
    """
    parts = filename.split('_')
    if len(parts) >= 2:
        return parts[0], parts[1]
    return parts[0], ""


def group_by_person_and_dialect(
    utt2dialect: Dict[str, str],
    text_dict: Dict[str, str]
) -> Dict[str, Dict[str, List[str]]]:
    """
    Group audio files by dialect and voice ID.

    Args:
        utt2dialect: Mapping of utterance ID to dialect, category plus voice ID mapping to dialect
        text_dict: Mapping of utterance ID to text, category plus voice ID mapping to text

    Returns:
        Nested dictionary: {dialect: {category: [utterance_ids]}}, file_name in Audio/1029757/phase1/is utt_id
    """
    grouped = {}

    for utt_id in utt2dialect:
        if utt_id not in text_dict:
            continue

        dialect = utt2dialect[utt_id]
        category, voice_id = parse_filename(utt_id)

        if dialect not in grouped:
            grouped[dialect] = {}
        if category not in grouped[dialect]:
            grouped[dialect][category] = []

        grouped[dialect][category].append(utt_id)

    return grouped


def select_voice_prompts(
    audio_utt_id: str,
    dialect: str,
    category_id: str,
    grouped_data: Dict[str, Dict[str, List[str]]],
    num_prompts: int
) -> List[str]:
    """
    Select voice prompt files with the same dialect but different from audio.

    Args:
        audio_utt_id: The audio utterance ID
        dialect: The dialect of the audio
        voice_id: The voice ID of the audio
        grouped_data: Grouped audio data
        num_prompts: Number of voice prompts to select

    Returns:
        List of selected voice prompt utterance IDs
    """
    if dialect not in grouped_data:
        return []
    
    # Collect all utterances with same dialect
    candidates = []
    for cate_id, utts in grouped_data[dialect].items():
        if cate_id != category_id:
            continue
        for utt in utts:
            if utt != audio_utt_id:  # Chose same person voice
                candidates.append(utt)

    if not candidates:
        print(f"Warning: No candidates found for dialect '{dialect}' and person '{category_id}', audio_utt_id '{audio_utt_id}'")
        return []

    # Randomly select voice prompts
    num_to_select = min(num_prompts, len(candidates))
    return random.sample(candidates, num_to_select)


def generate_dataset(
    audio_root: str,
    text_path: str,
    utt2dialect_path: str,
    output_path: str,
    phase: str = "phase1",
    selected_dialect: str = None,
    max_files: int = 5000,
    num_voice_prompts: int = 2,
    speaker_name: str = "Speaker 0"
) -> Tuple[List[Dict], Set[str]]:
    """
    Generate dataset from audio files and metadata.

    Args:
        audio_root: Root directory containing audio files
        text_path: Path to text metadata file
        utt2dialect_path: Path to dialect metadata file
        output_path: Path to output directory
        phase: Phase subdirectory name (default: "phase1")
        selected_dialect: Specific dialect to filter (None for all)
        max_files: Maximum number of files to select (-1 for unlimited)
        num_voice_prompts: Number of voice prompt files per sample
        speaker_name: Speaker name to use in output

    Returns:
        Tuple of (dataset entries, set of all audio files used)
    """
    # Parse metadata files
    print("Parsing metadata files...")
    utt2dialect = parse_metadata_file(utt2dialect_path)
    text_dict = parse_metadata_file(text_path)

    # Group by person and dialect
    print("Grouping audio files by dialect and person...")
    grouped_data = group_by_person_and_dialect(utt2dialect, text_dict)

    # Filter by dialect if specified
    if selected_dialect:
        if selected_dialect not in grouped_data:
            print(f"Warning: Dialect '{selected_dialect}' not found in data")
            return [], set()
        dialects_to_process = [selected_dialect]
    else:
        dialects_to_process = list(grouped_data.keys())

    print(f"Processing dialects: {dialects_to_process}, total {len(grouped_data[selected_dialect])} dialects")

    # Collect all valid utterances
    valid_utterances = []
    for dialect in dialects_to_process:
        for category_id, utts in grouped_data[dialect].items():
            for utt_id in utts:
                if utt_id in text_dict:
                    valid_utterances.append((utt_id, dialect, category_id))

    print(f"Found {len(valid_utterances)} valid utterances")

    # Limit number of files if specified
    random.shuffle(valid_utterances)

    # Generate dataset entries
    dataset = []
    all_audio_files = set()

    total_utterances = len(valid_utterances)
    print("\nProcessing audio files...")

    rec_num = 0

    for idx, (utt_id, dialect, category_id) in enumerate(valid_utterances, 1):
        # Display progress every 100 files or at the last file
        if idx % 100 == 0 or idx == total_utterances:
            print(f"Progress: {idx}/{total_utterances} ({idx*100//total_utterances}%) - Generated {len(dataset)} entries", end='\r')

        # Select voice prompts
        voice_prompts = select_voice_prompts(
            utt_id, dialect, category_id, grouped_data, num_voice_prompts
        )

        if not voice_prompts:
            if idx % 100 == 0 or idx == total_utterances:
                print()  # New line before warning
            # print(f"Warning: No voice prompts found for {utt_id}, skipping")
            continue

        # Parse category from filename
        category, _ = parse_filename(utt_id)

        # Build paths relative to dataset output directory
        audio_path = f"./audio/{utt_id}.wav"
        voice_prompt_paths = [f"./voice_prompts/{vp}.wav" for vp in voice_prompts]

        # Create dataset entry
        entry = {
            "text": f"{speaker_name}: {text_dict[utt_id]}",
            "audio": audio_path,
            "voice_prompts": voice_prompt_paths
        }
        dataset.append(entry)

        # Track all audio files for copy script
        all_audio_files.add((utt_id, category, phase, 'audio'))
        for vp in voice_prompts:
            vp_category, _ = parse_filename(vp)
            all_audio_files.add((vp, vp_category, phase, 'voice_prompts'))

        rec_num += 1
        if max_files is not None and rec_num >= max_files:
            break

    if max_files > 0:
        dataset = dataset[:max_files]
        print(f"Limited to {len(dataset)} utterances")
    print()  # New line after progress
    print(f"Generated {len(dataset)} dataset entries")
    return dataset, all_audio_files


def write_dataset_jsonl(dataset: List[Dict], output_path: str):
    """Write dataset to JSONL file."""
    output_file = os.path.join(output_path, "datasets.jsonl")
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    print(f"Written dataset to {output_file}")


def generate_copy_script(
    audio_files: Set[Tuple[str, str, str, str]],
    audio_root: str,
    output_path: str
) -> str:
    """
    Generate bash script to copy audio files.

    Args:
        audio_files: Set of (utt_id, category, phase, audio) tuples
        audio_root: Root directory of source audio files
        output_path: Output dataset directory

    Returns:
        Path to generated script
    """
    script_path = os.path.join(output_path, "copy_audio_files.sh")

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write("#!/bin/bash\n")
        f.write("# Script to copy audio files for training dataset\n\n")
        f.write("set -e\n\n")

        # Create directories
        f.write("# Create audio directories\n")
        f.write(f'mkdir -p "{output_path}/audio"\n')
        f.write(f'mkdir -p "{output_path}/voice_prompts"\n\n')

        # Sort audio files for consistent output
        sorted_files = sorted(audio_files)

        f.write("# Copy audio files\n")
        for utt_id, category, phase, audio_type in sorted_files:
            src_path = os.path.join(audio_root, category, phase, f"{utt_id}.wav")
            dst_path = os.path.join(output_path, audio_type, f"{utt_id}.wav")
            f.write(f'cp "{src_path}" "{dst_path}"\n')

        f.write('\necho "Audio files copied successfully!"\n')

    # Make script executable
    os.chmod(script_path, 0o755)
    print(f"Generated copy script: {script_path}")
    return script_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate training dataset for VibeVoice from audio files and metadata"
    )

    parser.add_argument(
        "--audio-path",
        required=True,
        help="Root path of all audio files (contains category subdirectories)"
    )

    parser.add_argument(
        "--text-path",
        required=True,
        help="Path to text metadata file"
    )

    parser.add_argument(
        "--utt2dialect-path",
        required=True,
        help="Path to utt2subdialect metadata file"
    )

    parser.add_argument(
        "--phase",
        default="phase1",
        help="Phase subdirectory name (default: phase1)"
    )

    parser.add_argument(
        "--dialect",
        default=None,
        help="Select specific dialect (e.g., 'Mandarin'). If omitted, all dialects are selected."
    )

    parser.add_argument(
        "--max-files",
        type=int,
        default=5000,
        help="Maximum number of audio files to select (-1 for unlimited, default: 5000)"
    )

    parser.add_argument(
        "--output-path",
        default=".",
        help="Path to output dataset directory (default: current directory)"
    )

    parser.add_argument(
        "--num-voice-prompts",
        type=int,
        default=2,
        help="Number of voice prompt files per sample (default: 2)"
    )

    parser.add_argument(
        "--speaker-name",
        default="Speaker 0",
        help="Speaker name to use in dataset (default: 'Speaker 0')"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)

    # Validate paths
    if not os.path.exists(args.audio_path):
        print(f"Error: Audio path does not exist: {args.audio_path}")
        return 1

    if not os.path.exists(args.text_path):
        print(f"Error: Text metadata file does not exist: {args.text_path}")
        return 1

    if not os.path.exists(args.utt2dialect_path):
        print(f"Error: Dialect metadata file does not exist: {args.utt2dialect_path}")
        return 1

    # Create output directory
    os.makedirs(args.output_path, exist_ok=True)

    # Generate dataset
    print("\nGenerating dataset...")
    print(f"Audio root: {args.audio_path}")
    print(f"Text metadata: {args.text_path}")
    print(f"Dialect metadata: {args.utt2dialect_path}")
    print(f"Phase: {args.phase}")
    print(f"Selected dialect: {args.dialect or 'All'}")
    print(f"Max files: {args.max_files if args.max_files > 0 else 'Unlimited'}")
    print(f"Voice prompts per sample: {args.num_voice_prompts}")
    print(f"Output path: {args.output_path}")
    print(f"Speaker name: {args.speaker_name}")
    print()

    dataset, audio_files = generate_dataset(
        audio_root=args.audio_path,
        text_path=args.text_path,
        utt2dialect_path=args.utt2dialect_path,
        output_path=args.output_path,
        phase=args.phase,
        selected_dialect=args.dialect,
        max_files=args.max_files,
        num_voice_prompts=args.num_voice_prompts,
        speaker_name=args.speaker_name
    )

    if not dataset:
        print("Error: No dataset entries generated")
        return 1

    # Write dataset JSONL
    write_dataset_jsonl(dataset, args.output_path)

    # Generate copy script
    generate_copy_script(audio_files, args.audio_path, args.output_path)

    print("\n✓ Dataset generation completed successfully!")
    print(f"  - Dataset entries: {len(dataset)}")
    print(f"  - Total audio files: {len(audio_files)}")
    print("\nNext steps:")
    print(f"  1. Review {os.path.join(args.output_path, 'dataset.jsonl')}")
    print(f"  2. Run {os.path.join(args.output_path, 'copy_audio_files.sh')} to copy audio files")

    return 0


if __name__ == "__main__":
    exit(main())
