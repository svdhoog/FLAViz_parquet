#!/usr/bin/env python3
"""
================================================================================
Global Sensitivity Analysis (GSA) & Isolated Bifurcation Engine
================================================================================
DESIGN DECISIONS & ARCHITECTURAL EVOLUTION:
    1. [Shift to Bifurcation Mapping]: Preserves every individual stochastic 
       run against the parameter continuum to uncover phase transitions.
       
    2. [I/O Optimization via Stride Filters]: Loads only N-th simulation 
       steps natively at the worker stage to drop data footprints by 80%+.
       
    3. [Strict Worker Scaling Strategy]: Throttles concurrency to maintain \
       stable memory footprints under high data-load volumes.
       
    4. [Percentile Clipping]: Integrates a `--percentile` threshold filter to \
       truncate extreme stochastic outliers (e.g., 1e285) that would otherwise \
       obfuscate bifurcation attractors.

    5. [Integer Key Optimization]: Replaces high-overhead string tracking IDs \
       ('set_id') with primitive 16-bit integers ('set_num') inside both Parquet \
       and Feather file schemas. This eliminates multi-gigabyte string object bloat.

    6. [Direct Arrow Zero-Copy Plotting]: Bypasses Pandas DataFrames and \
       relational merge lookups entirely during plotting. Memory-mapped PyArrow \
       tables supply data vectors directly to Matplotlib using fast, zero-copy \
       NumPy views.

    7. [Single-Precision Downcasting]: Enforces float32 downcasting across all \
       floating-point analytical columns to instantly half computational memory layouts.
"""

import os
import sys
import time
import psutil
import argparse
import threading
import numpy as np
import pyarrow as pa
import pyarrow.feather as ft
import pyarrow.parquet as pq
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor, as_completed

class LiveMemoryProfiler(threading.Thread):
    """Background thread that tracks physical memory overhead changes during runtime."""
    def __init__(self, check_interval=0.5):
        super().__init__()
        self.check_interval = check_interval
        self.daemon = True
        self.max_memory = 0
        self.running = False
        self.process = psutil.Process(os.getpid())

    def start(self):
        self.running = True
        super().start()

    def run(self):
        while self.running:
            try:
                current_mem = self.process.memory_info().rss / (1024 ** 3) # GB
                if current_mem > self.max_memory:
                    self.max_memory = current_mem
                time.sleep(self.check_interval)
            except Exception:
                break

    def stop(self):
        self.running = False
        return self.max_memory

def extract_worker(file_path, table_name, metric, set_num, run_num, stride, file_format, batch_size=100_000):
    """
    Worker task that scans a single file using streaming chunk iterators.
    Applies filters and projects the data down to a minimal binary layout.
    """
    try:
        processed_batches = []
        
        # Enforce structural downcasting directly to float32
        target_schema = pa.schema([
            pa.field('set_num', pa.int16()),
            pa.field('run_num', pa.int16()),
            pa.field('step', pa.int32()),
            pa.field(metric, pa.float32())
        ])
        
        if file_format == 'parquet':
            pf = pq.ParquetFile(file_path)
            # Stream the file in chunks instead of loading the whole table at once
            iterator = pf.iter_batches(batch_size=batch_size, columns=['step', metric])
        else:
            source = pa.memory_map(file_path, 'rb')
            reader = pa.ipc.RecordBatchFileReader(source)
            # Manual chunking iterator fallback for Feather files
            def feather_iterator():
                for b_idx in range(reader.num_record_batches):
                    yield reader.get_batch(b_idx)
            iterator = feather_iterator()
            
        for raw_batch in iterator:
            # Apply your strided data filter directly to the streaming chunk
            total_rows = raw_batch.num_rows
            stride_indices = np.arange(0, total_rows, stride, dtype=np.int64)
            
            if len(stride_indices) == 0:
                continue
                
            chunk_table = pa.Table.from_batches([raw_batch])
            sliced_table = chunk_table.take(pa.array(stride_indices))
            
            # Extract arrays using zero-copy views
            steps = sliced_table.column('step').to_numpy()
            vals = sliced_table.column(metric).to_numpy().astype(np.float32)
            
            n_rows = len(steps)
            set_arr = np.full(n_rows, set_num, dtype=np.int16)
            run_arr = np.full(n_rows, run_num, dtype=np.int16)
            
            batch = pa.RecordBatch.from_arrays(
                [pa.array(set_arr), pa.array(run_arr), pa.array(steps), pa.array(vals)],
                schema=target_schema
            )
            processed_batches.append(batch)
            
            # Clean up local iteration variables immediately
            batch = None
            raw_batch = None
            chunk_table = None
            sliced_table = None
            
        if file_format != 'parquet':
            source.close()
            
        return processed_batches
    except Exception as e:
        print(f"[-] Worker failure on {file_path}: {e}", file=sys.stderr)
        return []

