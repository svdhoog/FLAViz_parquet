#!/usr/bin/env python3
"""
================================================================================
Feather to Parquet Converter (Low-Memory Streamer)
================================================================================
Memory-mapped file streaming utility designed to convert Arrow IPC/Feather
checkpoint binaries into Parquet format batch-by-batch without memory inflation.
"""

import os
import sys
import time
import argparse
import pyarrow as pa
import pyarrow.parquet as pq

def convert_feather_to_parquet(input_path, output_path, compression='snappy'):
    print(f"[INFO] Initiating Conversion: Feather -> Parquet")
    print(f"[INFO] Source: {input_path}")
    print(f"[INFO] Target: {output_path}")
    
    start_time = time.time()
    
    # Open the Feather file using a memory-mapped file wrapper
    with pa.memory_map(input_path, 'rb') as source:
        # Open the file layout as an IPC stream reader
        reader = pa.ipc.RecordBatchFileReader(source)
        schema = reader.schema
        num_batches = reader.num_record_batches
        
        print(f"[INFO] Detected Schema with {len(schema.names)} columns.")
        print(f"[INFO] Processing {num_batches} record batches sequentially...")
        
        # Initialize the sequential Parquet writer
        with pq.ParquetWriter(output_path, schema, compression=compression) as writer:
            for i in range(num_batches):
                batch = reader.get_batch(i)
                writer.write_batch(batch)
                
                if (i + 1) % 50 == 0 or (i + 1) == num_batches:
                    print(f"[PROGRESS] Written {i + 1}/{num_batches} batches...")

    elapsed = time.time() - start_time
    print(f"[SUCCESS] Parquet file generated successfully in {elapsed:.2f} seconds.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OOM-Safe Feather to Parquet Converter.")
    parser.add_argument('--input', required=True, help="Path to the source .feather file.")
    parser.add_argument('--output', required=True, help="Path where the target .parquet file will be written.")
    parser.add_argument('--compression', default='snappy', choices=['snappy', 'gzip', 'brotli', 'none'],
                        help="Compression codec to apply to the Parquet columns (default: snappy).")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"[-] Error: Input file does not exist at {args.input}")
        sys.exit(1)
        
    convert_feather_to_parquet(args.input, args.output, compression=args.compression)