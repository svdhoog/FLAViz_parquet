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
       
    3. [Strict Worker Scaling Strategy]: Throttles concurrency to maintain 
       stable memory footprints under high data-load volumes.
       
    4. [Percentile Clipping]: Integrates a `--percentile` threshold filter to 
       truncate extreme stochastic outliers (e.g., 1e285) that would otherwise 
       obfuscate bifurcation attractors.

    5. [Integer Key Optimization]: Replaces high-overhead string tracking IDs 
       ('set_id') with primitive 16-bit integers ('set_num') inside both Parquet 
       and Feather file schemas. This eliminates multi-gigabyte string object bloat.

    6. [Direct Arrow Zero-Copy Plotting]: Bypasses Pandas DataFrames and 
       relational merge lookups entirely during plotting. Memory-mapped PyArrow 
       tables supply data vectors directly to Matplotlib using fast, zero-copy 
       NumPy views.

    7. [Single-Precision Downcasting (float32)]: Downcasts metric values and 
       mapped parameter vectors to 32-bit floats, keeping memory footprints 
       minimized during analysis execution.

    8. [Density-Binned Rainbow Heatmaps & Downsampled Scatter Plotting]: 
       Introduces 2D density histograms with a 500x500 mesh resolution and 
       the 'turbo' rainbow colormap. Provides a fallback scatter mode capped at 
       5,000,000 points to completely isolate the execution from OOM failures.
       
    9. [Targeted Path Synthesis Lookup]: Bypasses sequential `os.walk` scans 
       by generating direct structural wildcards relative to the `--input` root.