def stream_metric_data_to_file(input_root, table_name, metric, set_range, run_range, max_workers, stride, output_path, file_format):
    """Dispatches worker tasks to scan directories and streams completed chunks directly to disk."""
    print(f"[INFO] Compiling metric streams for target: {metric}")
    
    tasks = []
    set_min, set_max = set_range
    run_min, run_max = run_range
    
    for s in range(set_min, set_max + 1):
        for r in range(run_min, run_max + 1):
            f_name = f"set_{s}_run_{r}.{file_format}"
            f_path = os.path.join(input_root, f"set_{s}", f_name)
            if os.path.exists(f_path):
                tasks.append((f_path, table_name, metric, s, r, stride, file_format))
                
    if not tasks:
        print(f"[-] Error: No simulation assets found matching the target range criteria.")
        return

    # Create target schema mapping layout
    output_schema = pa.schema([
        pa.field('set_num', pa.int16()),
        pa.field('run_num', pa.int16()),
        pa.field('step', pa.int32()),
        pa.field(metric, pa.float32())
    ])
    
    print(f"[INFO] Launching extraction pool across {len(tasks)} target files...")
    
    # Explicit close orchestration handles older pyarrow versions safely
    if file_format == 'parquet':
        writer = pq.ParquetWriter(output_path, output_schema, compression='snappy')
    else:
        sink = open(output_path, 'wb')
        writer = pa.ipc.RecordBatchFileWriter(sink, output_schema)
        
    try:
        # Scaled processing executor prevents resource thrashing
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(extract_worker, t[0], t[1], t[2], t[3], t[4], t[5], t[6]): t for t in tasks
            }
            
            for idx, fut in enumerate(as_completed(futures)):
                batch_list = fut.result()
                if batch_list:
                    for batch in batch_list:
                        if file_format == 'parquet':
                            writer.write_table(pa.Table.from_batches([batch]))
                        else:
                            writer.write_batch(batch)
                        batch = None # Free reference immediately
                
                if (idx + 1) % 20 == 0 or (idx + 1) == len(tasks):
                    print(f"    -> Ingested {idx + 1}/{len(tasks)} tracking files...", flush=True)
    finally:
        if file_format == 'parquet':
            writer.close()
        else:
            writer.close()
            sink.close()

