#!/usr/bin/env python3
"""
================================================================================
Global Sensitivity Analysis (GSA) Module (Production Parallel Version)
================================================================================
Description:
    Processes large mirrored Parquet files using an isolated, memory-safe, 
    highly parallelized framework. Optimized to avoid IO stalling and memory leaks
    when executing Global Sensitivity Analysis calculations.

Usage Syntax:
    $ python sensitivity_analysis.py --input ./parquet_mirror_output \\
        --parameters sample_513_mode_3.csv --table Agent_n --metric wealth

Command-Line Arguments & Flags:
    -i, --input    [Required] Path to the mirrored Parquet folder root.
    -p, --parameters [Required] Path to CSV containing input parameter configs per set.
    -t, --table    [Required] Name of the inner agent database table to extract.
    -m, --metric   [Required] Column name within the table to use as performance target.
    --sets         [Optional] Inclusive range of sets to include (e.g., 1-50).
    --runs         [Optional] Inclusive range of runs to include (e.g., 1-1000).
    -w, --workers  [Optional] Number of concurrent process workers to run.
                              Default: Host logical core count.
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

def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def parse_range_arg(range_str):
    if not range_str:
        return None
    match = re.match(r'^(\d+)-(\d+)$', range_str.strip())
    if not match:
        raise argparse.ArgumentTypeError(f"Range format must be 'start-end' (e.g. 1-5). Got: '{range_str}'")
    start, end = int(match.group(1)), int(match.group(2))
    if start > end:
        raise argparse.ArgumentTypeError(f"Invalid range definition.")
    return (start, end)

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

def read_single_parquet_metric_native(task_args):
    file_path, set_id, run_id, metric_name = task_args
    try:
        data_table = pq.read_table(file_path, columns=[metric_name])
        if data_table.num_rows == 0:
            return None
        
        mean_val = np.mean(data_table.column(metric_name).to_numpy())
        return {'set_id': set_id, 'run_id': run_id, 'output_value': mean_val}
    except Exception:
        return None

def run_parallel_aggregation(root_dir, table_name, metric_name, set_range, run_range, num_workers):
    target_file = f"data_{table_name}.parquet"
    print("Analyzing filesystem mirrored structure indices...")
    
    scan_queue = []
    for root, _, files in os.walk(root_dir):
        if target_file in files:
            parts = root.replace("\\", "/").split("/")
            set_match = [p for p in parts if re.match(r'^set_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
            run_match = [p for p in parts if re.match(r'^run_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
            
            if set_match and run_match:
                if is_in_range(set_match[-1], set_range) and is_in_range(run_match[-1], run_range):
                    scan_queue.append((os.path.join(root, target_file), set_match[-1], run_match[-1], metric_name))
                    
    total_targets = len(scan_queue)
    print(f"Identified {total_targets} filtered data blocks for evaluation. Allocating engine execution pool...")
    
    if total_targets == 0:
        raise ValueError("Zero target files matched validation parameters inside target limits.")

    records = []
    with multiprocessing.Pool(processes=num_workers, initializer=init_worker, maxtasksperchild=500) as pool:
        try:
            results = pool.imap_unordered(read_single_parquet_metric_native, scan_queue, chunksize=50)
            for idx, item in enumerate(results, 1):
                if item is not None:
                    records.append(item)
                if idx % max(1, total_targets // 10) == 0 or idx == total_targets:
                    print(f" -> File Streaming Progression: {idx}/{total_targets} files evaluated...", flush=True)
        except KeyboardInterrupt:
            print("\n[ALERT] Processing halted via user cancel command. Safely dissolving active threads.")
            pool.terminate()
            pool.join()
            sys.exit(130)
            
    if not records:
        raise ValueError("Data read anomaly: Extraction yielded zero structural data sets.")

    df_raw = pd.DataFrame(records)
    return df_raw.groupby('set_id')['output_value'].mean().reset_index()

def perform_gsa(df_merged, parameter_columns):
    print("\n" + "="*85 + "\nExecuting Global Sensitivity Analysis\n" + "="*85)
    Y = df_merged['output_value'].values
    if np.var(Y) == 0:
        print("[ERROR] Variance is zero across data segments. Evaluation suspended.")
        return

    print("Parameter Boundaries Analyzed:")
    for col in parameter_columns:
        print(f"  * {col:<35} : [{df_merged[col].min():>12.4f}, {df_merged[col].max():>12.4f}]")

    print("\n--- Feature Correlation / Variance Contribution Proxy ---")
    correlations = {}
    for col in parameter_columns:
        corr = df_merged[col].corr(pd.Series(Y))
        correlations[col] = corr if not np.isnan(corr) else 0.0
        
    total_sq_corr = sum(c**2 for c in correlations.values())
    
    print(f"{'Economic Parameter Name':<40} | {'Pearson R':<12} | {'Estimated Variance Contribution':<30}")
    print("-" * 90)
    for param, r_val in correlations.items():
        contribution = (r_val**2 / total_sq_corr * 100) if total_sq_corr > 0 else 0.0
        print(f"{param:<40} | {r_val:>11.4f} | {contribution:>28.2f}%")

def main():
    parser = argparse.ArgumentParser(description="Production GSA Extraction Module Framework Configuration.")
    parser.add_argument('-i', '--input', required=True, help="Path to the mirrored Parquet folder root.")
    parser.add_argument('-p', '--parameters', required=True, help="Path to CSV containing input parameter configs per set.")
    parser.add_argument('-t', '--table', required=True, help="Name of the inner agent database table to extract.")
    parser.add_argument('-m', '--metric', required=True, help="Column name within the table to use as performance target.")
    parser.add_argument('--sets', type=parse_range_arg, help="Inclusive range of sets to include (e.g., 1-50).")
    parser.add_argument('--runs', type=parse_range_arg, help="Inclusive range of runs to include (e.g., 1-1000).")
    parser.add_argument('-w', '--workers', type=int, default=multiprocessing.cpu_count(), help="Number of concurrent process workers to run (defaults to host logical core count).")
    
    args = parser.parse_args()
    
    try:
        df_params, verified_cols = load_parameter_design(args.parameters, args.sets)
        df_outputs = run_parallel_aggregation(args.input, args.table, args.metric, args.sets, args.runs, args.workers)
        
        df_merged = pd.merge(df_params, df_outputs, on='set_id', how='inner')
        if df_merged.empty and not df_params.empty:
            df_params['set_id'] = df_params['set_id'].apply(lambda x: f"set_{int(re.search(r'\d+', x).group()):02d}" if re.search(r'\d+', x) else x)
            df_merged = pd.merge(df_params, df_outputs, on='set_id', how='inner')
            
        if df_merged.empty:
            print("[FATAL] Inner merge resolved into empty series set across target thresholds configuration indexes.")
            return
            
        print(f"\nSuccessfully matched {len(df_merged)} simulation sets for GSA.")
        perform_gsa(df_merged, verified_cols)
        
    except Exception as err:
        print(f"\n[FATAL ERROR] {err}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
