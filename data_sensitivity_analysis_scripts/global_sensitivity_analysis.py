#!/usr/bin/env python3
"""
================================================================================
Global Sensitivity Analysis (GSA) - Bifurcation Plotting Engine
================================================================================
Description:
    Generates bifurcation diagrams from pre-computed ETL checkpoints.
    Reads standardized Feather files produced by unified_etl.py and creates
    2D histograms mapping economic parameters against metric values.

Architecture:
    - Loads Feather checkpoints (from unified_etl.py output)
    - Two-pass streaming: sample for threshold, then render
    - Percentile clipping to remove stochastic outliers
    - Streaming histogram accumulation (memory-flat regardless of dataset size)
    - Direct Arrow zero-copy plotting (no Pandas materialization)

Prerequisites:
    - Run unified_etl.py first to generate checkpoint Feather files
    - Provide CSV with parameter metadata (set_num, parameter columns)

Usage:
    python global_sensitivity_analysis.py \\
        --checkpoint ./output/Bank/checkpoint_Bank.feather \\
        --parameters ./parameters.csv \\
        --metric wealth \\
        --output ./plots \\
        --percentile 95 \\
        --verbose
================================================================================
"""

import os
import sys
import gc
import time
import argparse
import threading
import numpy as np
import pandas as pd
import psutil
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.ipc as ipc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


class LiveMemoryProfiler(threading.Thread):
    """Background thread: log memory usage over time."""
    def __init__(self, log_path="gsa_memory_profile.csv", interval_sec=2.0):
        super().__init__()
        self.log_path = log_path
        self.interval_sec = interval_sec
        self.daemon = True
        self.is_running = True
    
    def run(self):
        process = psutil.Process(os.getpid())
        while self.is_running:
            try:
                ram_gb = process.memory_info().rss / (1024 ** 3)
                swap_gb = psutil.swap_memory().used / (1024 ** 3)
                with open(self.log_path, "a") as f:
                    f.write(f"{time.time()},{ram_gb:.3f},{swap_gb:.3f}\n")
            except:
                pass
            time.sleep(self.interval_sec)
    
    def stop(self):
        self.is_running = False


def log(message, verbose=False):
    """Conditional logging with timestamp."""
    if verbose:
        print(f"[{time.strftime('%H:%M:%S')}] {message}")


def get_iterator(checkpoint_path, file_format, columns):
    """
    Open optimized iterator over checkpoint file (Feather or Parquet).
    
    Args:
        checkpoint_path: Path to .feather or .parquet file
        file_format: 'feather' or 'parquet'
        columns: List of column names to read
    
    Returns:
        (iterator, source) where source is file handle for cleanup
    """
    if file_format == 'feather':
        import pyarrow.feather as feather
        # Read only the selected columns into a localized PyArrow Table
        table = feather.read_table(checkpoint_path, columns=columns)
        # Convert to an iterable batch list matching the chunk sizing of the Parquet pipeline
        return table.to_batches(max_chunksize=50_000), None
    else:  # parquet
        return pq.ParquetFile(checkpoint_path).iter_batches(batch_size=50_000, columns=columns), None

