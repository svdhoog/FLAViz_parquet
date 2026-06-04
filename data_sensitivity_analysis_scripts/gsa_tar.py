#!/usr/bin/env bash
# ================================================================================
# Global Sensitivity Analysis (GSA) Pipeline - Tar Native Reader Edition
# ================================================================================
# Description:
#     Reads Snappy-compressed Parquet files directly from an uncompressed 
#     tar archive into RAM buffers to perform sensitivity analysis without 
#     unpacking files to disk.
# ================================================================================
import os
import io
import sys
import tarfile
import argparse
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# Placeholders for your specific GSA mathematics package
# e.g., from SALib.analyze import sobol

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run Global Sensitivity Analysis directly from a simulation TAR archive."
    )
    parser.add_argument(
        "--archive", 
        type=str, 
        required=True, 
        help="Absolute path to the uncompressed simulations.tar file."
    )
    parser.add_argument(
        "--sets", 
        type=int, 
        default=513, 
        help="Total number of simulation sets to process (Default: 513)."
    )
    parser.add_argument(
        "--runs", 
        type=int, 
        default=1000, 
        help="Total number of runs per simulation set (Default: 1000)."
    )
    parser.add_argument(
        "--target-file", 
        type=str, 
        default="data_Eurostat.parquet", 
        help="The specific filename within each run folder to target."
    )
    return parser.parse_args()

def stream_parquet_from_tar(tar_handle, internal_path):
    """
    Locates a file inside the open TAR archive, reads its raw bytes, 
    and passes the decompressed Snappy stream straight into a Pandas DataFrame
    using an in-memory byte buffer.
    """
    try:
        # Get the file metadata from the tar index
        member = tar_handle.getmember(internal_path)
        
        # Read the raw binary stream directly from the archive file pointer
        file_bytes = tar_handle.extractfile(member).read()
        
        # Wrap bytes in an in-memory file-like object
        buffer = io.BytesIO(file_bytes)
        
        # PyArrow handles the on-the-fly Snappy decompression here
        table = pq.read_table(buffer)
        return table.to_pandas()
        
    except KeyError:
        # Handle cases where a specific run might be missing from the archive
        print(f" -> [Warning] Path missing inside archive: {internal_path}", file=sys.stderr)
        return None
    except Exception as e:
        print(f" -> [Error] Failed reading {internal_path}: {str(e)}", file=sys.stderr)
        return None

def execute_sensitivity_analysis(archive_path, total_sets, runs_per_set, target_filename):
    print(f"[*] Initializing GSA Engine...")
    print(f"[*] Source Archive: {archive_path}")
    print(f"[*] Layout Matrix : {total_sets} sets × {runs_per_set} runs")
    
    # Initialize data aggregation structures depending on your GSA layout
    # For example, if you are tracking a specific scalar metric across all runs:
    aggregated_results = []

    # Open the TAR file once and keep the handle alive for sequential streaming
    # Using 'r:' mode specifies an uncompressed stream for maximum access speed
    with tarfile.open(archive_path, "r:") as tar:
        
        for set_idx in range(1, total_sets + 1):
            # Track progression through the sets
            percentage = (set_idx / total_sets) * 100
            print(f" -> Processing Matrix: Set [{set_idx}/{total_sets}] ({percentage:.2f}%)", flush=True)
            
            for run_idx in range(1, runs_per_set + 1):
                # Construct the exact internal structural path used inside the tar archive
                # Adjust this string if your archive has a different base directory root name
                internal_path = f"sets/set_{set_idx}/run_{run_idx}/{target_filename}"
                
                # Stream the dataframe straight into RAM
                df = stream_parquet_from_tar(tar, internal_path)
                
                if df is not None:
                    # --------------------------------------------------------
                    # CORE ANALYSIS SECTION (Inherited from sensitivity_analysis.py)
                    # Extract the specific outputs/columns you need for your GSA calculation.
                    # --------------------------------------------------------
                    # Example hypothetical calculation:
                    # target_metric = df['output_column'].iloc[-1] 
                    # aggregated_results.append(target_metric)
                    pass

    print("[*] Data streaming complete. Running sensitivity indices calculations...")
    
    # --------------------------------------------------------
    # RUN GSA MATHEMATICS HERE
    # Pass your aggregated matrix variables down to SALib / customized indices loop.
    # --------------------------------------------------------
    
    print("[+] GSA Task Finished Successfully.")

if __name__ == "__main__":
    args = parse_arguments()
    
    # Verify the archive file exists on the filesystem before starting
    if not os.path.exists(args.archive):
        print(f"[-] Error: Target archive file not found at '{args.archive}'")
        sys.exit(1)
        
    execute_sensitivity_analysis(
        archive_path=args.archive,
        total_sets=args.sets,
        runs_per_set=args.runs,
        target_filename=args.target_file
    )