def generate_bifurcation_plots(checkpoint_path, metric, out_dir, file_format, percentile_threshold=100.0):
    """
    Streams data from consolidated checkpoints to perform zero-copy plotting 
    without loading the whole file into memory at once.
    """
    print(f"[PLOT] Generating zero-copy bifurcation figures for: {metric}")
    
    # First Pass: Stream the file to collect values and find the percentile threshold
    all_values = []
    
    if file_format == 'parquet':
        pf = pq.ParquetFile(checkpoint_path)
        iterator = pf.iter_batches(batch_size=200_000, columns=[metric])
    else:
        source = pa.memory_map(checkpoint_path, 'rb')
        reader = pa.ipc.RecordBatchFileReader(source)
        def feather_iter():
            for b_idx in range(reader.num_record_batches):
                yield reader.get_batch(b_idx)
        iterator = feather_iter()
        
    for batch in iterator:
        all_values.append(batch.column(metric).to_numpy())
        batch = None
        
    if not all_values:
        print("[-] Error: Checkpoint dataset is empty.")
        if file_format != 'parquet':
            source.close()
        return
        
    combined_values = np.concatenate(all_values)
    all_values = None # Clear references immediately
    
    # Calculate cutoff limits to filter extreme outliers
    if percentile_threshold < 100.0:
        cutoff = np.percentile(combined_values, percentile_threshold)
        print(f"[PLOT] Clipping active values above the {percentile_threshold}th percentile threshold limit ({cutoff:.4f})")
    else:
        cutoff = np.max(combined_values)
        
    combined_values = None # Free memory allocation before starting the plotting phase
    
    # Second Pass: Stream data into the plotting engine in blocks
    plt.figure(figsize=(12, 7))
    
    if file_format == 'parquet':
        iterator = pf.iter_batches(batch_size=200_000, columns=['set_num', metric])
    else:
        # Reset file pointer for the second pass over the Feather file
        source.seek(0)
        reader = pa.ipc.RecordBatchFileReader(source)
        iterator = feather_iter()
        
    total_points_plotted = 0
    
    for batch in iterator:
        set_nums = batch.column('set_num').to_numpy()
        metrics = batch.column(metric).to_numpy()
        
        # Apply the percentile filter mask to the current streaming chunk
        mask = metrics <= cutoff
        if not np.any(mask):
            continue
            
        plt.scatter(
            set_nums[mask], metrics[mask],
            color='black', s=0.05, alpha=0.15, rasterized=True
        )
        total_points_plotted += np.sum(mask)
        
        # Clear references within the loop to keep memory usage low
        batch = None
        set_nums = None
        metrics = None
        mask = None
        
    if file_format != 'parquet':
        source.close()
        
    print(f"[PLOT] Rendered {total_points_plotted:,} coordinates to canvas.")
    
    plt.title(f"Bifurcation Continuum Mapping Analysis: {metric}")
    plt.xlabel("Parameter Progression Matrix Sequence ID (set_num)")
    plt.ylabel(f"Stochastic Evaluation Profile Value ({metric})")
    plt.grid(True, linestyle=':', alpha=0.6)
    
    fig_path = os.path.join(out_dir, f"bifurcation_{metric}.png")
    plt.savefig(fig_path, dpi=400, bbox_inches='tight')
    plt.close()
    print(f"[SUCCESS] Bifurcation figure saved to disk target: {fig_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="High-Performance Low-Memory Global Sensitivity Analysis.")
    parser.add_argument('--input', required=True, help="Root folder containing the set_X directory trees.")
    parser.add_argument('--output', required=True, help="Target folder where checkpoints and figures are saved.")
    parser.add_argument('--metric', required=True, help="Comma-separated metric column names to extract.")
    parser.add_argument('--table', default='node_data', help="Internal simulation group name context.")
    parser.add_argument('--sets', default='0-50', help="Range of folder parameter settings to scan (e.g., 0-50).")
    parser.add_argument('--runs', default='1-10', help="Range of stochastic simulation runs to load (e.g., 1-10).")
    parser.add_argument('--workers', type=int, default=4, help="Maximum number of parallel extraction worker tasks.")
    parser.add_argument('--stride', type=int, default=1, help="N-th time step data filter reduction scale factor.")
    parser.add_argument('--checkpoint', action='store_true', help="Reuse existing checkpoint files found on disk.")
    parser.add_argument('--format', default='parquet', choices=['parquet', 'feather'], help="Binary storage format.")
    parser.add_argument('--percentile', type=float, default=100.0, help="Percentile threshold to drop extreme outliers.")
    args = parser.parse_args()
    
    # Block libraries from using too many internal threads to optimize CPU usage
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    
    profiler = LiveMemoryProfiler()
    profiler.start()
    
    try:
        metrics_list = [m.strip() for m in args.metric.split(',')]
        for current_metric in metrics_list:
            out_dir = os.path.join(args.output, current_metric)
            os.makedirs(out_dir, exist_ok=True)
            chk_path = os.path.join(out_dir, f"checkpoint_{current_metric}.{args.format}")
            
            # Compile metric streams if no valid checkpoint file is found on disk
            if not (args.checkpoint and os.path.exists(chk_path)):
                stream_metric_data_to_file(
                    args.input, args.table, current_metric, 
                    [int(x) for x in args.sets.split('-')], 
                    [int(x) for x in args.runs.split('-')], 
                    args.workers, args.stride, chk_path, args.format
                )
            else:
                print(f"[INFO] Found an active checkpoint file on disk. Bypassing extraction step: {chk_path}")
            
            # Execute zero-copy plotting engine using optimized routines
            generate_bifurcation_plots(chk_path, current_metric, out_dir, args.format, args.percentile)
            
    finally:
        max_ram = profiler.stop()
        print(f"\n================================================================================")
        print(f"[PROFILE] Peak Script Memory Allocation Footprint: {max_ram:.4f} GB")
        print(f"================================================================================\n")
