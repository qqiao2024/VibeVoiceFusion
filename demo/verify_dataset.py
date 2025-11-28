#!/usr/bin/env python3
"""
Verify generated dataset for VibeVoice training.

This script validates the generated dataset.jsonl and copy script to ensure:
1. Audio files correspond to correct entries in utt2subdialect with correct dialect
2. Voice prompt files are valid audio files
3. Voice prompts are different from target audio files
4. Text contents match the audio files
5. Number of voice prompts matches requirements
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def parse_metadata_file(file_path: str) -> Dict[str, str]:
    """Parse a metadata file with two columns separated by whitespace."""
    metadata = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                metadata[parts[0]] = parts[1]
    return metadata


def extract_audio_id(file_path: str) -> str:
    """Extract audio ID from file path (remove extension and directory)."""
    return Path(file_path).stem


def load_dataset(dataset_path: str) -> List[Dict]:
    """Load dataset from JSONL file."""
    dataset = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                dataset.append((line_num, entry))
            except json.JSONDecodeError as e:
                print(f"{Colors.RED}✗ Error parsing line {line_num}: {e}{Colors.RESET}")
                sys.exit(1)
    return dataset


def verify_dataset(
    dataset_path: str,
    text_path: str,
    utt2dialect_path: str,
    expected_dialect: str = None,
    expected_num_prompts: int = 2
) -> Tuple[int, int]:
    """
    Verify the generated dataset.
    
    Returns:
        Tuple of (total_checks, failed_checks)
    """
    print(f"\n{Colors.BOLD}=== Dataset Verification ==={Colors.RESET}\n")
    
    # Load metadata
    print("Loading metadata files...")
    utt2dialect = parse_metadata_file(utt2dialect_path)
    text_dict = parse_metadata_file(text_path)
    
    print(f"  - Loaded {len(utt2dialect)} dialect entries")
    print(f"  - Loaded {len(text_dict)} text entries")
    
    # Load dataset
    print(f"\nLoading dataset from {dataset_path}...")
    dataset = load_dataset(dataset_path)
    print(f"  - Loaded {len(dataset)} dataset entries\n")
    
    total_checks = 0
    failed_checks = 0
    warnings = []
    
    # Verify each entry
    print(f"{Colors.BOLD}Verifying dataset entries...{Colors.RESET}\n")
    
    for line_num, entry in dataset:
        entry_errors = []
        
        # Extract fields
        text = entry.get('text', '')
        audio_path = entry.get('audio', '')
        voice_prompts = entry.get('voice_prompts', [])
        
        # Extract audio ID from path
        audio_id = extract_audio_id(audio_path)
        
        # Check 1: Audio file exists in utt2subdialect
        total_checks += 1
        if audio_id not in utt2dialect:
            failed_checks += 1
            entry_errors.append(f"Audio file '{audio_id}' not found in utt2subdialect")
        else:
            # Check dialect if specified
            if expected_dialect:
                actual_dialect = utt2dialect[audio_id]
                total_checks += 1
                if actual_dialect != expected_dialect:
                    failed_checks += 1
                    entry_errors.append(
                        f"Audio file '{audio_id}' has dialect '{actual_dialect}', "
                        f"expected '{expected_dialect}'"
                    )
        
        # Check 2: Voice prompts are valid audio files
        for vp_path in voice_prompts:
            vp_id = extract_audio_id(vp_path)
            total_checks += 1
            if vp_id not in utt2dialect:
                failed_checks += 1
                entry_errors.append(f"Voice prompt '{vp_id}' not found in utt2subdialect")
            else:
                # Check dialect matches if specified
                if expected_dialect:
                    vp_dialect = utt2dialect[vp_id]
                    total_checks += 1
                    if vp_dialect != expected_dialect:
                        failed_checks += 1
                        entry_errors.append(
                            f"Voice prompt '{vp_id}' has dialect '{vp_dialect}', "
                            f"expected '{expected_dialect}'"
                        )
        
        # Check 3: Voice prompts are different from target audio
        vp_ids = [extract_audio_id(vp) for vp in voice_prompts]
        total_checks += 1
        if audio_id in vp_ids:
            failed_checks += 1
            entry_errors.append(f"Voice prompt contains target audio file '{audio_id}'")
        
        # Check 4: Text content matches audio file
        total_checks += 1
        if audio_id not in text_dict:
            failed_checks += 1
            entry_errors.append(f"Audio file '{audio_id}' not found in text metadata")
        else:
            expected_text = text_dict[audio_id]
            # Extract text after speaker name
            if ': ' in text:
                actual_text = text.split(': ', 1)[1]
            else:
                actual_text = text
            
            if actual_text != expected_text:
                failed_checks += 1
                entry_errors.append(
                    f"Text mismatch for '{audio_id}':\n"
                    f"    Expected: {expected_text}\n"
                    f"    Actual: {actual_text}"
                )
        
        # Check 5: Number of voice prompts
        total_checks += 1
        if len(voice_prompts) != expected_num_prompts:
            failed_checks += 1
            entry_errors.append(
                f"Expected {expected_num_prompts} voice prompts, found {len(voice_prompts)}"
            )
        
        # Report errors for this entry
        if entry_errors:
            print(f"{Colors.RED}✗ Line {line_num} (audio: {audio_id}):{Colors.RESET}")
            for error in entry_errors:
                print(f"    {error}")
            print()
        else:
            if line_num % 100 == 0:
                print(f"{Colors.GREEN}✓ Verified {line_num} entries...{Colors.RESET}", end='\r')
    
    print()  # New line after progress
    
    return total_checks, failed_checks


def verify_copy_script(script_path: str, dataset_path: str) -> Tuple[int, int]:
    """
    Verify the generated copy script.
    
    Returns:
        Tuple of (total_checks, failed_checks)
    """
    print(f"\n{Colors.BOLD}=== Copy Script Verification ==={Colors.RESET}\n")
    
    if not os.path.exists(script_path):
        print(f"{Colors.YELLOW}⚠ Warning: Copy script not found at {script_path}{Colors.RESET}")
        return 0, 0
    
    # Load dataset to get expected files
    dataset = load_dataset(dataset_path)
    expected_files = set()
    
    for line_num, entry in dataset:
        audio_path = entry.get('audio', '')
        voice_prompts = entry.get('voice_prompts', [])
        
        audio_id = extract_audio_id(audio_path)
        expected_files.add(audio_id)
        
        for vp_path in voice_prompts:
            vp_id = extract_audio_id(vp_path)
            expected_files.add(vp_id)
    
    print(f"Expected {len(expected_files)} unique audio files")
    
    # Parse copy script
    with open(script_path, 'r', encoding='utf-8') as f:
        script_content = f.read()
    
    found_files = set()
    for line in script_content.split('\n'):
        if line.strip().startswith('cp '):
            # Extract source file path
            parts = line.split('"')
            if len(parts) >= 2:
                src_path = parts[1]
                audio_id = Path(src_path).stem
                found_files.add(audio_id)
    
    print(f"Found {len(found_files)} files in copy script")
    
    total_checks = 2
    failed_checks = 0
    
    # Check if all expected files are in script
    missing_files = expected_files - found_files
    if missing_files:
        failed_checks += 1
        print(f"\n{Colors.RED}✗ Missing {len(missing_files)} files in copy script:{Colors.RESET}")
        for file_id in sorted(list(missing_files)[:10]):  # Show first 10
            print(f"    {file_id}")
        if len(missing_files) > 10:
            print(f"    ... and {len(missing_files) - 10} more")
    else:
        print(f"{Colors.GREEN}✓ All expected files are in copy script{Colors.RESET}")
    
    # Check if there are extra files in script
    extra_files = found_files - expected_files
    if extra_files:
        failed_checks += 1
        print(f"\n{Colors.RED}✗ Extra {len(extra_files)} files in copy script:{Colors.RESET}")
        for file_id in sorted(list(extra_files)[:10]):  # Show first 10
            print(f"    {file_id}")
        if len(extra_files) > 10:
            print(f"    ... and {len(extra_files) - 10} more")
    else:
        print(f"{Colors.GREEN}✓ No extra files in copy script{Colors.RESET}")
    
    return total_checks, failed_checks


def main():
    parser = argparse.ArgumentParser(
        description="Verify generated training dataset for VibeVoice"
    )
    
    parser.add_argument(
        "--dataset-path",
        default="./demo/datasets/dataset.jsonl",
        help="Path to dataset.jsonl file (default: ./demo/datasets/dataset.jsonl)"
    )
    
    parser.add_argument(
        "--script-path",
        default="./demo/datasets/copy_audio_files.sh",
        help="Path to copy script (default: ./demo/datasets/copy_audio_files.sh)"
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
        "--dialect",
        default=None,
        help="Expected dialect for all entries (optional)"
    )
    
    parser.add_argument(
        "--num-voice-prompts",
        type=int,
        default=2,
        help="Expected number of voice prompts per sample (default: 2)"
    )
    
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.exists(args.dataset_path):
        print(f"{Colors.RED}Error: Dataset file does not exist: {args.dataset_path}{Colors.RESET}")
        return 1
    
    if not os.path.exists(args.text_path):
        print(f"{Colors.RED}Error: Text metadata file does not exist: {args.text_path}{Colors.RESET}")
        return 1
    
    if not os.path.exists(args.utt2dialect_path):
        print(f"{Colors.RED}Error: Dialect metadata file does not exist: {args.utt2dialect_path}{Colors.RESET}")
        return 1
    
    # Run verification
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Dataset Verification Tool{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"\nDataset: {args.dataset_path}")
    print(f"Text metadata: {args.text_path}")
    print(f"Dialect metadata: {args.utt2dialect_path}")
    if args.dialect:
        print(f"Expected dialect: {args.dialect}")
    print(f"Expected voice prompts: {args.num_voice_prompts}")
    
    # Verify dataset
    dataset_total, dataset_failed = verify_dataset(
        dataset_path=args.dataset_path,
        text_path=args.text_path,
        utt2dialect_path=args.utt2dialect_path,
        expected_dialect=args.dialect,
        expected_num_prompts=args.num_voice_prompts
    )
    
    # Verify copy script
    script_total, script_failed = verify_copy_script(
        script_path=args.script_path,
        dataset_path=args.dataset_path
    )
    
    # Summary
    total_checks = dataset_total + script_total
    total_failed = dataset_failed + script_failed
    total_passed = total_checks - total_failed
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Verification Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    print(f"Total checks: {total_checks}")
    print(f"{Colors.GREEN}Passed: {total_passed}{Colors.RESET}")
    if total_failed > 0:
        print(f"{Colors.RED}Failed: {total_failed}{Colors.RESET}")
        print(f"\n{Colors.RED}✗ Verification FAILED{Colors.RESET}")
        return 1
    else:
        print(f"\n{Colors.GREEN}✓ All checks PASSED{Colors.RESET}")
        return 0


if __name__ == "__main__":
    exit(main())
