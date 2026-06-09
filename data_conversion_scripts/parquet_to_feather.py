#!/usr/bin/env python3
"""
================================================================================
Parquet to Feather Converter (Low-Memory Streamer with Dynamic Verbosity)
================================================================================
Iterative streaming utility designed to convert Parquet datasets back into 
uncompressed or compressed Arrow IPC/Feather binary layouts chunk-by-chunk.
Includes adaptive console reporting based on quiet, normal, and verbose flags.
"""

import os
import sys
import time
import argparse
import pyarrow as pa
import pyarrow.parquet as pq

def convert_parquet_to_feather(input_path, output_path, quiet=False, verbose=False):
    # Detect if stdout is connected to an interactive terminal or a piped text file
    is_terminal = sys.stdout.isatty()

    # Initial startup messages are preserved across all configurations
    print(f"[INFO] Initiating Conversion: Parquet -> Feather")
    print(f"[INFO] Source: {input_path}")
    print(f"[INFO] Target: {output_path}")
    
    start_time = time.time()
    
    # Bind to the Parquet structural handle
    parquet_file = pq.ParquetFile(input_path)
    
    # Cross-version compatibility safeguard for Arrow schema resolution
    if hasattr(parquet_file, 'schema_arrow'):
        schema = parquet_file.schema_arrow
    else:
        schema = parquet_file.schema.to_arrow_schema()
        
    num_row_groups = parquet_file.num_row_groups
    
    if verbose:
        print(f"[VERBOSE] Detailed Parquet Schema Layout:\n{schema}")
        print(f"[VERBOSE] File Metadata contains {num_row_groups} Row Groups.")
    else:
        print(f"[INFO] Detected Schema with {len(schema.names)} columns.")
        print(f"[INFO] Streaming Row Groups directly to disk sink...")
        
    # Set up batch iteration based on available file components
    batch_iterator = parquet_file.iter_batches()
    
    # Initialize resource trackers to None for robust scoped exception handling
    sink = None
    writer = None
    
    try:
        # Open file handle inside the try block to avoid unhandled OSExceptions
        sink = open(output_path, 'wb')
        writer = pa.ipc.RecordBatchFileWriter(sink, schema)
        
        # Iteratively yield row batches across all internal Row Groups
        for i, batch in enumerate(batch_iterator):
            if verbose:
                print(f"[VERBOSE] Streaming chunk {i + 1} (Rows in batch: {batch.num_rows}, Bytes: {batch.nbytes})")
                
            writer.write_batch(batch)
            
            # Dynamic terminal log routing based on quiet, verbose, and stream environment
            if not quiet:
                if not verbose:
                    if (i + 1) % 50 == 0:
                        print(f"[PROGRESS] Streamed {i + 1} processing chunks...", flush=True)
            else:
                # If quiet is True, only print progress inline when running in an active terminal
                if is_terminal:
                    print(f"\r[PROGRESS] Streaming block execution chunk: {i + 1} written...", end="", flush=True)
                    
            # Explicitly clear loop reference to assist PyArrow's garbage collection
            batch = None
        
        if quiet and is_terminal:
            print() # Advance terminal line on completion
            
    finally:
        # Guarantee resource cleanup even if the stream process encounters errors midway
        if writer is not None:
            writer.close()
        if sink is not None:
            sink.close()

    elapsed = time.time() - start_time
    # The final success printout is completely preserved under all flags
    print(f"[SUCCESS] Feather file generated successfully in {elapsed:.2f} seconds.", flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OOM-Safe Parquet to Feather Converter with Advanced Verbosity Control.")
    parser.add_argument('--input', required=True, help="Path to the source .parquet file.")
    parser.add_argument('--output', required=True, help="Path where the target .feather file will be written.")
    
    # Mutually exclusive verbosity group setup
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument('--quiet', action='store_true', help="Suppresses intensive progressive iteration logs. Shows an inline counter in terminal, or periodic batch summaries in files.")
    verbosity_group.add_argument('--verbose', action='store_true', help="Outputs granular low-level buffer details for every active file chunk iteration.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"[-] Error: Input file does not exist at {args.input}")
        sys.exit(1)
        
    convert_parquet_to_feather(
        input_path=args.input,
        output_path=args.output,
        quiet=args.quiet,
        verbose=args.verbose
    )
