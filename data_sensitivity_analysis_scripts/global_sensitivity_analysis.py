#!/usr/bin/env python3
"""
================================================================================
Global Sensitivity Analysis (GSA) & Isolated Bifurcation Engine
================================================================================
DESIGN DECISIONS & ARCHITECTURAL EVOLUTION:
    1. [Shift to Bifurcation Mapping]: Abandoned the original approach of 
       compressing simulation runs down to a single statistical point (e.g., 
       np.median). Instead, the engine preserves and maps every individual 
       time-series iteration of every stochastic run against the parameter 
       continuum to uncover phase transitions and attractors.
       
    2. [I/O Optimization via Stride Filters]: Loading raw unaggregated arrays 
       across hundreds of thousands of files presents a massive memory challenge. 
       To mitigate this, a `--stride` parameter was implemented to sample every 
       N-th simulation step natively at the worker stage, dropping the initial 
       data footprint dynamically by 80% or more.
       
    3. [Strict Worker Scaling Strategy]: Parallel worker allocation is throttled 
       and decoupled from total CPU cores (`-w 1` or `-w 2`). This forces a predictable, 
       low-concurrency data stream that keeps the aggregate data frame overhead 
       well below host hardware saturation limits.
       
    4. [Transition to Isolated Parameter Plotting]: Scrapped the multi-panel 
       (8-subplot) grid design. Forcing Matplotlib to hold an 8-panel compound 
       canvas forced it to retain over 82 million vector coordinates in a single 
       uninterruptible process loop, causing Linux OOM (Out-of-Memory) kernel 
       kills. Shifting to isolated, single-parameter plots cuts active canvas 
       memory demands to exactly 1/8th of the original profile.
       
    5. [Aggressive Graphic Engine Garbage Collection]: Matplotlib aggressively 
       caches visual coordinate buffers. The rendering pipeline now executes a 
       strict teardown workflow (`plt.clf()`, `plt.close('all')`, explicit array 
       deletion, and `gc.collect()`) immediately after every single image is 
       written to disk, dropping the memory high-water mark back to baseline 
       before starting the next iteration.

    6. [On-Demand Intermediate Checkpoint Caching]: Integrated a decoupled data 
       block checkpointing layer controlled via the `--checkpoint` boolean flag 
       paired with the `--format` option. When enabled, processed metric arrays 
       are written directly to disk. Sub-sequential script executions skip the 
       heavy, metadata-bound hierarchical folder traversal entirely and load 
       the raw matrices instantaneously. Supports two high-performance columnar formats:
         - 'feather': Maximizes I/O throughput via uncompressed zero-copy memory 
           mapping directly to system RAM (fastest development loop).
         - 'parquet': Maximizes filesystem compression via advanced column encoding 
           schemes, preserving long-term archival footprint at the cost of slight 
           CPU decompression overhead on reload.
================================================================================
"""

import os
import re
import sys
import gc
import signal
import argparse
import multiprocessing
import pandas as pd
import numpy as np
import pyarrow.parquet as pq

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def parse_range_arg(range_str):
    if not range_str:
        return None
    match = re.match(r'^(\d+)-(\d+)$', range_str.strip())
    if not match:
        raise argparse.ArgumentTypeError(f"Range format must be 'start-end'. Got: '{range_str}'")
    return int(match.group(1)), int(match.group(2))

def parse_metrics_arg(metric_input):
    if isinstance(metric_input, list):
        raw_str = "".join(metric_input).strip()
    else:
        raw_str = str(metric_input).strip()

    if raw_str.startswith('[') and raw_str.endswith(']'):
        content = raw_str[1:-1]
        metrics = [m.strip() for m in content.split(',') if m.strip()]
    else:
        metrics = [m.strip() for m in raw_str.replace(',', ' ').split() if m.strip()]
    return metrics

def is_in_range(value_str, range_tuple):
    if range_tuple is None:
        return True
    match = re.search(r'\d+', value_str)
    if not match:
        return False
    return range_tuple[0] <= int(match.group()) <= range_tuple[1]

