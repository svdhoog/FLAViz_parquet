#!/usr/bin/env python3
"""
================================================================================
Global Sensitivity Analysis (GSA) & Bifurcation Mapping Module
================================================================================
Description:
    Processes large mirrored Parquet files using a highly parallel framework to 
    construct empirical bifurcation diagrams. Instead of aggressively averaging 
    dynamics down to a single point, this module maps every iteration of every 
    run directly against the parameter continuum.

    Supports rendering low-opacity monochrome structures, color-mapped probability 
    density fields, or executing both layouts simultaneously to track phase 
    transitions, stable attractors, and chaotic splits.
================================================================================
"""

import os
import re
import sys
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
        {"symbol": "α", "name": "Capital Adequacy Ratio"},
        {"symbol": "β", "name": "Reserve Requirement Ratio"},
        {"symbol": "γ", "name": "Price Sensitivity"},
        {"symbol": "d", "name": "Dividend Ratio"},
        {"symbol": "φ", "name": "Debt Rescaling Ratio"},
        {"symbol": "τ", "name": "Tax Rate"},
        {"symbol": "T", "name": "Debt Repayment (months)"},
        {"symbol": "r^ecb", "name": "Base Interest Rate"}
    ]
    param_names = [f"{p['symbol']} ({p['name']})" for p in param_definitions]
    rename_dict = {0: 'set_id'}
    for i, name in enumerate(param_names):
        rename_dict[i + 1] = name
        
    df.rename(columns=rename_dict, inplace=True)
    df['set_id'] = df['set_id'].astype(str).str.strip()
    
    if set_range:
        df = df[df['set_id'].apply(lambda x: is_in_range(x, set_range))]
    return df, param_names

def read_single_parquet_raw_stream(task_args):
    file_path, set_id, run_id, single_metric = task_args
    try:
        data_table = pq.read_table(file_path, columns=[single_metric])
        if data_table.num_rows == 0:
            return None
        y_values = data_table.column(single_metric).to_numpy()
        return {'set_id': set_id, 'y': y_values}
    except Exception:
        return None

def stream_metric_data(root_dir, table_name, metric, set_range, run_range, num_workers):
    target_file = f"data_{table_name}.parquet"
    scan_queue = []
    
    for root, _, files in os.walk(root_dir):
        if target_file in files:
            parts = root.replace("\\", "/").split("/")
            set_match = [p for p in parts if re.match(r'^set_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
            run_match = [p for p in parts if re.match(r'^run_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
            
            if set_match and run_match:
                if is_in_range(set_match[-1], set_range) and is_in_range(run_match[-1], run_range):
                    scan_queue.append((os.path.join(root, target_file), set_match[-1], run_match[-1], metric))
                    
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

# ================================================================================
# DIAGNOSTIC PLOTTING PLUGINS
# ================================================================================
def plot_bifurcation_greyscale(df_merged, parameter_columns, target_metric, save_path):
    """Monochrome engine capitalizing on high-density alpha-blending."""
    num_params = len(parameter_columns)
    cols = 4
    rows = (num_params + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(18, 4 * rows), sharey=True)
    axes = axes.flatten()
    
    print(f" -> Rendering low-opacity monochrome scatter canvas...")
    
    for i, col in enumerate(parameter_columns):
        axes[i].scatter(df_merged[col], df_merged[target_metric], 
                        alpha=0.01, s=0.05, color='#111111', rasterized=True)
        
        axes[i].set_title(f'{col}', fontsize=11)
        axes[i].set_ylabel(target_metric if i % cols == 0 else '')
        axes[i].grid(True, linestyle='--', alpha=0.2)
        
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])
        
    title_text = (
        f"Simulation Empirical Bifurcation Diagram (Monochrome Vector Mapping)\n"
        f"Target Metric: {target_metric} (All Iterations & Runs Plotted)"
    )
    plt.suptitle(title_text, fontsize=14, y=0.98)
    plt.tight_layout()
    plt.savefig(save_path, dpi=400)
    plt.close()


def plot_bifurcation_color(df_merged, parameter_columns, target_metric, save_path):
    """Color engine mapping localized 2D histogram bins to a logarithmic colormap."""
    num_params = len(parameter_columns)
    cols = 4
    rows = (num_params + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(18, 4 * rows), sharey=True)
    axes = axes.flatten()
    
    print(f" -> Computing 2D histograms and color-coding densities...")
    
    last_scatter = None
    
    for i, col in enumerate(parameter_columns):
        x = df_merged[col].values
        y = df_merged[target_metric].values
        
        counts, xedges, yedges = np.histogram2d(x, y, bins=[100, 200])
        
        x_bins = np.clip(np.digitize(x, xedges) - 1, 0, counts.shape[0] - 1)
        y_bins = np.clip(np.digitize(y, yedges) - 1, 0, counts.shape[1] - 1)
        densities = counts[x_bins, y_bins]
        
        idx = densities.argsort()
        x_sort, y_sort, d_sort = x[idx], y[idx], densities[idx]
        
        last_scatter = axes[i].scatter(x_sort, y_sort, c=d_sort, cmap='inferno', 
                                       norm=LogNorm(vmin=1, vmax=max(2, densities.max())),
                                       s=0.15, alpha=0.4, rasterized=True)
        
        axes[i].set_title(f'{col}', fontsize=11)
        axes[i].set_ylabel(target_metric if i % cols == 0 else '')
        axes[i].grid(True, linestyle='--', alpha=0.2)
        
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])
        
    if last_scatter is not None:
        cbar_ax = fig.add_axes([0.96, 0.15, 0.015, 0.7])
        fig.colorbar(last_scatter, cax=cbar_ax, label='Relative State Point Density (Log Scale)')
        
    title_text = (
        f"Simulation Empirical Bifurcation Topology Map (Probability Density Colorized)\n"
        f"Target Metric: {target_metric} (All Iterations & Runs Plotted)"
    )
    plt.suptitle(title_text, fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0, 0.95, 1.0])
    plt.savefig(save_path, dpi=400)
    plt.close()

