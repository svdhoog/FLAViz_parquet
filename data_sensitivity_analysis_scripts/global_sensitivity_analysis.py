#!/usr/bin/env python3
import os
import re
import gc
import sys
import time
import argparse
import threading
import multiprocessing
import numpy as np
import pandas as pd

# Try importing psutil gracefully to prevent hard crashes if uninstalled
try:
    import psutil
except ImportError:
    print("[-] Error: 'psutil' package is required for real-time memory profiling.")
    print("    Please run: pip install psutil")
    sys.exit(1)

# Try importing pyarrow gracefully for memory-efficient caching
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import pyarrow.feather as feather
except ImportError:
    print("[-] Warning: PyArrow components missing. Checkpoint streaming will have limited optimization.")

# ==========================================
# ASYNCHRONOUS ONLINE MEMORY TELEMETRY ENGINE
# ==========================================
class LiveMemoryProfiler(threading.Thread):
    """
    Runs an isolated background thread to sample active RAM/Swap metrics 
    periodically, writing telemetry straight to an on-disk CSV to track 
    resource footprints per metric channel.
    """
    def __init__(self, log_path="gsa_memory_profile.csv", interval_sec=2.0):
        super().__init__()
        self.log_path = log_path
        self.interval_sec = interval_sec
        self.daemon = True  # Instantly exits if the main thread terminates/crashes
        self.is_running = True
        
    def run(self):
        process = psutil.Process(os.getpid())
        
        # Initialize the telemetry CSV log file with explicit headers
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write("timestamp,elapsed_sec,ram_used_gb,ram_percent,swap_used_gb\n")
            
        start_time = time.time()
        while self.is_running:
            try:
                # Target process specific Resident Set Size (RSS) physical memory footprint
                mem_info = process.memory_info()
                swap_info = psutil.swap_memory()
                
                elapsed = time.time() - start_time
                ram_gb = mem_info.rss / (1024 ** 3)  # Bytes to Gigabytes
                swap_gb = swap_info.used / (1024 ** 3)
                
                # Global total system virtualization saturation rate
                ram_pct = psutil.virtual_memory().percent
                
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(f"{time.time()},{elapsed:.2f},{ram_gb:.3f},{ram_pct:.1f},{swap_gb:.3f}\n")
                    
            except Exception:
                pass  # Do not block processing loops if a sampling collision occurs
            time.sleep(self.interval_sec)
            
    def stop(self):
        self.is_running = False

# ==========================================
# PARALLEL WORKER COMPONENT STUBS
# ==========================================
def init_worker():
    """Initializer hook for subprocess pools to manage clean signals."""
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def is_in_range(folder_name, target_range):
    """Checks if a given folder ID matches requested boundaries (e.g., set_10)."""
    match = re.search(r'\d+', folder_name)
    if not match or not target_range:
        return True
    val = int(match.group())
    return target_range[0] <= val <= target_range[1]

def read_single_parquet_raw_stream(args):
    """
    Isolated file parser passed to parallel workers.
    Downsamples indices inside the worker to prevent RAM overload.
    """
    file_path, set_id, run_id, metric, stride = args
    try:
        # High-performance selective column read via pyarrow engines
        table = pq.read_table(file_path, columns=[metric])
        y_raw = table.column(metric).to_numpy()
        
        # Apply worker-stage stride filter slicing
        if stride > 1:
            y_raw = y_raw[::stride]
            
        return {'set_id': set_id, 'run_id': run_id, 'y': y_raw}
    except Exception as e:
        print(f"[-] Error parsing target file {file_path}: {e}")
        return None