def load_parameter_design(csv_path, set_range):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Configuration parameter file absent: {csv_path}")
    
    df = pd.read_csv(csv_path, header=None)
    param_definitions = [
        {"symbol": "alpha", "name": "Capital Adequacy Ratio"},
        {"symbol": "beta", "name": "Reserve Requirement Ratio"},
        {"symbol": "gamma", "name": "Price Sensitivity"},
        {"symbol": "d", "name": "Dividend Ratio"},
        {"symbol": "phi", "name": "Debt Rescaling Ratio"},
        {"symbol": "tau", "name": "Tax Rate"},
        {"symbol": "T", "name": "Debt Repayment (months)"},
        {"symbol": "r_ecb", "name": "Base Interest Rate"}
    ]
    param_names = [f"{p['symbol']}" for p in param_definitions]
    rename_dict = {0: 'set_id'}
    for i, name in enumerate(param_names):
        rename_dict[i + 1] = name
        
    df.rename(columns=rename_dict, inplace=True)
    df['set_id'] = df['set_id'].astype(str).str.strip()
    
    if set_range:
        df = df[df['set_id'].apply(lambda x: is_in_range(x, set_range))]
    return df, param_names

def read_single_parquet_raw_stream(task_args):
    file_path, set_id, run_id, single_metric, stride = task_args
    try:
        data_table = pq.read_table(file_path, columns=[single_metric])
        if data_table.num_rows == 0:
            return None
        y_values = data_table.column(single_metric).to_numpy()[::stride]
        return {'set_id': set_id, 'y': y_values}
    except Exception:
        return None

def stream_metric_data(root_dir, table_name, metric, set_range, run_range, num_workers, stride):
    target_file = f"data_{table_name}.parquet"
    scan_queue = []
    
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

    compiled_records = []
    with multiprocessing.Pool(processes=num_workers, initializer=init_worker, maxtasksperchild=500) as pool:
        results = pool.imap_unordered(read_single_parquet_raw_stream, scan_queue, chunksize=50)
        for idx, item in enumerate(results, 1):
            if item is not None:
                compiled_records.append(item)
                
    flat_set_ids = []
    flat_y_values = []
    for r in compiled_records:
        flat_set_ids.extend([r['set_id']] * len(r['y']))
        flat_y_values.extend(r['y'])
        
    return pd.DataFrame({'set_id': flat_set_ids, metric: flat_y_values})

def plot_bifurcation_panel(df_merged, param_col, target_metric, style, save_path):
    fig, ax = plt.subplots(figsize=(8, 6))
    x = df_merged[param_col].values
    y = df_merged[target_metric].values

    if style == 'greyscale':
        ax.scatter(x, y, alpha=0.02, s=0.08, color='#111111', rasterized=True)
        title_suffix = "(Monochrome Mode)"
    else:
        counts, xedges, yedges = np.histogram2d(x, y, bins=[100, 200])
        x_bins = np.clip(np.digitize(x, xedges) - 1, 0, counts.shape[0] - 1)
        y_bins = np.clip(np.digitize(y, yedges) - 1, 0, counts.shape[1] - 1)
        densities = counts[x_bins, y_bins]
        
        idx = densities.argsort()
        x_sort, y_sort, d_sort = x[idx], y[idx], densities[idx]
        
        scatter = ax.scatter(x_sort, y_sort, c=d_sort, cmap='inferno', 
                             norm=LogNorm(vmin=1, vmax=max(2, densities.max())),
                             s=0.15, alpha=0.4, rasterized=True)
        fig.colorbar(scatter, ax=ax, label='Relative State Point Density (Log Scale)')
        title_suffix = "(Probability Density Mode)"

    ax.set_title(f"Empirical Bifurcation Space: {param_col} vs {target_metric}\n{title_suffix}", fontsize=11)
    ax.set_xlabel(f"Economic Parameter Range: {param_col}", fontsize=10)
    ax.set_ylabel(target_metric, fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.2)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    
    plt.clf()
    plt.close(fig)
    plt.close('all')
    del x, y
    gc.collect()

