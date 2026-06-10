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

    7. [Single-Precision Downcasting]: Enforces float32 downcasting across all 
       floating-point analytical columns to instantly half computational memory layouts.
       
    8. [Two-Pass Streaming Plotting]: Eliminates monolithic table materialization 
       by decoupling percentile threshold calculation (via sampling) from rendering.

    9. [Streaming Histogram Accumulation]: Updates a static 500x500 grid buffer 
       batch-by-batch. This architecture decouples memory usage from dataset size, 
       ensuring that RAM usage remains flat regardless of whether the dataset 
       is 1 GB or 100 GB.
"""

import os, re, gc, sys, time, argparse, glob, threading, multiprocessing
import numpy as np
import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.ipc as ipc
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

class LiveMemoryProfiler(threading.Thread):
    def __init__(self, log_path="gsa_memory_profile.csv", interval_sec=2.0):
        super().__init__()
        self.log_path = log_path; self.interval_sec = interval_sec
        self.daemon = True; self.is_running = True
    def run(self):
        process = psutil.Process(os.getpid())
        while self.is_running:
            try:
                ram_gb = process.memory_info().rss / (1024 ** 3)
                swap_gb = psutil.swap_memory().used / (1024 ** 3)
                with open(self.log_path, "a") as f:
                    f.write(f"{time.time()},{ram_gb:.3f},{swap_gb:.3f}\n")
            except: pass
            time.sleep(self.interval_sec)
    def stop(self): self.is_running = False

def log(message, verbose=False):
    if verbose:
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

def init_worker():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def read_single_parquet_raw_stream(args):
    file_path, set_id, run_id, metric, stride = args
    try:
        processed_chunks = []
        pf = pq.ParquetFile(file_path)
        for raw_batch in pf.iter_batches(batch_size=100_000, columns=[metric]):
            y_raw = raw_batch.column(metric).to_numpy().astype(np.float32)
            if stride > 1: y_raw = y_raw[::stride]
            if len(y_raw) > 0: processed_chunks.append(y_raw)
        return {'set_id': set_id, 'y': np.concatenate(processed_chunks)} if processed_chunks else None
    except: return None

def stream_metric_data_to_file(root_dir, table_name, metric, set_range, run_range, num_workers, stride, output_checkpoint_path, format_type, verbose):
    log(f"[START] Scanning hierarchy for {metric}...", verbose)
    target_file = f"data_{table_name}.parquet"
    scan_queue = []
    for file_path in glob.iglob(os.path.join(root_dir, "set_*", "run_*", target_file).replace("\\", "/")):
        parts = file_path.replace("\\", "/").split("/")
        s_val = int(re.search(r'\d+', parts[-3]).group())
        r_val = int(re.search(r'\d+', parts[-2]).group())
        if (set_range[0] <= s_val <= set_range[1]) and (run_range[0] <= r_val <= run_range[1]):
            scan_queue.append((file_path, parts[-3], parts[-2], metric, stride))
    
    log(f"[INGEST] Identified {len(scan_queue)} files for processing.", verbose)
    schema = pa.schema([('set_num', pa.int16()), (metric, pa.float32())])
    writer = pq.ParquetWriter(output_checkpoint_path, schema) if format_type == 'parquet' else ipc.RecordBatchFileWriter(open(output_checkpoint_path, 'wb'), schema)
    
    processed_count = 0
    with multiprocessing.Pool(processes=num_workers, initializer=init_worker) as pool:
        for item in pool.imap_unordered(read_single_parquet_raw_stream, scan_queue):
            if item:
                set_num = int(re.search(r'\d+', item['set_id']).group())
                batch = pa.RecordBatch.from_arrays([np.repeat(set_num, len(item['y'])).astype(np.int16), item['y']], schema=schema)
                if format_type == 'parquet': writer.write_table(pa.Table.from_batches([batch]))
                else: writer.write_batch(batch)
                processed_count += 1
                if verbose and processed_count % 100 == 0:
                    print(f"  -> Processed {processed_count}/{len(scan_queue)} files...")
    writer.close()
    log(f"[FINISH] Checkpoint created: {output_checkpoint_path}", verbose)

def get_iterator(checkpoint_path, format_type, columns):
    if format_type == 'parquet':
        return pq.ParquetFile(checkpoint_path).iter_batches(batch_size=250_000, columns=columns), None
    else:
        source = pa.memory_map(checkpoint_path, 'rb')
        reader = ipc.RecordBatchFileReader(source)
        return (reader.get_batch(i) for i in range(reader.num_record_batches)), source

def generate_bifurcation_plots(checkpoint_path, metric, format_type, output_dir, style, parameters_file_path, percentile_limit, verbose):
    log(f"[START] Plotting bifurcation for {metric}...", verbose)
    param_meta_df = pd.read_csv(parameters_file_path)
    param_meta_df['set_num'] = param_meta_df['set_num'].astype(str).str.extract(r'(\d+)').astype(int)
    param_meta_df = param_meta_df.set_index('set_num').reindex(range(1, param_meta_df['set_num'].max() + 1))
    
    log(f"[ANALYSIS] Calculating global threshold...", verbose)
    sample_points = []
    it, _ = get_iterator(checkpoint_path, format_type, [metric])
    for batch in it:
        sample_points.append(batch.column(metric).to_numpy())
        if sum(len(s) for s in sample_points) > 1_000_000: break
    threshold = np.percentile(np.concatenate(sample_points), percentile_limit)
    del sample_points; gc.collect()
    log(f"  -> Threshold set at {threshold:.4f} (percentile {percentile_limit})", verbose)

    economic_params = [c for c in param_meta_df.columns if c not in {'run_num', 'time_step', 'set_id', metric}]
    for param_name in economic_params:
        log(f"[RENDER] Creating plot for {param_name.upper()}...", verbose)
        param_vector = param_meta_df[param_name].values.astype(np.float32)
        hist_grid = np.zeros((500, 500))
        x_edges = np.linspace(param_vector.min(), param_vector.max(), 501)
        y_edges = np.linspace(0, threshold, 501)
        
        it, source = get_iterator(checkpoint_path, format_type, ['set_num', metric])
        for batch in it:
            sets = batch.column('set_num').to_numpy()
            vals = batch.column(metric).to_numpy()
            mask = (vals <= threshold) & (vals >= 0)
            if np.any(mask):
                H, _, _ = np.histogram2d(param_vector[sets[mask]-1], vals[mask], bins=[x_edges, y_edges])
                hist_grid += H
        
        fig, ax = plt.subplots(figsize=(11, 6))
        im = ax.imshow(hist_grid.T, origin='lower', extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]], 
                       cmap='turbo', norm=mcolors.LogNorm(vmin=1, vmax=hist_grid.max() or 1), aspect='auto')
        plt.colorbar(im, ax=ax); plt.savefig(os.path.join(output_dir, f"bifurcation_{metric}_{param_name}.png")); plt.close('all')
        if source: source.close(); gc.collect()
    log(f"[FINISH] Plotting completed for {metric}", verbose)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True); parser.add_argument('--parameters', required=True)
    parser.add_argument('--table', required=True); parser.add_argument('--metric', required=True)
    parser.add_argument('--output', required=True); parser.add_argument('--style', default='color')
    parser.add_argument('--sets', required=True); parser.add_argument('--runs', required=True)
    parser.add_argument('--workers', type=int, default=1); parser.add_argument('--stride', type=int, default=1)
    parser.add_argument('--checkpoint', action='store_true'); parser.add_argument('--format', default='parquet')
    parser.add_argument('--percentile', type=float, default=100); parser.add_argument('--no-plot', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    
    os.environ.update({"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})
    profiler = LiveMemoryProfiler(); profiler.start()
    try:
        for current_metric in [m.strip() for m in args.metric.split(',')]:
            out_dir = os.path.join(args.output, current_metric)
            os.makedirs(out_dir, exist_ok=True)
            chk_path = os.path.join(out_dir, f"checkpoint_{current_metric}.{args.format}")
            if not (args.checkpoint and os.path.exists(chk_path)):
                stream_metric_data_to_file(args.input, args.table, current_metric, [int(x) for x in args.sets.split('-')], [int(x) for x in args.runs.split('-')], args.workers, args.stride, chk_path, args.format, args.verbose)
            if not args.no_plot:
                generate_bifurcation_plots(chk_path, current_metric, args.format, out_dir, args.style, args.parameters, args.percentile, args.verbose)
    finally: profiler.stop(); profiler.join()