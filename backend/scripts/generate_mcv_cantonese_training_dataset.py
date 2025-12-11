#!/usr/bin/env python3
"""
Generate training dataset for VibeVoice from Mozilla Common Voice Cantonese (yue) audio files.

This script processes audio files from the Mozilla Common Voice Cantonese dataset
to generate a dataset.jsonl file and a bash script for copying the selected audio files.

Source: Mozilla Common Voice dataset (cv-corpus-23.0-2025-09-05/yue)
"""

import argparse
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Set, Tuple


def parse_tsv_file(file_path: str) -> List[Dict[str, str]]:
    """
    Parse the train.tsv metadata file from Mozilla Common Voice.

    The file format is TSV with columns:
    client_id, path, sentence_id, sentence, sentence_domain, up_votes, down_votes,
    age, gender, accents, variant, locale, segment

    Args:
        file_path: Path to the train.tsv file

    Returns:
        List of dictionaries with utterance metadata
    """
    utterances = []
    with open(file_path, 'r', encoding='utf-8') as f:
        # Read header line to get column names
        header = f.readline().strip().split('\t')
        
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) >= 4:  # At least need client_id, path, sentence_id, sentence
                utterance = {
                    'client_id': parts[0],  # Speaker ID (hashed)
                    'path': parts[1],       # Audio filename (e.g., common_voice_yue_32061964.mp3)
                    'sentence_id': parts[2] if len(parts) > 2 else '',
                    'sentence': parts[3] if len(parts) > 3 else '',
                    'up_votes': int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0,
                    'down_votes': int(parts[6]) if len(parts) > 6 and parts[6].isdigit() else 0,
                }
                # Only include utterances with positive net votes (quality filter)
                if utterance['sentence']:  # Must have transcription
                    utterances.append(utterance)
    
    return utterances