# ================================================================================
# EXECUTION COUPLING
# ================================================================================
def main():
    parser = argparse.ArgumentParser(description="Parallel Bifurcation Space Extraction Engine.")
    parser.add_argument('-i', '--input', required=True, help="Path to the mirrored Parquet folder root.")
    parser.add_argument('-p', '--parameters', required=True, help="Path to CSV parameters file.")
    parser.add_argument('-t', '--table', required=True, help="Name of the inner agent database table.")
    parser.add_argument('-m', '--metric', required=True, nargs='+', type=parse_metrics_arg,
                        help="Target performance metrics. Supports [a,b,c] or space-separated lists.")
    
    # MODIFIED: Added 'color-and-greyscale' option choice
    parser.add_argument('-s', '--style', choices=['color', 'greyscale', 'color-and-greyscale'], default='color',
                        help="Visual styling format engine used for rendering diagrams (default: color).")
    
    parser.add_argument('-o', '--output', default=None, help="Output destination root folder.")
    parser.add_argument('--sets', type=parse_range_arg)
    parser.add_argument('--runs', type=parse_range_arg)
    parser.add_argument('-w', '--workers', type=int, default=multiprocessing.cpu_count())
    
    args = parser.parse_args()
    
    metrics_list = []
    for sublist in args.metric:
        metrics_list.extend(sublist)
    metrics_list = list(dict.fromkeys(metrics_list))
    
    try:
        df_params, verified_cols = load_parameter_design(args.parameters, args.sets)
        
        def format_set_id(x):
            match = re.search(r'\d+', str(x))
            return f"set_{int(match.group())}" if match else x
        df_params['set_id'] = df_params['set_id'].apply(format_set_id)

        dir_name = os.path.dirname(os.path.abspath(args.output)) if args.output else "./"

        for metric in metrics_list:
            print(f"\n[*] Processing data vector blocks for target metric: '{metric}'...")
            df_outputs = stream_metric_data(args.input, args.table, metric, args.sets, args.runs, args.workers)
            df_outputs['set_id'] = df_outputs['set_id'].apply(format_set_id)
            
            print(f"[*] Merging parameters with tracking arrays...")
            df_merged = pd.merge(df_params, df_outputs, on='set_id', how='inner')
            
            if df_merged.empty:
                print(f"[ERROR] Failed to map data for metric '{metric}'. Skipping graphics.")
                continue
                
            metric_subfolder = os.path.join(dir_name, metric)
            if not os.path.exists(metric_subfolder):
                os.makedirs(metric_subfolder)
            
            # MODIFIED: Control plot processing paths via string matching to support simultaneous multi-rendering outputs
            if args.style in ['color', 'color-and-greyscale']:
                save_dest_color = os.path.join(metric_subfolder, f'gsa_behavior_grid_{metric}_color.png')
                plot_bifurcation_color(df_merged, verified_cols, metric, save_dest_color)
                
            if args.style in ['greyscale', 'color-and-greyscale']:
                save_dest_grey = os.path.join(metric_subfolder, f'gsa_behavior_grid_{metric}_greyscale.png')
                plot_bifurcation_greyscale(df_merged, verified_cols, metric, save_dest_grey)
            
            del df_outputs
            del df_merged

        print(f"\n[+] GSA Execution pipeline completed successfully using style flag: '{args.style}'.")
        
    except Exception as err:
        print(f"\n[FATAL ERROR] {err}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
