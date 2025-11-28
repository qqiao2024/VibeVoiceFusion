#!/usr/bin/env python3
"""
Tool to inspect safetensors files.
Can display metadata and list tensor keys with optional regex filtering.
"""

import argparse
import re
import sys
from pathlib import Path
from safetensors import safe_open


def print_metadata(metadata: dict, format_type: str = "plain"):
    """Print metadata in different formats."""
    if not metadata:
        print("No metadata found in file.")
        return
    
    if format_type == "plain":
        print("Metadata:")
        print("-" * 80)
        for key, value in sorted(metadata.items()):
            print(f"{key}: {value}")
        print("-" * 80)
    elif format_type == "json":
        import json
        print(json.dumps(metadata, indent=2))
    elif format_type == "key-only":
        for key in sorted(metadata.keys()):
            print(key)


def list_tensor_keys(file_path: str, key_pattern: str = None, show_shapes: bool = False, show_dtypes: bool = False):
    """List tensor keys from safetensors file with optional regex filtering."""
    keys_found = []
    
    with safe_open(file_path, framework="pt") as f:
        all_keys = list(f.keys())
        
        # Filter by regex if provided
        if key_pattern:
            pattern = re.compile(key_pattern)
            matching_keys = [k for k in all_keys if pattern.search(k)]
        else:
            matching_keys = all_keys
        
        if not matching_keys:
            if key_pattern:
                print(f"No keys matching pattern '{key_pattern}' found.")
            else:
                print("No tensor keys found in file.")
            return
        
        print(f"\nTensor Keys ({len(matching_keys)}/{len(all_keys)} shown):")
        print("-" * 80)
        
        for key in sorted(matching_keys):
            tensor = f.get_tensor(key)
            info_parts = [key]
            
            if show_shapes:
                info_parts.append(f"shape={list(tensor.shape)}")
            if show_dtypes:
                info_parts.append(f"dtype={tensor.dtype}")
            
            print(" | ".join(info_parts))
        
        print("-" * 80)
        print(f"Total: {len(matching_keys)} keys")


def get_file_stats(file_path: str):
    """Get statistics about the safetensors file."""
    total_params = 0
    total_size_bytes = 0
    dtype_counts = {}
    
    with safe_open(file_path, framework="pt") as f:
        keys = list(f.keys())
        
        for key in keys:
            tensor = f.get_tensor(key)
            num_params = tensor.numel()
            total_params += num_params
            
            # Approximate size (bytes per element)
            dtype_str = str(tensor.dtype)
            if dtype_str not in dtype_counts:
                dtype_counts[dtype_str] = 0
            dtype_counts[dtype_str] += 1
            
            # Calculate byte size
            element_size = tensor.element_size()
            total_size_bytes += num_params * element_size
    
    print("\nFile Statistics:")
    print("-" * 80)
    print(f"Total tensors: {len(keys)}")
    print(f"Total parameters: {total_params:,}")
    print(f"Total size: {total_size_bytes / (1024**2):.2f} MB ({total_size_bytes / (1024**3):.2f} GB)")
    print(f"\nData types:")
    for dtype, count in sorted(dtype_counts.items()):
        print(f"  {dtype}: {count} tensors")
    print("-" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Inspect safetensors files - view metadata and list tensor keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show metadata and all keys
  python view_tensorfile.py model.safetensors
  
  # Show only metadata in JSON format
  python view_tensorfile.py model.safetensors --metadata-only --format json
  
  # List keys matching a pattern with shapes
  python view_tensorfile.py model.safetensors --keys-only --pattern ".*lora.*" --show-shapes
  
  # Show file statistics
  python view_tensorfile.py model.safetensors --stats
        """
    )
    
    parser.add_argument("file", type=str, help="Path to safetensors file")
    
    # Display options
    parser.add_argument("--metadata-only", action="store_true", 
                        help="Only display metadata")
    parser.add_argument("--keys-only", action="store_true",
                        help="Only display tensor keys")
    parser.add_argument("--stats", action="store_true",
                        help="Show file statistics")
    
    # Metadata options
    parser.add_argument("--format", choices=["plain", "json", "key-only"], default="plain",
                        help="Format for metadata display (default: plain)")
    parser.add_argument("--metadata-key", type=str,
                        help="Show only a specific metadata key")
    
    # Key filtering options
    parser.add_argument("--pattern", type=str,
                        help="Regex pattern to filter tensor keys")
    parser.add_argument("--show-shapes", action="store_true",
                        help="Show tensor shapes")
    parser.add_argument("--show-dtypes", action="store_true",
                        help="Show tensor data types")
    
    args = parser.parse_args()
    
    # Validate file exists
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    
    if not file_path.suffix == ".safetensors":
        print(f"Warning: File does not have .safetensors extension", file=sys.stderr)
    
    print(f"Inspecting: {file_path}")
    print("=" * 80)
    
    try:
        # Display metadata
        if not args.keys_only and not args.stats:
            with safe_open(str(file_path), framework="pt") as f:
                metadata = f.metadata()
                
                if args.metadata_key:
                    if metadata and args.metadata_key in metadata:
                        print(f"{args.metadata_key}: {metadata[args.metadata_key]}")
                    else:
                        print(f"Metadata key '{args.metadata_key}' not found.")
                else:
                    print_metadata(metadata, args.format)
        
        # Display tensor keys
        if not args.metadata_only and not args.stats:
            list_tensor_keys(
                str(file_path),
                key_pattern=args.pattern,
                show_shapes=args.show_shapes,
                show_dtypes=args.show_dtypes
            )
        
        # Display statistics
        if args.stats:
            get_file_stats(str(file_path))
    
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()