"""

import os
import re
import gc
import sys
import time
import argparse
import glob
import threading
import multiprocessing
import numpy as np
import pandas as pd

# Graceful import handling
try:
    import psutil
except ImportError:
    print("[-] Error: 'psutil' package is required.")
    sys.exit(1)

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pyarrow.feather as feather
    import pyarrow.compute as pc
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False
    print("[-] Warning: PyArrow missing. Checkpoint streaming disabled.")

# ==========================================
# ASYNCHRONOUS ONLINE MEMORY TELEMETRY ENGINE
# ==========================================
class LiveMemoryProfiler(threading.Thread):
    def __init__(self, log_path="gsa_memory_profile.csv", interval_sec=2.0):
        super().__init__()
        self.log_path = log_path
        self.interval_sec = interval_sec
        self.daemon = True
        self.is_running = True
        
    def run(self):
        process = psutil.Process(os.getpid())
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("timestamp,elapsed_sec,ram_used_gb,ram_percent,swap_used_gb\n")
        start_time = time.time()
        while self.is_running:
            try:
                mem_info = process.memory_info()
                swap_info = psutil.swap_memory()
                elapsed = time.time() - start_time
                ram_gb = mem_info.rss / (1024 ** 3)
                swap_gb = swap_info.used / (1024 ** 3)
                ram_pct = psutil.virtual_memory().percent
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(f"{time.time()},{elapsed:.2f},{ram_gb:.3f},{ram_pct:.1f},{swap_gb:.3f}\n")
            except Exception: pass
            time.sleep(self.interval_sec)
            
    def stop(self):
        self.is_running = False

# ==========================================
# STREAMING COMPILER & RENDERING ROUTINES
# ==========================================
def init_worker():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def read_single_parquet_raw_stream(args):
    file_path, set_id, run_id, metric, stride = args
    try:
        table = pq.read_table(file_path, columns=[metric])
        # Downcast to float32 natively at extraction time to yield immediate 50% memory savings
        y_raw = table.column(metric).to_numpy().astype(np.float32)
        if stride > 1: y_raw = y_raw[::stride]
        return {'set_id': set_id, 'run_id': run_id, 'y': y_raw}
    except Exception: return None

def stream_metric_data_to_file(root_dir, table_name, metric, set_range, run_range, num_workers, stride, output_checkpoint_path, format_type):
    target_file = f"data_{table_name}.parquet"
    scan_queue = []
    
    # SYSTEM OPTIMIZATION: Predict direct structure based on the --input (root_dir) parameter layout
    search_pattern = os.path.join(root_dir, "set_*", "run_*", target_file).replace("\\", "/")
    print(f"[INFO] Scanning filesystem via targeted pattern layout: {search_pattern}")
    
    for file_path in glob.iglob(search_pattern):
        clean_path = file_path.replace("\\", "/")
        parts = clean_path.split("/")
        
        # Parse structural context attributes directly out of file tokens
        s_folders = [p for p in parts if re.match(r'^set_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
        r_folders = [p for p in parts if re.match(r'^run_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
        
        if s_folders and r_folders:
            s_val = int(re.search(r'\d+', s_folders[-1]).group())
            r_val = int(re.search(r'\d+', r_folders[-1]).group())
            
            # Filter rows based on command-line scenario scale bounds
            if (set_range[0] <= s_val <= set_range[1]) and (run_range[0] <= r_val <= run_range[1]):
                scan_queue.append((file_path, s_folders[-1], r_folders[-1], metric, stride))
                
    total_files = len(scan_queue)
    print(f"[INFO] Ingestion queue populated with {total_files} file targets.")
    if total_files == 0:
        print("[-] Error: No matching simulation source files located. Check your path variables.")
        sys.exit(1)
    
    # SCHEMA OPTIMIZATION: int16 tracking keys and float32 data representations
    schema = pa.schema([('set_num', pa.int16()), (metric, pa.float32())])
    
    if format_type == 'parquet':
        writer = pq.ParquetWriter(output_checkpoint_path, schema)
    else:
        sink = pa.OSFile(output_checkpoint_path, 'wb')
        writer = pa.ipc.RecordBatchFileWriter(sink, schema)
        
    batches, accumulated_rows = [], 0
    chunk_write_boundary = 5000000  # OPTIMIZATION: Higher chunk ceiling saves output write coordination overhead

    with multiprocessing.Pool(processes=num_workers, initializer=init_worker, maxtasksperchild=500) as pool:
        for item in pool.imap_unordered(read_single_parquet_raw_stream, scan_queue, chunksize=50):
            if item is not None and len(item['y']) > 0:
                match = re.search(r'\d+', str(item['set_id']))
                clean_set_num = int(match.group()) if match else 0
                
                # Construct dense contiguous numerical arrays instead of string sequences
                set_num_array = np.repeat(clean_set_num, len(item['y'])).astype(np.int16())
                
                batch = pa.RecordBatch.from_arrays([set_num_array, item['y']], schema=schema)
                batches.append(batch)
                accumulated_rows += len(item['y'])
                
                # DUAL-FORMAT STREAMING: Stream chunks properly aligned with file layout expectations
                if accumulated_rows >= chunk_write_boundary:
                    if format_type == 'parquet':
                        table_chunk = pa.Table.from_batches(batches)
                        writer.write_table(table_chunk)
                    else:
                        for b in batches: 
                            writer.write_batch(b)
                    batches, accumulated_rows = [], 0
                    gc.collect()

    # Flush final leftovers
    if batches:
        if format_type == 'parquet':
            table_chunk = pa.Table.from_batches(batches)
            writer.write_table(table_chunk)
        else:
            for b in batches: 
                writer.write_batch(b)

    writer.close()
    if format_type != 'parquet':
        sink.close()

def generate_bifurcation_plots(checkpoint_path, metric, format_type, output_dir, style, parameters_file_path, percentile_limit):
    if not HAS_PYARROW: return
    
    # ZERO-COPY READ: Load checkpoint data using native PyArrow tables (Memory-mapped)
    if format_type == 'parquet':
        table = pq.read_table(checkpoint_path)
    else:
        with pa.memory_map(checkpoint_path, 'rb') as source:
            table = pa.ipc.RecordBatchFileReader(source).read_all()
            
    # CRITICAL SAFEGUARD: Verify that checkpoint schema matches current engine requirements
    if 'set_num' not in table.column_names:
        raise ValueError(
            f"Schema mismatch in checkpoint file '{checkpoint_path}'.\n"
            f"Available columns: {table.column_names}.\n"
            f"Fix: Delete this stale checkpoint file and re-run to reconstruct it with the correct fields."
        )
            
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    
    # Load parameters lookup reference file into a small reference DataFrame
    param_meta_df = pd.read_csv(parameters_file_path)
    
    # Convert parameters lookup alignment keys to standard index offsets
    if 'set_num' in param_meta_df.columns:
        if param_meta_df['set_num'].dtype == object:
            param_meta_df['set_num'] = param_meta_df['set_num'].astype(str).str.extract(r'(\d+)').astype(int)
        else:
            param_meta_df['set_num'] = param_meta_df['set_num'].astype(int)
        # Re-index the metadata dataframe by set_num to handle fast array lookups
        param_meta_df = param_meta_df.set_index('set_num').reindex(range(1, param_meta_df['set_num'].max() + 1))
    
    # Convert Arrow columns into zero-copy numpy views
    set_num_array = table['set_num'].to_numpy()
    metric_array = table[metric].to_numpy()
    
    # Percentile filter for outlier suppression using numpy primitives
    if percentile_limit < 100:
        threshold = np.percentile(metric_array, percentile_limit)
        valid_mask = metric_array <= threshold
        set_num_array = set_num_array[valid_mask]
        metric_array = metric_array[valid_mask]

    economic_parameters = [c for c in param_meta_df.columns if c not in {'run_num', 'time_step', 'set_id', metric}]
    
    for param_name in economic_parameters:
        # OPTIMIZATION A: Force float32 mapping to prevent 64-bit vector memory inflation
        mapped_param = param_meta_df[param_name].values.astype(np.float32)[set_num_array - 1]
        
        # Determine active visualization style modes
        if style == 'color-and-greyscale':
            render_styles = ['color', 'greyscale']
        else:
            render_styles = [style]
            
        for current_style in render_styles:
            fig, ax = plt.subplots(figsize=(11, 6))
            
            # OPTIMIZATION C: 2D Density Binned Plotting Layout
            if current_style == 'color':
                # BINS: 500x500 Mesh Grid Resolution
                # CMAP: 'turbo' Google Perceptually Uniform Rainbow Heatmap (Purple -> Blue -> Green -> Yellow -> Red)
                # NORM: LogNorm ensures low-density chaotic tracking paths aren't hidden by dense core attractors
                counts, xedges, yedges, im = ax.hist2d(
                    mapped_param, metric_array, 
                    bins=500, 
                    cmap='turbo', 
                    norm=mcolors.LogNorm(),
                    cmin=1
                )
                cbar = fig.colorbar(im, ax=ax, pad=0.02)
                cbar.set_label('Stochastic Point Density (Log Scale)', fontsize=10)
                ax.set_title(f"GSA Heatmap - {param_name.upper()} (Turbo Rainbow)", fontsize=12, fontweight='bold')
                
            elif current_style == 'greyscale':
                counts, xedges, yedges, im = ax.hist2d(
                    mapped_param, metric_array, 
                    bins=500, 
                    cmap='gray_r', 
                    norm=mcolors.LogNorm(),
                    cmin=1
                )
                cbar = fig.colorbar(im, ax=ax, pad=0.02)
                cbar.set_label('Stochastic Point Density (Log Scale)', fontsize=10)
                ax.set_title(f"GSA Heatmap - {param_name.upper()} (Greyscale)", fontsize=12, fontweight='bold')
                
            elif current_style == 'scatter':
                # OPTIMIZATION B: High-Fidelity Downsampling Guardrail (Caps scatter tracking to exactly 5 Million Points max)
                MAX_PLOT_POINTS = 5_000_000
                if len(metric_array) > MAX_PLOT_POINTS:
                    rng = np.random.default_rng(seed=42)
                    sample_indices = rng.choice(len(metric_array), size=MAX_PLOT_POINTS, replace=False)
                    scat_x = mapped_param[sample_indices]
                    scat_y = metric_array[sample_indices]
                else:
                    scat_x = mapped_param
                    scat_y = metric_array
                    
                ax.scatter(scat_x, scat_y, alpha=0.04, s=0.4, c='#1f77b4', edgecolors='none')
                ax.set_title(f"GSA Scatter Bifurcation - {param_name.upper()} (Downsampled to 5M Points Max)", fontsize=12, fontweight='bold')

            ax.set_xlabel(f"Economic Input: {param_name}")
            ax.set_ylabel(f"Dynamic Space: {metric}")
            ax.grid(True, linestyle='--', alpha=0.2)
            
            plt.savefig(os.path.join(output_dir, f"bifurcation_{metric}_{param_name}_{current_style}.png"), dpi=150, bbox_inches='tight')
            plt.clf(); plt.close('all'); gc.collect()

# ==========================================
# RUNTIME ENTRY POINT
# ==========================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True); parser.add_argument('--parameters', required=True)
    parser.add_argument('--table', required=True); parser.add_argument('--metric', required=True)
    parser.add_argument('--output', required=True); parser.add_argument('--style', default='color')
    parser.add_argument('--sets', required=True); parser.add_argument('--runs', required=True)
    parser.add_argument('--workers', type=int, default=1); parser.add_argument('--stride', type=int, default=1)
    parser.add_argument('--checkpoint', action='store_true'); parser.add_argument('--format', default='parquet')
    parser.add_argument('--percentile', type=float, default=100)
    args = parser.parse_args()
    
    # Block internal computational library execution hooks to prevent 2-core CPU context-switch choking
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    
    profiler = LiveMemoryProfiler(); profiler.start()
    try:
        for current_metric in [m.strip() for m in args.metric.split(',')]:
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
            
            # Execute zero-copy plotting engine using optimized routines
            generate_bifurcation_plots(chk_path, current_metric, args.format, out_dir, args.style, args.parameters, args.percentile)
    finally:
        profiler.stop(); profiler.join()