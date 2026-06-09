#!/usr/bin/env python3
"""
================================================================================
Parquet to Feather Converter (Low-Memory Streamer)
================================================================================
Iterative streaming utility designed to convert Parquet datasets back into 
uncompressed or compressed Arrow IPC/Feather binary layouts chunk-by-chunk.
"""

import os
import sys
import time
import argparse
import pyarrow as pa
import pyarrow.parquet as pq

def convert_parquet_to_feather(input_path, output_path):
    print(f"[INFO] Initiating Conversion: Parquet -> Feather")
    print(f"[INFO] Source: {input_path}")
    print(f"[INFO] Target: {output_path}")
    
    start_time = time.time()
    
    # Bind to the Parquet structural handle
    parquet_file = pq.ParquetFile(input_path)
    schema = parquet_file.schema_arrow
    
    print(f"[INFO] Detected Schema with {len(schema.names)} columns.")
    print(f"[INFO] Streaming Row Groups directly to disk sink...")
    
    # Open an operating system file descriptor handle for the binary output sink
    with pa.OSFile(output_path, 'wb') as sink:
        # Instantiate a standard Arrow IPC RecordBatchFileWriter
        with pa.ipc.RecordBatchFileWriter(sink, schema) as writer:
            # Iteratively yield row batches across all internal Row Groups
            for i, batch in enumerate(parquet_file.iter_batches()):
                writer.write_batch(batch)
                
                if (i + 1) % 50 == 0:
                    print(f"[PROGRESS] Streamed {i + 1} processing chunks...")
                    
    elapsed = time.time() - start_time
    print(f"[SUCCESS] Feather file generated successfully in {elapsed:.2f} seconds.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OOM-Safe Parquet to Feather Converter.")
    parser.add_argument('--input', required=True, help="Path to the source .parquet file.")
    parser.add_argument('--output', required=True, help="Path where the target .feather file will be written.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"[-] Error: Input file does not exist at {args.input}")
        sys.exit(1)
        
    convert_parquet_to_feather(args.input, args.output)