def group_by_speaker(utterances: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """
    Group utterances by speaker (client_id).

    Args:
        utterances: List of utterance dictionaries

    Returns:
        Dictionary mapping client_id to list of utterances
    """
    grouped = {}
    for utt in utterances:
        speaker_id = utt['client_id']
        if speaker_id not in grouped:
            grouped[speaker_id] = []
        grouped[speaker_id].append(utt)
    return grouped


def select_voice_prompts(
    current_utt: Dict[str, str],
    speaker_utterances: List[Dict[str, str]],
    num_prompts: int = 2
) -> List[Dict[str, str]]:
    """
    Select voice prompt files from the same speaker but different from current utterance.
    
    This function ensures:
    1. Voice prompts are from the SAME speaker as the current utterance (same person)
    2. Voice prompts are DIFFERENT files from the current audio file
    3. Voice prompts are unique (no duplicates among themselves)

    Args:
        current_utt: The current utterance dictionary
        speaker_utterances: List of all utterances from the SAME speaker
        num_prompts: Number of voice prompts to select (default: 2)

    Returns:
        List of selected voice prompt utterance dictionaries (all from same speaker, 
        all different from current_utt, all unique)
    """
    current_path = current_utt['path']
    current_speaker = current_utt['client_id']
    
    # Filter: must be same speaker AND different file from current audio
    candidates = [
        utt for utt in speaker_utterances 
        if utt['path'] != current_path and utt['client_id'] == current_speaker
    ]
    
    if not candidates:
        return []
    
    # Randomly select unique voice prompts (random.sample guarantees no duplicates)
    num_to_select = min(num_prompts, len(candidates))
    selected = random.sample(candidates, num_to_select)
    
    # Validation: ensure all selected are from same speaker and different from audio
    for vp in selected:
        assert vp['client_id'] == current_speaker, "Voice prompt must be from same speaker"
        assert vp['path'] != current_path, "Voice prompt must be different file from audio"
    
    # Validation: ensure no duplicates in voice prompts
    selected_paths = [vp['path'] for vp in selected]
    assert len(selected_paths) == len(set(selected_paths)), "Voice prompts must be unique"
    
    return selected


def generate_dataset(
    tsv_file_path: str,
    clips_dir: str,
    output_path: str,
    max_files: int = 5000,
    num_voice_prompts: int = 2,
    speaker_name: str = "Speaker 0",
    min_votes: int = 0
) -> Tuple[List[Dict], Set[Tuple[str, str, str]]]:
    """
    Generate dataset from Mozilla Common Voice Cantonese audio files.

    Args:
        tsv_file_path: Path to train.tsv metadata file
        clips_dir: Path to the clips directory containing audio files
        output_path: Path to output directory
        max_files: Maximum number of files to select (-1 for unlimited)
        num_voice_prompts: Number of voice prompt files per sample
        speaker_name: Speaker name to use in output
        min_votes: Minimum net votes (up_votes - down_votes) for quality filter

    Returns:
        Tuple of (dataset entries, set of all audio files used)
    """
    # Parse metadata file
    print("Parsing metadata file...")
    utterances = parse_tsv_file(tsv_file_path)
    print(f"Found {len(utterances)} utterances")

    # Filter by vote quality
    if min_votes > 0:
        utterances = [u for u in utterances if (u['up_votes'] - u['down_votes']) >= min_votes]
        print(f"After quality filter (min_votes={min_votes}): {len(utterances)} utterances")

    # Group by speaker
    print("Grouping utterances by speaker...")
    grouped_data = group_by_speaker(utterances)
    print(f"Found {len(grouped_data)} speakers")

    # Filter speakers with at least 3 utterances (1 for audio + 2 for voice prompts)
    valid_speakers = {k: v for k, v in grouped_data.items() if len(v) >= 3}
    print(f"Speakers with >= 3 utterances: {len(valid_speakers)}")

    # Collect all valid utterances
    valid_utterances = []
    for speaker_id, speaker_utts in valid_speakers.items():
        for utt in speaker_utts:
            valid_utterances.append((utt, speaker_utts))

    print(f"Found {len(valid_utterances)} valid utterances")

    # Shuffle for random selection
    random.shuffle(valid_utterances)

    # Generate dataset entries
    dataset = []
    all_audio_files = set()  # (path, audio_type)

    total_utterances = len(valid_utterances)
    print("\nProcessing audio files...")

    rec_num = 0
    for idx, (utt, speaker_utts) in enumerate(valid_utterances, 1):
        # Display progress every 100 files
        if idx % 100 == 0 or idx == total_utterances:
            print(f"Progress: {idx}/{total_utterances} ({idx*100//total_utterances}%) - Generated {len(dataset)} entries", end='\r')

        # Select voice prompts from same speaker
        voice_prompts = select_voice_prompts(utt, speaker_utts, num_voice_prompts)

        if len(voice_prompts) < num_voice_prompts:
            continue

        # Build paths relative to dataset output directory
        # Convert mp3 filename to use in output path
        audio_basename = os.path.splitext(utt['path'])[0]
        audio_path = f"./audio/{audio_basename}.mp3"
        
        voice_prompt_paths = []
        for vp in voice_prompts:
            vp_basename = os.path.splitext(vp['path'])[0]
            voice_prompt_paths.append(f"./voice_prompts/{vp_basename}.mp3")

        # Create dataset entry with fixed prefix "Speaker 0:"
        entry = {
            "text": f"{speaker_name}: {utt['sentence']}",
            "audio": audio_path,
            "voice_prompts": voice_prompt_paths
        }
        dataset.append(entry)

        # Track all audio files for copy script
        all_audio_files.add((utt['path'], 'audio'))
        for vp in voice_prompts:
            all_audio_files.add((vp['path'], 'voice_prompts'))

        rec_num += 1
        if max_files > 0 and rec_num >= max_files:
            break

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
    audio_files: Set[Tuple[str, str]],
    clips_dir: str,
    output_path: str
) -> str:
    """
    Generate bash script to copy audio files.

    Args:
        audio_files: Set of (filename, audio_type) tuples
        clips_dir: Path to the clips directory containing source audio files
        output_path: Output dataset directory

    Returns:
        Path to generated script
    """
    script_path = os.path.join(output_path, "copy_audio_files.sh")
    # Convert to absolute paths for portability
    clips_dir = os.path.abspath(clips_dir)
    output_path = os.path.abspath(output_path)

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write("#!/bin/bash\n")
        f.write("# Script to copy audio files for Mozilla Common Voice Cantonese training dataset\n")
        f.write("# Source: Mozilla Common Voice cv-corpus-23.0-2025-09-05/yue\n\n")
        f.write("set -e\n\n")

        # Create directories
        f.write("# Create audio directories\n")
        f.write(f'mkdir -p "{output_path}/audio"\n')
        f.write(f'mkdir -p "{output_path}/voice_prompts"\n\n')

        # Sort audio files for consistent output
        sorted_files = sorted(audio_files)

        f.write("# Copy audio files\n")
        f.write(f"# Total files to copy: {len(sorted_files)}\n\n")
        
        for filename, audio_type in sorted_files:
            src_path = os.path.join(clips_dir, filename)
            dst_path = os.path.join(output_path, audio_type, filename)
            f.write(f'cp "{src_path}" "{dst_path}"\n')

        f.write('\necho "Audio files copied successfully!"\n')
        f.write(f'echo "Total files copied: {len(audio_files)}"\n')

    # Make script executable
    os.chmod(script_path, 0o755)
    print(f"Generated copy script: {script_path}")
    return script_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate training dataset for VibeVoice from Mozilla Common Voice Cantonese corpus"
    )

    parser.add_argument(
        "--tsv-file",
        required=True,
        help="Path to train.tsv metadata file"
    )

    parser.add_argument(
        "--clips-dir",
        required=True,
        help="Path to the clips directory containing audio files"
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="Path to output dataset directory where datasets.jsonl and copy script will be generated"
    )

    parser.add_argument(
        "--max-number",
        type=int,
        default=5000,
        help="Maximum number of audio files to select (-1 for unlimited, default: 5000)"
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
        help="Speaker name prefix to use in dataset (default: 'Speaker 0')"
    )

    parser.add_argument(
        "--min-votes",
        type=int,
        default=0,
        help="Minimum net votes (up_votes - down_votes) for quality filter (default: 0)"
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
    if not os.path.exists(args.tsv_file):
        print(f"Error: TSV file does not exist: {args.tsv_file}")
        return 1

    if not os.path.exists(args.clips_dir):
        print(f"Error: Clips directory does not exist: {args.clips_dir}")
        return 1

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate dataset
    print("\nGenerating Mozilla Common Voice Cantonese training dataset...")
    print(f"TSV file: {args.tsv_file}")
    print(f"Clips directory: {args.clips_dir}")
    print(f"Max files: {args.max_number if args.max_number > 0 else 'Unlimited'}")
    print(f"Voice prompts per sample: {args.num_voice_prompts}")
    print(f"Min votes filter: {args.min_votes}")
    print(f"Output path: {args.output_dir}")
    print(f"Speaker name: {args.speaker_name}")
    print()

    dataset, audio_files = generate_dataset(
        tsv_file_path=args.tsv_file,
        clips_dir=args.clips_dir,
        output_path=args.output_dir,
        max_files=args.max_number,
        num_voice_prompts=args.num_voice_prompts,
        speaker_name=args.speaker_name,
        min_votes=args.min_votes
    )

    if not dataset:
        print("Error: No dataset entries generated")
        return 1

    # Write dataset JSONL
    write_dataset_jsonl(dataset, args.output_dir)

    # Generate copy script
    generate_copy_script(audio_files, args.clips_dir, args.output_dir)

    print("\n✓ Dataset generation completed successfully!")
    print(f"  - Dataset entries: {len(dataset)}")
    print(f"  - Total audio files: {len(audio_files)}")
    print("\nNext steps:")
    print(f"  1. Review {os.path.join(args.output_dir, 'datasets.jsonl')}")
    print(f"  2. Run {os.path.join(args.output_dir, 'copy_audio_files.sh')} to copy audio files")

    return 0


if __name__ == "__main__":
    exit(main())
