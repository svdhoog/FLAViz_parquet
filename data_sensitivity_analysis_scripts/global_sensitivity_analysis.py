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
"""

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
        y_raw = table.column(metric).to_numpy()
        if stride > 1: y_raw = y_raw[::stride]
        return {'set_id': set_id, 'run_id': run_id, 'y': y_raw}
    except Exception: return None

def stream_metric_data_to_file(root_dir, table_name, metric, set_range, run_range, num_workers, stride, output_checkpoint_path, format_type):
    target_file = f"data_{table_name}.parquet"
    scan_queue = []
    for root, _, files in os.walk(root_dir):
        if target_file in files:
            parts = root.replace("\\", "/").split("/")
            s = [p for p in parts if re.match(r'^set_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
            r = [p for p in parts if re.match(r'^run_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
            if s and r:
                s_val = int(re.search(r'\d+', s[-1]).group())
                if set_range[0] <= s_val <= set_range[1]:
                    scan_queue.append((os.path.join(root, target_file), s[-1], r[-1], metric, stride))
    
    schema = pa.schema([('set_id', pa.string()), (metric, pa.float64())])
    writer = pq.ParquetWriter(output_checkpoint_path, schema) if format_type == 'parquet' else None
    batches, accumulated_rows = [], 0

    with multiprocessing.Pool(processes=num_workers, initializer=init_worker, maxtasksperchild=500) as pool:
        for item in pool.imap_unordered(read_single_parquet_raw_stream, scan_queue, chunksize=50):
            if item is not None and len(item['y']) > 0:
                match = re.search(r'\d+', str(item['set_id']))
                clean_set_id = f"set_{int(match.group())}" if match else item['set_id']
                batch = pa.RecordBatch.from_arrays([np.repeat(clean_set_id, len(item['y'])), item['y']], schema=schema)
                batches.append(batch)
                accumulated_rows += len(item['y'])
                if format_type == 'parquet' and accumulated_rows >= 500000:
                    writer.write_table(pa.Table.from_batches(batches))
                    batches, accumulated_rows = [], 0
                    gc.collect()

    table_chunk = pa.Table.from_batches(batches)
    if format_type == 'parquet':
        writer.write_table(table_chunk)
        writer.close()
    else: feather.write_feather(table_chunk, output_checkpoint_path)

def generate_bifurcation_plots(checkpoint_path, metric, format_type, output_dir, style, parameters_file_path, percentile_limit):
    if not HAS_PYARROW: return
    df = pq.read_table(checkpoint_path).to_pandas() if format_type == 'parquet' else feather.read_feather(checkpoint_path)
    
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    
    df['set_num'] = df['set_id'].str.extract(r'(\d+)').astype(int)
    param_meta_df = pd.read_csv(parameters_file_path)
    
    # Coerce index for safe merge
    if 'set_num' not in param_meta_df.columns:
        param_meta_df['set_num'] = param_meta_df.index + 1
    else:
        param_meta_df['set_num'] = param_meta_df['set_num'].astype(str).str.extract(r'(\d+)').astype(int)

    df = df.merge(param_meta_df, on='set_num', how='left')
    
    # Percentile filter for outlier suppression
    if percentile_limit < 100:
        threshold = df[metric].quantile(percentile_limit / 100)
        df = df[df[metric] <= threshold]

    economic_parameters = [c for c in param_meta_df.columns if c not in {'set_num', 'run_num', 'time_step', 'set_id', metric}]
    
    for param_name in economic_parameters:
        for current_style in (['color', 'greyscale'] if style == 'color-and-greyscale' else [style]):
            fig, ax = plt.subplots(figsize=(11, 6))
            ax.scatter(df[param_name], df[metric], alpha=0.04, s=0.4, c='#1f77b4' if current_style == 'color' else '#404040', edgecolors='none')
            ax.set_title(f"GSA Bifurcation Mapping - {param_name.upper()} ({current_style.capitalize()})", fontsize=12, fontweight='bold')
            ax.set_xlabel(f"Economic Input: {param_name}"); ax.set_ylabel(f"Dynamic Space: {metric}"); ax.grid(True, linestyle='--', alpha=0.3)
            plt.savefig(os.path.join(output_dir, f"bifurcation_{metric}_{param_name}_{current_style}.png"), dpi=150, bbox_inches='tight')
            plt.clf(); plt.close('all'); gc.collect()

# ==========================================
# RUNTIME
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
    
    profiler = LiveMemoryProfiler(); profiler.start()
    try:
        for current_metric in [m.strip() for m in args.metric.split(',')]:
            out_dir = os.path.join(args.output, current_metric)
            os.makedirs(out_dir, exist_ok=True)
            chk_path = os.path.join(out_dir, f"checkpoint_{current_metric}.{args.format}")
            
            if not (args.checkpoint and os.path.exists(chk_path)):
                stream_metric_data_to_file(args.input, args.table, current_metric, [int(x) for x in args.sets.split('-')], [int(x) for x in args.runs.split('-')], args.workers, args.stride, chk_path, args.format)
            
            generate_bifurcation_plots(chk_path, current_metric, args.format, out_dir, args.style, args.parameters, args.percentile)
    finally:
        profiler.stop(); profiler.join()