def generate_bifurcation_plots(checkpoint_path, metric, file_format, output_dir, 
                               parameters_file_path, percentile_limit, verbose):
    """
    Generate bifurcation diagrams for a metric across economic parameters.
    
    Args:
        checkpoint_path: Path to checkpoint Feather/Parquet file (from unified_etl)
        metric: Metric name (column in checkpoint)
        file_format: 'feather' or 'parquet'
        output_dir: Output directory for plots
        parameters_file_path: CSV file with parameter metadata
        percentile_limit: Percentile threshold to clip outliers (e.g., 95)
        verbose: Verbose logging
    """
    log(f"[START] Plotting bifurcation for {metric}...", verbose)
    
    # Load parameter metadata
    param_meta_df = pd.read_csv(parameters_file_path)
    param_meta_df['set_num'] = param_meta_df['set_num'].astype(str).str.extract(r'(\d+)').astype(int)
    param_meta_df = param_meta_df.set_index('set_num').reindex(range(1, param_meta_df['set_num'].max() + 1))
    
    # Calculate percentile threshold (sampling pass)
    log(f"[ANALYSIS] Calculating global metric boundaries...", verbose)
    sample_points = []
    it, _ = get_iterator(checkpoint_path, file_format, [metric])
    
    for batch in it:
        if metric not in batch.schema.names:
            raise ValueError(f"Metric {metric!r} not found in checkpoint")
        sample_points.append(batch.column(metric).to_numpy())
        if sum(len(s) for s in sample_points) > 1_000_000:
            break
    
    if not sample_points:
        raise ValueError(f"No finite values found for metric {metric!r}")

    metric_sample = np.concatenate(sample_points)
    finite_metric_sample = metric_sample[np.isfinite(metric_sample)]

    # Calculate a symmetric lower bound to exclude extreme negative outliers
    if not 0 <= percentile_limit <= 100:
        raise ValueError("--percentile must be between 0 and 100")

    # If percentile_limit is 99, this sets the floor at the 1st percentile
    lower_percentile = 100.0 - percentile_limit

    lower = np.percentile(finite_metric_sample, lower_percentile)
    upper = np.percentile(finite_metric_sample, percentile_limit)
    
    del sample_points, metric_sample, finite_metric_sample
    gc.collect()
    
    log(f"  -> Metric Range: Floor = {lower:.4f} (0%), Ceiling = {upper:.4f} ({percentile_limit}%)", verbose)

    # Identify economic parameters (exclude metadata columns)
    economic_params = [c for c in param_meta_df.columns if c not in {'run_num', 'time_step', 'set_num'}]
    
    # Rendering pass: accumulate histograms
    for param_name in economic_params:
        log(f"[RENDER] Creating plot for {param_name.upper()}...", verbose)
        param_vector = param_meta_df[param_name].values.astype(np.float32)
        
        # Pre-compute bin edges
        hist_grid = np.zeros((500, 500))
        x_edges = np.linspace(param_vector.min(), param_vector.max(), 501)

        # Fix negative metric values
        y_edges = np.linspace(lower, upper, 501)
        
        # Stream batches, accumulate histogram
        it, source = get_iterator(checkpoint_path, file_format, ['set_num', metric])
        for batch in it:
            sets = batch.column('set_num').to_numpy()
            vals = batch.column(metric).to_numpy()
            mask = np.isfinite(vals) & (vals >= lower) & (vals <= upper)
            
            if np.any(mask):
                H, _, _ = np.histogram2d(
                    param_vector[sets[mask] - 1],
                    vals[mask],
                    bins=[x_edges, y_edges]
                )
                hist_grid += H
            
            del sets, vals, mask
        
        # Render and save
        fig, ax = plt.subplots(figsize=(11, 6))
        im = ax.imshow(
            hist_grid.T,
            origin='lower',
            extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
            cmap='turbo',
            norm=mcolors.LogNorm(vmin=1, vmax=hist_grid.max() or 1),
            aspect='auto'
        )
        plt.colorbar(im, ax=ax)
        plt.title(f"Bifurcation: {metric} vs {param_name}")
        plt.xlabel(param_name)
        plt.ylabel(metric)
        
        output_path = os.path.join(output_dir, f"bifurcation_{metric}_{param_name}.png")
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close('all')
        
        if verbose:
            print(f"[WRITE] {output_path}")
        
        del param_vector, hist_grid, fig, ax
        if source:
            source.close()
        gc.collect()
    
    log(f"[FINISH] Plotting completed for {metric}", verbose)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Global Sensitivity Analysis: Bifurcation plotting from ETL checkpoints."
    )
    parser.add_argument('--checkpoint', required=True,
                       help="Path to checkpoint Feather file (output from unified_etl.py)")
    parser.add_argument('--parameters', required=True,
                       help="CSV file with parameter metadata (columns: set_num, parameter columns)")
    parser.add_argument('--metric', required=True,
                       help="Metric name (column in checkpoint file)")
    parser.add_argument('--output', required=True,
                       help="Output directory for bifurcation plots")
    parser.add_argument('--format', default='feather', choices=['feather', 'parquet'],
                       help="Checkpoint file format (default: feather)")
    parser.add_argument('--percentile', type=float, default=100,
                       help="Percentile threshold to clip outliers (default: 100 = no clipping)")
    parser.add_argument('--memory-profile', action='store_true',
                       help="Enable background memory profiling")
    parser.add_argument('--verbose', action='store_true',
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.checkpoint):
        print(f"[ERROR] Checkpoint file not found: {args.checkpoint}")
        sys.exit(1)
    
    if not os.path.exists(args.parameters):
        print(f"[ERROR] Parameters file not found: {args.parameters}")
        sys.exit(1)
    
    os.makedirs(args.output, exist_ok=True)
    
    os.environ.update({"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})
    
    # Optional memory profiling
    profiler = None
    if args.memory_profile:
        profiler = LiveMemoryProfiler()
        profiler.start()
    
    try:
        generate_bifurcation_plots(
            checkpoint_path=args.checkpoint,
            metric=args.metric,
            file_format=args.format,
            output_dir=args.output,
            parameters_file_path=args.parameters,
            percentile_limit=args.percentile,
            verbose=args.verbose
        )
    finally:
        if profiler:
            profiler.stop()
            profiler.join()