def main():
    parser = argparse.ArgumentParser(description="Memory-Isolated Parallel Bifurcation Space Engine.")
    parser.add_argument('-i', '--input', required=True, help="Path to the mirrored Parquet folder root.")
    parser.add_argument('-p', '--parameters', required=True, help="Path to CSV parameters file.")
    parser.add_argument('-t', '--table', required=True, help="Name of the inner agent database table.")
    parser.add_argument('-m', '--metric', required=True, nargs='+', type=parse_metrics_arg)
    parser.add_argument('-s', '--style', choices=['color', 'greyscale', 'color-and-greyscale'], default='color')
    
    # NEW OPTION FLAG: Elect whether to leverage checkpoint read/writes at all
    parser.add_argument('-c', '--checkpoint', action='store_true',
                        help="Toggle switch to activate intermediate disk file serialization checkpointing.")
    
    # Format selection flag (ordered exactly after the checkpoint parameter toggle)
    parser.add_argument('-f', '--format', choices=['feather', 'parquet'], default='feather',
                        help="Disk checkpoint serialization standard format for intermediate arrays (default: feather).")
    
    parser.add_argument('-o', '--output', default=None, help="Output destination folder configuration file.")
    parser.add_argument('--sets', type=parse_range_arg)
    parser.add_argument('--runs', type=parse_range_arg)
    parser.add_argument('-w', '--workers', type=int, default=multiprocessing.cpu_count())
    parser.add_argument('--stride', type=int, default=5, help="Time series index sampling filter.")
    
    args = parser.parse_args()
    metrics_list = [m for sublist in args.metric for m in sublist]
    metrics_list = list(dict.fromkeys(metrics_list))
    
    try:
        df_params, verified_cols = load_parameter_design(args.parameters, args.sets)
        
        def format_set_id(x):
            match = re.search(r'\d+', str(x))
            return f"set_{int(match.group())}" if match else x
        df_params['set_id'] = df_params['set_id'].apply(format_set_id)

        dir_name = os.path.dirname(os.path.abspath(args.output)) if args.output else "./"

        for metric in metrics_list:
            metric_subfolder = os.path.join(dir_name, metric)
            if not os.path.exists(metric_subfolder):
                os.makedirs(metric_subfolder)

            ext = "feather" if args.format == "feather" else "parquet"
            checkpoint_file = os.path.join(metric_subfolder, f"checkpoint_{metric}.{ext}")
            
            # CONTROL EXECUTION BRANCH VIA CHECKPOINT REGISTRATION STATE
            if args.checkpoint and os.path.exists(checkpoint_file):
                print(f"\n[+] Active checkpoint found for '{metric}' [{args.format.upper()}]. Restoring instantly...")
                if args.format == 'feather':
                    df_outputs = pd.read_feather(checkpoint_file)
                else:
                    df_outputs = pd.read_parquet(checkpoint_file)
            else:
                print(f"\n[*] Streaming pipeline arrays for metric: '{metric}' (Stride: {args.stride})...")
                df_outputs = stream_metric_data(args.input, args.table, metric, args.sets, args.runs, args.workers, args.stride)
                df_outputs['set_id'] = df_outputs['set_id'].apply(format_set_id)
                
                # Only write out to disk if the parameter flag is explicitly active
                if args.checkpoint:
                    print(f"[+] Flag '--checkpoint' active. Writing intermediate cache file: {checkpoint_file}")
                    if args.format == 'feather':
                        df_outputs.to_feather(checkpoint_file)
                    else:
                        df_outputs.to_parquet(checkpoint_file)
            
            print(f"[*] Intersecting model boundaries with simulation data tables...")
            df_merged = pd.merge(df_params, df_outputs, on='set_id', how='inner')
            del df_outputs
            gc.collect()
            
            if df_merged.empty:
                print(f"[ERROR] Clean merge index context empty for metric '{metric}'. Skipping.")
                continue
            
            for param in verified_cols:
                print(f"   -> Processing isolated parameter channel: [{param}]")
                
                if args.style in ['color', 'color-and-greyscale']:
                    dest = os.path.join(metric_subfolder, f'bifurcation_{metric}_{param}_color.png')
                    plot_bifurcation_panel(df_merged, param, metric, 'color', dest)
                    
                if args.style in ['greyscale', 'color-and-greyscale']:
                    dest = os.path.join(metric_subfolder, f'bifurcation_{metric}_{param}_greyscale.png')
                    plot_bifurcation_panel(df_merged, param, metric, 'greyscale', dest)
            
            del df_merged
            gc.collect()

        print(f"\n[+] Pipeline execution completed successfully using layout flag: '{args.style}'.")
        
    except Exception as err:
        print(f"\n[FATAL ERROR] {err}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
