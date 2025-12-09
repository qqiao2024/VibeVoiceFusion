#!/usr/bin/env python3
"""
Generate training dataset for VibeVoice from ASR-SCCantDuSC Cantonese audio files and metadata.

This script processes audio files from the ASR-SCCantDuSC (Scripted Chinese Cantonese Daily-use Speech Corpus)
to generate a dataset.jsonl file and a bash script for copying the selected audio files.

Source: ASR-SCCantDuSC corpus with UTTRANSINFO.txt metadata file.
"""

import argparse
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Set, Tuple


def parse_metadata_file(file_path: str) -> List[Dict[str, str]]:
    """
    Parse the UTTRANSINFO.txt metadata file.

    The file format is TSV with columns:
    CHANNEL, UTTRANS_ID, SPEAKER_ID, PROMPT, TRANSCRIPTION

    Args:
        file_path: Path to the UTTRANSINFO.txt file

    Returns:
        List of dictionaries with utterance metadata
    """
    utterances = []
    with open(file_path, 'r', encoding='utf-8') as f:
        # Skip header line
        header = f.readline().strip()
        
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) >= 5:
                utterance = {
                    'channel': parts[0],
                    'uttrans_id': parts[1],  # e.g., G0051_S0008.wav
                    'speaker_id': parts[2],  # e.g., G0051
                    'prompt': parts[3],
                    'transcription': parts[4]
                }
                utterances.append(utterance)
    
    return utterances


