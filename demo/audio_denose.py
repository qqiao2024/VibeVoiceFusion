#!/usr/bin/env python3
"""
Audio Denoising Script using SpeechBrain SepFormer model.

This script uses the speechbrain/sepformer-wham16k-enhancement model from HuggingFace
to enhance and denoise audio files.

Usage:
    python audio_denose.py -i input.wav -o output.wav
    python audio_denose.py --input input.wav --output output.wav --device cuda
"""

import argparse
import os
import sys
from pathlib import Path

import torch
import torchaudio
from speechbrain.inference.separation import SepformerSeparation as separator


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Audio denoising using SpeechBrain SepFormer model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python audio_denose.py -i noisy_audio.wav -o clean_audio.wav

    # Use GPU
    python audio_denose.py -i noisy_audio.wav -o clean_audio.wav --device cuda

    # Specify custom model cache directory
    python audio_denose.py -i noisy_audio.wav -o clean_audio.wav --savedir ./models/sepformer

    # Process with specific sample rate handling
    python audio_denose.py -i noisy_audio.wav -o clean_audio.wav --resample
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Path to the input audio file (noisy audio)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Path to save the denoised output audio file",
    )

    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device to run inference on (default: auto - uses CUDA if available)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="speechbrain/sepformer-wham16k-enhancement",
        help="HuggingFace model identifier for denoising (default: speechbrain/sepformer-wham16k-enhancement)",
    )

    parser.add_argument(
        "--savedir",
        type=str,
        default=None,
        help="Directory to cache the pretrained model (default: uses HuggingFace cache)",
    )

    parser.add_argument(
        "--resample",
        action="store_true",
        help="Automatically resample input audio to 16kHz if needed (model expects 16kHz)",
    )

    parser.add_argument(
        "--keep-original-sr",
        action="store_true",
        help="Resample output back to original sample rate (only works with --resample)",
    )

    parser.add_argument(
        "--normalize",
        action="store_true",
        default=True,
        help="Normalize output audio to prevent clipping (default: True)",
    )

    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Disable output normalization",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def get_device(device_arg: str) -> str:
    """Determine the device to use for inference."""
    if device_arg == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return device_arg


def load_audio(file_path: str, target_sr: int = 16000, resample: bool = False):
    """
    Load audio file and optionally resample to target sample rate.

    Args:
        file_path: Path to the audio file
        target_sr: Target sample rate (model expects 16kHz)
        resample: Whether to resample if sample rate doesn't match

    Returns:
        tuple: (waveform, sample_rate, original_sample_rate)
    """
    waveform, sr = torchaudio.load(file_path)

    original_sr = sr

    # Convert stereo to mono if needed
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    # Resample if needed
    if sr != target_sr:
        if resample:
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)
            waveform = resampler(waveform)
            sr = target_sr
        else:
            print(
                f"Warning: Audio sample rate is {sr}Hz, but model expects {target_sr}Hz."
            )
            print("Use --resample flag to automatically resample the audio.")

    return waveform, sr, original_sr


def save_audio(
    waveform: torch.Tensor,
    file_path: str,
    sample_rate: int,
    normalize: bool = True,
    original_sr: int = None,
    keep_original_sr: bool = False,
):
    """
    Save audio waveform to file.

    Args:
        waveform: Audio waveform tensor
        file_path: Output file path
        sample_rate: Current sample rate
        normalize: Whether to normalize the audio
        original_sr: Original sample rate (for resampling back)
        keep_original_sr: Whether to resample back to original sample rate
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(file_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Normalize if requested
    if normalize:
        max_val = torch.max(torch.abs(waveform))
        if max_val > 0:
            waveform = waveform / max_val * 0.95  # Leave some headroom

    # Resample back to original sample rate if requested
    if keep_original_sr and original_sr and original_sr != sample_rate:
        resampler = torchaudio.transforms.Resample(
            orig_freq=sample_rate, new_freq=original_sr
        )
        waveform = resampler(waveform)
        sample_rate = original_sr

    # Save the audio
    torchaudio.save(file_path, waveform, sample_rate)


def denoise_audio(
    model: separator,
    input_path: str,
    output_path: str,
    resample: bool = False,
    keep_original_sr: bool = False,
    normalize: bool = True,
    verbose: bool = False,
):
    """
    Denoise an audio file using the SepFormer model.

    Args:
        model: Loaded SepFormer model
        input_path: Path to input audio file
        output_path: Path to save denoised audio
        resample: Whether to resample input to 16kHz
        keep_original_sr: Whether to resample output back to original sample rate
        normalize: Whether to normalize output audio
        verbose: Whether to print verbose information
    """
    if verbose:
        print(f"Loading audio from: {input_path}")

    # Load audio
    waveform, sr, original_sr = load_audio(input_path, target_sr=16000, resample=resample)

    if verbose:
        print(f"  Original sample rate: {original_sr}Hz")
        print(f"  Processing sample rate: {sr}Hz")
        print(f"  Duration: {waveform.shape[1] / sr:.2f} seconds")
        print(f"  Channels: {waveform.shape[0]}")

    # Save temporary file for model input if needed
    # The model's separate_file method expects a file path
    temp_input = None
    if sr != original_sr or waveform.shape[0] == 1:
        temp_input = output_path + ".temp_input.wav"
        torchaudio.save(temp_input, waveform, sr)
        input_for_model = temp_input
    else:
        input_for_model = input_path

    if verbose:
        print("Running denoising model...")

    # Run the enhancement model
    try:
        enhanced = model.separate_file(path=input_for_model)
    finally:
        # Clean up temp file
        if temp_input and os.path.exists(temp_input):
            os.remove(temp_input)

    # The model returns enhanced audio with shape (batch, time, sources)
    # For enhancement, we typically have one source (the clean signal)
    if len(enhanced.shape) == 3:
        enhanced = enhanced[:, :, 0]  # Take the first (and usually only) source

    # Ensure correct shape for saving (channels, time)
    if len(enhanced.shape) == 1:
        enhanced = enhanced.unsqueeze(0)
    elif enhanced.shape[0] > enhanced.shape[1]:
        enhanced = enhanced.T

    if verbose:
        print(f"Saving denoised audio to: {output_path}")

    # Save the enhanced audio
    save_audio(
        enhanced.cpu(),
        output_path,
        sample_rate=sr,
        normalize=normalize,
        original_sr=original_sr,
        keep_original_sr=keep_original_sr,
    )

    if verbose:
        print("Done!")


def main():
    """Main entry point."""
    args = parse_args()

    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Determine device
    device = get_device(args.device)
    if args.verbose:
        print(f"Using device: {device}")

    # Determine normalization setting
    normalize = not args.no_normalize

    # Load the model
    if args.verbose:
        print(f"Loading model: {args.model}")

    model_kwargs = {
        "source": args.model,
        "run_opts": {"device": device},
    }

    if args.savedir:
        model_kwargs["savedir"] = args.savedir

    try:
        model = separator.from_hparams(**model_kwargs)
    except Exception as e:
        print(f"Error loading model: {e}")
        print("\nMake sure you have speechbrain installed:")
        print("  pip install speechbrain")
        sys.exit(1)

    # Run denoising
    denoise_audio(
        model=model,
        input_path=args.input,
        output_path=args.output,
        resample=args.resample,
        keep_original_sr=args.keep_original_sr,
        normalize=normalize,
        verbose=args.verbose,
    )

    print(f"Successfully denoised audio saved to: {args.output}")


if __name__ == "__main__":
    main()
