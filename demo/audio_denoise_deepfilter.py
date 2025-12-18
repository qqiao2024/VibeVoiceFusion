#!/usr/bin/env python3
"""
Audio Denoising Script using DeepFilterNet.

DeepFilterNet is a state-of-the-art deep learning model for real-time speech enhancement,
winner of the ICASSP 2022 DNS Challenge. It provides excellent noise suppression while
preserving speech quality.

Paper: https://arxiv.org/abs/2305.08227
GitHub: https://github.com/Rikorose/DeepFilterNet

Usage:
    python audio_denoise_deepfilter.py -i input.wav -o output.wav
    python audio_denoise_deepfilter.py --input input.wav --output output.wav --atten-lim 100
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import torch
import torchaudio


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Audio denoising using DeepFilterNet (SOTA real-time speech enhancement)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python audio_denoise_deepfilter.py -i noisy_audio.wav -o clean_audio.wav

    # Maximum noise reduction (may affect speech quality)
    python audio_denoise_deepfilter.py -i noisy_audio.wav -o clean_audio.wav --atten-lim 100

    # Gentle noise reduction (preserves more natural sound)
    python audio_denoise_deepfilter.py -i noisy_audio.wav -o clean_audio.wav --atten-lim 12

    # Process directory of files
    python audio_denoise_deepfilter.py -i ./noisy_folder/ -o ./clean_folder/

    # Verbose mode with post-filtering disabled
    python audio_denoise_deepfilter.py -i noisy.wav -o clean.wav --no-post-filter -v

Model Comparison:
    DeepFilterNet3 (default) - Best quality, slightly slower
    DeepFilterNet2           - Good balance of speed and quality
    DeepFilterNet            - Fastest, still good quality
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Path to the input audio file or directory (noisy audio)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Path to save the denoised output audio file or directory",
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
        default="DeepFilterNet3",
        choices=["DeepFilterNet", "DeepFilterNet2", "DeepFilterNet3"],
        help="Model version to use (default: DeepFilterNet3 - best quality)",
    )

    parser.add_argument(
        "--atten-lim",
        type=float,
        default=None,
        help="Noise attenuation limit in dB (default: model default ~40dB). "
        "Higher values = more aggressive noise reduction. "
        "Range: 0-100. Use 12-20 for gentle, 40-60 for moderate, 80-100 for aggressive.",
    )

    parser.add_argument(
        "--no-post-filter",
        action="store_true",
        help="Disable post-filtering (may sound more natural but less clean)",
    )

    parser.add_argument(
        "--compensate-delay",
        action="store_true",
        help="Compensate for the algorithmic delay (useful for real-time applications)",
    )

    parser.add_argument(
        "--keep-original-sr",
        action="store_true",
        help="Resample output back to original sample rate (model uses 48kHz internally)",
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


def load_audio(file_path: str) -> Tuple[torch.Tensor, int]:
    """
    Load audio file.

    Args:
        file_path: Path to the audio file

    Returns:
        tuple: (waveform, sample_rate)
    """
    waveform, sr = torchaudio.load(file_path)
    return waveform, sr


def save_audio(
    waveform: torch.Tensor,
    file_path: str,
    sample_rate: int,
    normalize: bool = True,
    original_sr: Optional[int] = None,
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


def load_deepfilter_model(model_name: str, device: str, post_filter: bool = True):
    """
    Load DeepFilterNet model.

    Args:
        model_name: Model version (DeepFilterNet, DeepFilterNet2, DeepFilterNet3)
        device: Device to load model on
        post_filter: Whether to enable post-filtering

    Returns:
        tuple: (model, df_state)
    """
    try:
        from df import init_df
    except ImportError as e:
        print(f"Error: DeepFilterNet import failed: {e}")
        print("\nInstall it with:")
        print("  pip install deepfilternet")
        print("\nOr for GPU support:")
        print("  pip install deepfilternet[cuda]")
        sys.exit(1)

    # Initialize the model - init_df will automatically download the model
    # When model_base_dir is None, it uses default_model parameter
    model, df_state, _ = init_df(
        model_base_dir=None,
        post_filter=post_filter,
        log_level="WARNING",
        log_file=None,
        default_model=model_name,
    )

    # Move model to device
    if device == "cuda":
        model = model.cuda()

    return model, df_state


def denoise_audio_deepfilter(
    model,
    df_state,
    input_path: str,
    output_path: str,
    device: str = "cpu",
    compensate_delay: bool = False,
    keep_original_sr: bool = False,
    normalize: bool = True,
    atten_lim: Optional[float] = None,
    verbose: bool = False,
):
    """
    Denoise an audio file using DeepFilterNet.

    Args:
        model: DeepFilterNet model
        df_state: DeepFilter state
        input_path: Path to input audio file
        output_path: Path to save denoised audio
        device: Device for inference
        compensate_delay: Whether to compensate algorithmic delay
        keep_original_sr: Whether to resample output back to original sample rate
        normalize: Whether to normalize output audio
        atten_lim: Noise attenuation limit in dB (passed to enhance function)
        verbose: Whether to print verbose information
    """
    from df import enhance
    from df.io import load_audio as df_load_audio, save_audio as df_save_audio

    if verbose:
        print(f"Loading audio from: {input_path}")

    # Load audio using DeepFilterNet's loader (handles resampling to 48kHz)
    audio, original_info = df_load_audio(input_path, sr=df_state.sr())

    if verbose:
        print(f"  Sample rate: {df_state.sr()}Hz (processing)")
        print(f"  Duration: {audio.shape[-1] / df_state.sr():.2f} seconds")
        print(f"  Channels: {audio.shape[0] if len(audio.shape) > 1 else 1}")

    # Ensure audio is a tensor and move to device if needed
    if not isinstance(audio, torch.Tensor):
        audio = torch.from_numpy(audio)
    
    if device == "cuda":
        audio = audio.cuda()

    if verbose:
        print("Running DeepFilterNet enhancement...")
        if atten_lim is not None:
            print(f"  Attenuation limit: {atten_lim} dB")

    # Run enhancement
    enhanced = enhance(
        model,
        df_state,
        audio,
        pad=compensate_delay,
        atten_lim_db=atten_lim,
    )

    # Move back to CPU for saving
    if device == "cuda":
        enhanced = enhanced.cpu()

    if verbose:
        print(f"Saving denoised audio to: {output_path}")

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Convert to numpy for saving
    enhanced_np = enhanced.numpy()

    # Normalize if requested
    if normalize:
        max_val = abs(enhanced_np).max()
        if max_val > 0:
            enhanced_np = enhanced_np / max_val * 0.95

    # Save the audio
    df_save_audio(
        output_path,
        enhanced_np,
        sr=df_state.sr(),
    )

    # Optionally resample back to original sample rate
    if keep_original_sr and original_info is not None:
        # original_info is an AudioMetaData object with sample_rate attribute
        original_sr = getattr(original_info, 'sample_rate', None)
        if original_sr and original_sr != df_state.sr():
            # Reload and resample
            waveform, sr = torchaudio.load(output_path)
            resampler = torchaudio.transforms.Resample(
                orig_freq=sr, new_freq=original_sr
            )
            waveform = resampler(waveform)
            torchaudio.save(output_path, waveform, original_sr)
            if verbose:
                print(f"  Resampled output to original {original_sr}Hz")

    if verbose:
        print("Done!")


def process_directory(
    model,
    df_state,
    input_dir: str,
    output_dir: str,
    device: str,
    compensate_delay: bool,
    keep_original_sr: bool,
    normalize: bool,
    atten_lim: Optional[float],
    verbose: bool,
):
    """Process all audio files in a directory."""
    audio_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    audio_files = [
        f for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() in audio_extensions
    ]

    if not audio_files:
        print(f"No audio files found in: {input_dir}")
        return

    print(f"Found {len(audio_files)} audio files to process")

    for i, audio_file in enumerate(audio_files, 1):
        output_file = output_path / f"{audio_file.stem}_denoised.wav"
        print(f"[{i}/{len(audio_files)}] Processing: {audio_file.name}")

        try:
            denoise_audio_deepfilter(
                model=model,
                df_state=df_state,
                input_path=str(audio_file),
                output_path=str(output_file),
                device=device,
                compensate_delay=compensate_delay,
                keep_original_sr=keep_original_sr,
                normalize=normalize,
                atten_lim=atten_lim,
                verbose=verbose,
            )
        except Exception as e:
            print(f"  Error processing {audio_file.name}: {e}")
            continue

    print(f"\nAll files processed. Output saved to: {output_dir}")


def main():
    """Main entry point."""
    args = parse_args()

    # Determine device
    device = get_device(args.device)
    if args.verbose:
        print(f"Using device: {device}")

    # Determine normalization setting
    normalize = not args.no_normalize
    post_filter = not args.no_post_filter

    # Load the model
    if args.verbose:
        print(f"Loading model: {args.model}")

    model, df_state = load_deepfilter_model(
        model_name=args.model,
        device=device,
        post_filter=post_filter,
    )

    if args.verbose:
        print(f"Model loaded successfully")
        print(f"  Post-filter: {'enabled' if post_filter else 'disabled'}")

    # Check if input is directory or file
    input_path = Path(args.input)
    output_path = Path(args.output)

    if input_path.is_dir():
        # Process directory
        process_directory(
            model=model,
            df_state=df_state,
            input_dir=args.input,
            output_dir=args.output,
            device=device,
            compensate_delay=args.compensate_delay,
            keep_original_sr=args.keep_original_sr,
            normalize=normalize,
            atten_lim=args.atten_lim,
            verbose=args.verbose,
        )
    else:
        # Process single file
        if not input_path.exists():
            print(f"Error: Input file not found: {args.input}")
            sys.exit(1)

        denoise_audio_deepfilter(
            model=model,
            df_state=df_state,
            input_path=args.input,
            output_path=args.output,
            device=device,
            compensate_delay=args.compensate_delay,
            keep_original_sr=args.keep_original_sr,
            normalize=normalize,
            atten_lim=args.atten_lim,
            verbose=args.verbose,
        )

        print(f"Successfully denoised audio saved to: {args.output}")


if __name__ == "__main__":
    main()