# ==========================================
# CORE DIRECT-TO-DISK STREAMING COMPILER
# ==========================================
def stream_metric_data_to_file(root_dir, table_name, metric, set_range, run_range, num_workers, stride, output_checkpoint_path, format_type):
    """
    Extracts multi-run arrays via parallel workers, flushing blocks progressively
    to the filesystem to enforce a flat physical memory blueprint.
    """
    target_file = f"data_{table_name}.parquet"
    scan_queue = []
    
    print(f"[*] Crawling simulation directory space for target: '{target_file}'")
    for root, _, files in os.walk(root_dir):
        if target_file in files:
            parts = root.replace("\\", "/").split("/")
            set_match = [p for p in parts if re.match(r'^set_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
            run_match = [p for p in parts if re.match(r'^run_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
            
            if set_match and run_match:
                if is_in_range(set_match[-1], set_range) and is_in_range(run_match[-1], run_range):
                    scan_queue.append((os.path.join(root, target_file), set_match[-1], run_match[-1], metric, stride))
                    
    total_targets = len(scan_queue)
    if total_targets == 0:
        raise ValueError(f"Zero target files matched validation parameters for metric: {metric}")

    schema = pa.schema([
        ('set_id', pa.string()),
        (metric, pa.float64())
    ])

    print(f"   -> Processing {total_targets} files in disk-streaming mode...")

    writer = None
    if format_type == 'parquet':
        writer = pq.ParquetWriter(output_checkpoint_path, schema)

    batches = []
    chunk_size_threshold = 500000  # Progressive disk dump threshold (500k rows)
    accumulated_rows = 0

    with multiprocessing.Pool(processes=num_workers, initializer=init_worker, maxtasksperchild=500) as pool:
        results = pool.imap_unordered(read_single_parquet_raw_stream, scan_queue, chunksize=50)
        
        for idx, item in enumerate(results, 1):
            if item is not None and len(item['y']) > 0:
                match = re.search(r'\d+', str(item['set_id']))
                clean_set_id = f"set_{int(match.group())}" if match else item['set_id']
                
                y_array = np.array(item['y'], dtype=np.float64)
                id_array = np.repeat(clean_set_id, len(y_array))
                
                batch = pa.RecordBatch.from_arrays([id_array, y_array], schema=schema)
                batches.append(batch)
                accumulated_rows += len(y_array)

                if accumulated_rows >= chunk_size_threshold:
                    table_chunk = pa.Table.from_record_batches(batches)
                    if format_type == 'parquet':
                        writer.write_table(table_chunk)
                    batches = []
                    accumulated_rows = 0
                    gc.collect()  # Flush discarded chunks out of active memory scope

    if batches:
        table_chunk = pa.Table.from_record_batches(batches)
        if format_type == 'parquet':
            writer.write_table(table_chunk)
        elif format_type == 'feather':
            feather.write_feather(table_chunk, output_checkpoint_path)

    if format_type == 'parquet' and writer is not None:
        writer.close()
        
    print(f"[+] Direct-to-disk streaming cache complete for: {metric}")

# ==========================================
# RENDERING PLOT LOOPS (MEMORY-CONTROLLED)
# ==========================================
def generate_bifurcation_plots(checkpoint_path, metric, format_type, output_dir, style):
    """
    Loads data from structured serialization blocks, drawing single parameter paths 
    sequentially with strict Matplotlib canvas tearing tracking.
    """
    print(f"[*] Extracting visualization frame context from: {checkpoint_path}")
    if format_type == 'parquet':
        df = pq.read_table(checkpoint_path).to_pandas()
    else:
        df = feather.read_feather(checkpoint_path)
        
    # Lazy load Matplotlib strictly inside rendering function context
    import matplotlib
    matplotlib.use('Agg')  # Headless backend prevents window tracking context overhead
    import matplotlib.pyplot as plt

    # Extract clean integers from set labels for correct coordinate assignment
    df['set_num'] = df['set_id'].str.extract(r'(\d+)').astype(int)
    
    # Identify unique parameter blocks (e.g., alpha, beta) mapped out across parameter sets
    unique_sets = df['set_num'].unique()
    
    print(f"[*] Rendering visualization channels across {len(unique_sets)} assigned domains...")
    
    # Mock loop showcasing isolated single canvas layout
    for parameter_channel in ['alpha', 'beta']:
        if style in ['color', 'color-and-greyscale']:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Executing scatter operations using low opacity maps to balance alpha layers
            ax.scatter(df['set_num'], df[metric], alpha=0.05, s=0.5, c='#1f77b4', edgecolors='none')
            ax.set_title(f"GSA Bifurcation Mapping - Parameter Channel: {parameter_channel.upper()}")
            ax.set_xlabel("Parameter Set Configuration Array")
            ax.set_ylabel(f"Extracted Dynamic Space: {metric}")
            
            out_img = os.path.join(output_dir, f"bifurcation_{metric}_{parameter_channel}_color.png")
            plt.savefig(out_img, dpi=150, format='png')
            print(f"   -> Successfully deployed single plot: {out_img}")
            
            # Explicit canvas tearing layout
            plt.clf()
            plt.close(fig)
            plt.close('all')
            del fig, ax
            gc.collect()

# ==========================================
# PARSER UTILITIES & APPLICATION RUNTIME
# ==========================================
def parse_range(arg_str):
    if not arg_str:
        return None
    nums = list(map(int, arg_str.split('-')))
    return (nums[0], nums[1]) if len(nums) == 2 else (nums[0], nums[0])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="GSA Bifurcation Pipeline with Live Memory Logging")
    parser.add_argument('--input', required=True, help="Root path to simulation data tree")
    parser.add_argument('--parameters', required=True, help="Path to targeted configurations parameters file")
    parser.add_argument('--table', required=True, help="Data table baseline identifier string (e.g., Eurostat)")
    parser.add_argument('--metric', required=True, help="Comma-separated tracking targets")
    parser.add_argument('--output', required=True, help="Global destination root path for output arrays")
    parser.add_argument('--style', default='color', choices=['color', 'greyscale', 'color-and-greyscale'])
    parser.add_argument('--sets', required=True, help="Range format filter (e.g., 1-513)")
    parser.add_argument('--runs', required=True, help="Range format filter (e.g., 1-200)")
    parser.add_argument('--workers', type=int, default=1, help="Parallel processing allocation pools")
    parser.add_argument('--stride', type=int, default=1, help="Downsampling window filter step index")
    parser.add_argument('--checkpoint', action='store_true', help="Activates automated data cache engines")
    parser.add_argument('--format', default='parquet', choices=['feather', 'parquet'], help="Serialization standard type")
    
    args = parser.parse_args()
    
    set_bounds = parse_range(args.sets)
    run_bounds = parse_range(args.runs)
    metrics_list = [m.strip() for m in args.metric.split(',')]

    # ==========================================
    # STARTING THE ONLINE TELEMETRY BUFFER
    # ==========================================
    print("[*] Initializing live memory telemetry engine...")
    profiler = LiveMemoryProfiler(log_path="gsa_memory_profile.csv", interval_sec=2.0)
    profiler.start()
    
    try:
        for current_metric in metrics_list:
            print(f"\n" + "="*60)
            print(f"[*] Launching analytical context execution for metric: '{current_metric}'")
            print("="*60)
            
            metric_output_dir = os.path.join(args.output, current_metric)
            os.makedirs(metric_output_dir, exist_ok=True)
            
            ext = 'feather' if args.format == 'feather' else 'parquet'
            checkpoint_file_name = f"checkpoint_{current_metric}.{ext}"
            checkpoint_full_path = os.path.join(metric_output_dir, checkpoint_file_name)
            
            # Cache Engine Logic Checking
            if args.checkpoint and os.path.exists(checkpoint_full_path):
                print(f"[+] Automated Cache Hit found. Skipping tracking crawl for: {checkpoint_full_path}")
            else:
                print(f"[-] Cache Miss or caching bypassed. Commencing pipeline streaming profile.")
                stream_metric_data_to_file(
                    root_dir=args.input,
                    table_name=args.table,
                    metric=current_metric,
                    set_range=set_bounds,
                    run_range=run_bounds,
                    num_workers=args.workers,
                    stride=args.stride,
                    output_checkpoint_path=checkpoint_full_path,
                    format_type=args.format
                )
                
            # Visualization Phase
            generate_bifurcation_plots(
                checkpoint_path=checkpoint_full_path,
                metric=current_metric,
                format_type=args.format,
                output_dir=metric_output_dir,
                style=args.style
            )
            
    except KeyboardInterrupt:
        print("\n[-] Process aborted via user interrupt command sequence.")
    finally:
        # ==========================================
        # CLEANUP THE TELEMETRY BUFFER SECURELY
        # ==========================================
        print("\n[*] Halting memory telemetry engine. Saving metrics log...")
        profiler.stop()
        profiler.join(timeout=5.0)
        print("[+] Log processing complete. Review performance logs inside 'gsa_memory_profile.csv'")
