#!/usr/bin/env python3
"""
================================================================================
Feather to Parquet Converter (Optimized Low-Memory Aggregator)
================================================================================
Memory-mapped streaming utility that converts Arrow IPC/Feather binaries into 
Parquet format. Aggregates small record batches into consolidated Row Groups 
to prevent file fragmentation and eliminate downstream parquet2feather crashes.
"""

import os
import sys
import time
import argparse
import pyarrow as pa
import pyarrow.parquet as pq

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=40, fill='█'):
    """
    Call in a loop to create terminal progress bar. Forces flush=True to resolve
    terminal display buffering bugs.
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    # The carriage return character is placed at the front to reset the line correctly
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='', flush=True)
    if iteration == total: 
        print()

def convert_feather_to_parquet(input_path, output_path, compression='snappy', quiet=False, verbose=False):
    is_terminal = sys.stdout.isatty()

    # Initial startup messages are preserved across all configurations
    print(f"[INFO] Initiating Conversion: Feather -> Parquet")
    print(f"[INFO] Source: {input_path}")
    print(f"[INFO] Target: {output_path}")
    
    start_time = time.time()
    
    # Open the Feather file using a memory-mapped file wrapper
    with pa.memory_map(input_path, 'rb') as source:
        reader = pa.ipc.RecordBatchFileReader(source)
        schema = reader.schema
        num_batches = reader.num_record_batches
        
        # Defensive Check: Handle empty files gracefully
        if num_batches == 0:
            print("[-] Warning: The source Feather file contains 0 record batches. Terminating conversion.")
            return

        if verbose:
            print(f"[VERBOSE] Detailed Arrow Schema Layout:\n{schema}")
            print(f"[VERBOSE] Target Metadata Compression Engine: {compression.upper()}")
        else:
            print(f"[INFO] Detected Schema with {len(schema.names)} columns.")
            print(f"[INFO] Processing {num_batches} record batches sequentially...")
            
        if quiet and is_terminal:
            print_progress_bar(0, num_batches, prefix='[PROGRESS] Converting:', suffix='Complete', length=40)
        
        # Buffer multiple record batches into an internal list and write them 
        # out as a single consolidated Table chunk to limit Row Group fragmentation.
        batch_buffer = []
        rows_in_buffer = 0
        ROW_GROUP_CEILING = 5_000_000 
        
        with pq.ParquetWriter(output_path, schema, compression=compression) as writer:
            for i in range(num_batches):
                batch = reader.get_batch(i)
                batch_buffer.append(batch)
                rows_in_buffer += batch.num_rows
                
                # If buffer hits the threshold or we reach the final batch, commit to disk
                if rows_in_buffer >= ROW_GROUP_CEILING or (i + 1) == num_batches:
                    if verbose:
                        print(f"[VERBOSE] Flashing aggregated Table block to disk (Batches: {len(batch_buffer)}, Rows: {rows_in_buffer})")
                    
                    chunk_table = pa.Table.from_batches(batch_buffer, schema=schema)
                    writer.write_table(chunk_table)
                    
                    # Reset memory state tracking arrays and clear batch objects
                    chunk_table = None
                    batch_buffer = []
                    rows_in_buffer = 0
                
                # Explicitly decouple batch reference to assist PyArrow's C++ garbage collection
                batch = None
                
                # Dynamic terminal log routing based on quiet, verbose, and stream environment
                if quiet:
                    if is_terminal:
                        if (i + 1) % 5 == 0 or (i + 1) == num_batches:
                            print_progress_bar(i + 1, num_batches, prefix='[PROGRESS] Converting:', suffix='Complete', length=40)
                    else:
                        # Throttles progress bar output to 10 lines max in headless logs
                        reporting_step = max(1, round(num_batches / 10))
                        if (i + 1) % reporting_step == 0 or (i + 1) == num_batches:
                            pct = (100 * (i + 1)) / num_batches
                            print(f"[PROGRESS] Conversion Checkpoint: {pct:.1f}% Complete ({i + 1}/{num_batches} batches processed)", flush=True)
                elif not verbose:
                    # Normal mode: outputs progress message update line every 50 batches
                    if (i + 1) % 50 == 0 or (i + 1) == num_batches:
                        print(f"[PROGRESS] Processed {i + 1}/{num_batches} batches...", flush=True)

    elapsed = time.time() - start_time
    # The final success printout is completely preserved under all flags
    print(f"[SUCCESS] Parquet file generated successfully in {elapsed:.2f} seconds.", flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OOM-Safe Feather to Parquet Converter with Advanced Verbosity Control.")
    parser.add_argument('--input', required=True, help="Path to the source .feather file.")
    parser.add_argument('--output', required=True, help="Path where the target .parquet file will be written.")
    parser.add_argument('--compression', default='snappy', choices=['snappy', 'gzip', 'brotli', 'none'],
                        help="Compression codec to apply to the Parquet columns (default: snappy).")
    
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument('--quiet', action='store_true', help="Suppresses intensive progressive iteration logs. Shows an inline bar in terminal, or clean 10% interval ticks in files.")
    verbosity_group.add_argument('--verbose', action='store_true', help="Outputs granular low-level buffer details for every active file chunk iteration.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"[-] Error: Input file does not exist at {args.input}")
        sys.exit(1)
        
    convert_feather_to_parquet(
        input_path=args.input, 
        output_path=args.output, 
        compression=args.compression, 
        quiet=args.quiet, 
        verbose=args.verbose
    )