def group_by_speaker(utterances: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """
    Group utterances by speaker ID.

    Args:
        utterances: List of utterance dictionaries

    Returns:
        Dictionary mapping speaker_id to list of utterances
    """
    grouped = {}
    for utt in utterances:
        speaker_id = utt['speaker_id']
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

    Args:
        current_utt: The current utterance dictionary
        speaker_utterances: List of all utterances from the same speaker
        num_prompts: Number of voice prompts to select (default: 2)

    Returns:
        List of selected voice prompt utterance dictionaries
    """
    # Filter out the current utterance
    candidates = [utt for utt in speaker_utterances if utt['uttrans_id'] != current_utt['uttrans_id']]
    
    if not candidates:
        return []
    
    # Randomly select voice prompts
    num_to_select = min(num_prompts, len(candidates))
    return random.sample(candidates, num_to_select)


def get_wav_path(meta_file_path: str, speaker_id: str, uttrans_id: str) -> str:
    """
    Get the path to a WAV file relative to the metadata file location.

    Args:
        meta_file_path: Path to the UTTRANSINFO.txt file
        speaker_id: Speaker ID (e.g., G0051)
        uttrans_id: Utterance ID (e.g., G0051_S0008.wav)

    Returns:
        Absolute path to the WAV file
    """
    base_dir = os.path.dirname(meta_file_path)
    return os.path.join(base_dir, 'WAV', speaker_id, uttrans_id)


def generate_dataset(
    meta_file_path: str,
    output_path: str,
    max_files: int = 5000,
    num_voice_prompts: int = 2,
    speaker_name: str = "Speaker 0"
) -> Tuple[List[Dict], Set[Tuple[str, str, str]]]:
    """
    Generate dataset from Cantonese audio files and metadata.

    Args:
        meta_file_path: Path to UTTRANSINFO.txt metadata file
        output_path: Path to output directory
        max_files: Maximum number of files to select (-1 for unlimited)
        num_voice_prompts: Number of voice prompt files per sample
        speaker_name: Speaker name to use in output

    Returns:
        Tuple of (dataset entries, set of all audio files used)
    """
    # Parse metadata file
    print("Parsing metadata file...")
    utterances = parse_metadata_file(meta_file_path)
    print(f"Found {len(utterances)} utterances")

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
    all_audio_files = set()  # (speaker_id, uttrans_id, audio_type)

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
        uttrans_id_no_ext = os.path.splitext(utt['uttrans_id'])[0]
        audio_path = f"./audio/{uttrans_id_no_ext}.wav"
        
        voice_prompt_paths = []
        for vp in voice_prompts:
            vp_id_no_ext = os.path.splitext(vp['uttrans_id'])[0]
            voice_prompt_paths.append(f"./voice_prompts/{vp_id_no_ext}.wav")

        # Create dataset entry with fixed prefix "Speaker 0:"
        entry = {
            "text": f"{speaker_name}: {utt['transcription']}",
            "audio": audio_path,
            "voice_prompts": voice_prompt_paths
        }
        dataset.append(entry)

        # Track all audio files for copy script
        all_audio_files.add((utt['speaker_id'], utt['uttrans_id'], 'audio'))
        for vp in voice_prompts:
            all_audio_files.add((vp['speaker_id'], vp['uttrans_id'], 'voice_prompts'))

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
    audio_files: Set[Tuple[str, str, str]],
    meta_file_path: str,
    output_path: str
) -> str:
    """
    Generate bash script to copy audio files.

    Args:
        audio_files: Set of (speaker_id, uttrans_id, audio_type) tuples
        meta_file_path: Path to the UTTRANSINFO.txt metadata file
        output_path: Output dataset directory

    Returns:
        Path to generated script
    """
    script_path = os.path.join(output_path, "copy_audio_files.sh")
    # Convert to absolute paths for portability
    base_dir = os.path.dirname(os.path.abspath(meta_file_path))
    wav_dir = os.path.join(base_dir, 'WAV')
    output_path = os.path.abspath(output_path)

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write("#!/bin/bash\n")
        f.write("# Script to copy audio files for Cantonese training dataset\n")
        f.write("# Source: ASR-SCCantDuSC corpus\n\n")
        f.write("set -e\n\n")

        # Create directories
        f.write("# Create audio directories\n")
        f.write(f'mkdir -p "{output_path}/audio"\n')
        f.write(f'mkdir -p "{output_path}/voice_prompts"\n\n')

        # Sort audio files for consistent output
        sorted_files = sorted(audio_files)

        f.write("# Copy audio files\n")
        for speaker_id, uttrans_id, audio_type in sorted_files:
            src_path = os.path.join(wav_dir, speaker_id, uttrans_id)
            # Remove .wav extension from uttrans_id if present for consistency
            file_basename = uttrans_id if uttrans_id.endswith('.wav') else f"{uttrans_id}.wav"
            dst_path = os.path.join(output_path, audio_type, file_basename)
            f.write(f'cp "{src_path}" "{dst_path}"\n')

        f.write('\necho "Audio files copied successfully!"\n')
        f.write(f'echo "Total files copied: {len(audio_files)}"\n')

    # Make script executable
    os.chmod(script_path, 0o755)
    print(f"Generated copy script: {script_path}")
    return script_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate training dataset for VibeVoice from ASR-SCCantDuSC Cantonese corpus"
    )

    parser.add_argument(
        "--meta-file",
        required=True,
        help="Path to UTTRANSINFO.txt metadata file (WAV directory should be in the same parent directory)"
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
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)

    # Validate paths
    if not os.path.exists(args.meta_file):
        print(f"Error: Metadata file does not exist: {args.meta_file}")
        return 1

    # Check WAV directory exists
    base_dir = os.path.dirname(args.meta_file)
    wav_dir = os.path.join(base_dir, 'WAV')
    if not os.path.exists(wav_dir):
        print(f"Error: WAV directory does not exist: {wav_dir}")
        return 1

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate dataset
    print("\nGenerating Cantonese training dataset...")
    print(f"Metadata file: {args.meta_file}")
    print(f"WAV directory: {wav_dir}")
    print(f"Max files: {args.max_number if args.max_number > 0 else 'Unlimited'}")
    print(f"Voice prompts per sample: {args.num_voice_prompts}")
    print(f"Output path: {args.output_dir}")
    print(f"Speaker name: {args.speaker_name}")
    print()

    dataset, audio_files = generate_dataset(
        meta_file_path=args.meta_file,
        output_path=args.output_dir,
        max_files=args.max_number,
        num_voice_prompts=args.num_voice_prompts,
        speaker_name=args.speaker_name
    )

    if not dataset:
        print("Error: No dataset entries generated")
        return 1

    # Write dataset JSONL
    write_dataset_jsonl(dataset, args.output_dir)

    # Generate copy script
    generate_copy_script(audio_files, args.meta_file, args.output_dir)

    print("\n✓ Dataset generation completed successfully!")
    print(f"  - Dataset entries: {len(dataset)}")
    print(f"  - Total audio files: {len(audio_files)}")
    print("\nNext steps:")
    print(f"  1. Review {os.path.join(args.output_dir, 'datasets.jsonl')}")
    print(f"  2. Run {os.path.join(args.output_dir, 'copy_audio_files.sh')} to copy audio files")

    return 0


if __name__ == "__main__":
    exit(main())
