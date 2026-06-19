#!/usr/bin/env python3
"""
================================================================================
Unified ETL: Single-Pass Agent Data Pipeline with Auto-Detection
================================================================================
Description:
    Processes hierarchical simulation folder structures (set_*/run_*) containing
    data_{agent_type}.parquet files. Automatically discovers agent types and
    metrics from input files, then performs a single folder traversal to:
    
    1. Standardize schemas: [set_num, run_num, time_step, ID, metric1, metric2, ...]
    2. Optimize types: int16/float32 for memory efficiency
    3. Apply optional stride filtering for downsampling
    4. Sort outputs: (set_num, run_num, time_step, ID)
    5. Generate Feather files: One per agent_type for fast queries

Architecture:
    - Metadata Scan: Quick discovery of agent types and available metrics
    - Parallel Processing: Multi-worker pool processes source files in parallel
    - Batch Streaming: 50k row chunks with explicit garbage collection
    - Stride Filtering: Optional downsampling (e.g., keep every Nth time step)
    - Memory Optimization: Batch streaming (50k rows), explicit garbage collection

Usage Examples:
    # Auto-detect everything
    python unified_etl.py --input ./data --output ./output --sets 1-100 --runs 1-50 --workers 8 --verbose
    
    # Filter to specific agents
    python unified_etl.py --input ./data --output ./output --sets 1-100 --runs 1-50 \
        --agent-types "Bank,Firm" --workers 8 --verbose
    
    # Filter to specific metrics with stride downsampling
    python unified_etl.py --input ./data --output ./output --sets 1-100 --runs 1-50 \
        --metrics "wealth,revenue,debt" --stride 2 --workers 8 --verbose
================================================================================
"""

import os
import sys

# Configure environment variables before loading native compiled libraries
os.environ.update({"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})

import re
import glob
import gc
import sys
import argparse
import multiprocessing
from collections import defaultdict

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc
import pyarrow.feather as feather

def init_worker():
    """Initialize worker process: ignore SIGINT to allow graceful shutdown."""
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def scan_metadata(root_dir, set_range, run_range, verbose=False):
    """
    Quick scan to discover:
      - All agent_types present in input
      - All metrics (columns) per agent_type
    
    Args:
        root_dir: Root directory containing set_*/run_*/data_*.parquet
        set_range: (start, end) inclusive
        run_range: (start, end) inclusive
        verbose: Enable verbose output
    
    Returns:
        {agent_type: [metric_names, ...]}
    """
    manifest = {}
    glob_pattern = os.path.join(root_dir, "set_*", "run_*", "data_*.parquet")
    
    for file_path in glob.iglob(glob_pattern.replace("\\", "/")):
        parts = file_path.replace("\\", "/").split("/")
        
        set_match = re.search(r'\d+', parts[-3])
        run_match = re.search(r'\d+', parts[-2])
        filename = parts[-1]
        agent_type = filename.replace("data_", "").replace(".parquet", "")
        
        if not (set_match and run_match):
            continue
        
        set_num = int(set_match.group())
        run_num = int(run_match.group())
        
        if not (set_range[0] <= set_num <= set_range[1] and
                run_range[0] <= run_num <= run_range[1]):
            continue
        
        # Read schema to extract metrics (only first file per agent type)
        if agent_type not in manifest:
            try:
                pf = pq.ParquetFile(file_path)
                col_names = pf.schema.names
                
                # Reserved columns to exclude
                reserved = {'set_num', 'run_num', 'time_step', 'ID', 'id', 'agent_id', 'iteration', 'tick'}
                metrics = [c for c in col_names if c not in reserved]
                
                manifest[agent_type] = metrics
                
                if verbose:
                    print(f"[DISCOVER] {agent_type}: metrics = {metrics}")
            except Exception as e:
                print(f"[WARNING] Could not read schema from {file_path}: {e}", file=sys.stderr)
                continue
    
    return manifest


def build_file_manifest(root_dir, agent_types, set_range, run_range):
    """
    Build list of (file_path, set_num, run_num, agent_type) for processing.
    
    Args:
        root_dir: Root directory containing set_*/run_*/data_*.parquet
        agent_types: List of agent types to include
        set_range: (start, end) inclusive
        run_range: (start, end) inclusive
    
    Returns:
        [(file_path, set_num, run_num, agent_type), ...]
    """
    manifest = []
    glob_pattern = os.path.join(root_dir, "set_*", "run_*", "data_*.parquet")
    
    for file_path in glob.iglob(glob_pattern.replace("\\", "/")):
        parts = file_path.replace("\\", "/").split("/")
        
        set_match = re.search(r'\d+', parts[-3])
        run_match = re.search(r'\d+', parts[-2])
        filename = parts[-1]
        agent_type = filename.replace("data_", "").replace(".parquet", "")
        
        if not (set_match and run_match):
            continue
        
        set_num = int(set_match.group())
        run_num = int(run_match.group())
        
        # Filter by agent_type and ranges
        if agent_type not in agent_types:
            continue
        if not (set_range[0] <= set_num <= set_range[1] and
                run_range[0] <= run_num <= run_range[1]):
            continue
        
        manifest.append((file_path, set_num, run_num, agent_type))
    
    return manifest


def process_source_file(task_args):
    """
    Process one data_{agent_type}.parquet file.
    
    Standardizes schema, casts types, applies stride filtering, and returns structured table.
    
    Args:
        task_args: (file_path, set_num, run_num, agent_type, metrics, stride)
    
    Returns:
        {
            'agent_type': str,
            'table': pa.Table [set_num, run_num, time_step, ID, metric1, metric2, ...]
        }
        or None on error
    """
    file_path, set_num, run_num, agent_type, metrics, stride = task_args
    
    try:
        pf = pq.ParquetFile(file_path)
        col_names = pf.schema.names
        
        # Identify time and ID columns
        time_col = next((c for c in ['time_step', 'iteration', 'tick'] if c in col_names), None)
        id_col = next((c for c in ['ID', 'id', 'agent_id'] if c in col_names), None)
        
        if not time_col:
            return None  # Can't process without time column
        
        batches_processed = []
        
        for batch in pf.iter_batches(batch_size=50_000):
            total_rows = batch.num_rows
            if total_rows == 0:
                continue
            
            # Apply stride filtering if needed
            if stride > 1:
                # Keep rows at indices 0, stride, 2*stride, ...
                indices = np.arange(0, total_rows, stride, dtype=np.int64)
                batch = batch.take(indices)
                total_rows = batch.num_rows
            
            if total_rows == 0:
                continue
            
            # Build standardized columns using np.full with int32 specifications
            arrays = [
                pa.array(np.full(total_rows, set_num, dtype=np.int32)),
                pa.array(np.full(total_rows, run_num, dtype=np.int32)),
                batch.column(time_col).cast(pa.int64()),
            ]
            names = ['set_num', 'run_num', 'time_step']
            
            # Add ID column
            if id_col:
                arrays.append(batch.column(id_col).cast(
                    pa.int64()
                ))
                names.append('ID')
            
            # Add detected metrics (only those that exist in this file)
            for metric in metrics:
                if metric in col_names:
                    col_type = batch.column(metric).type
                    if pa.types.is_floating(col_type):
                        arrays.append(batch.column(metric).cast(pa.float32()))
                    elif pa.types.is_integer(col_type):
                        arrays.append(batch.column(metric).cast(pa.int64()))
                    else:
                        arrays.append(batch.column(metric))
                    names.append(metric)
            
            batches_processed.append(pa.RecordBatch.from_arrays(arrays, names=names))
        
        if not batches_processed:
            return None
        
        return {
            'agent_type': agent_type,
            'table': pa.Table.from_batches(batches_processed)
        }
    
    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}", file=sys.stderr)
        return None


def run_unified_etl(root_dir, set_range, run_range, num_workers, output_dir, 
                    verbose=False, stride=1, filter_agents=None, filter_metrics=None):
    """
    Unified ETL: Auto-detect agent types and metrics, process in parallel.
    
    Args:
        root_dir: Root directory containing set_*/run_*/data_*.parquet
        set_range: (start, end) inclusive
        run_range: (start, end) inclusive
        num_workers: Number of parallel workers
        output_dir: Output directory for Feather files
        verbose: Enable verbose output
        stride: Stride for downsampling (default 1 = no downsampling)
        filter_agents: Optional list of agent types to include (if None, auto-detect all)
        filter_metrics: Optional list of metrics to include (if None, auto-detect all)
    """
    
    # Scan metadata
    if verbose:
        print("[SCAN] Discovering agent types and metrics...")
    
    metadata = scan_metadata(root_dir, set_range, run_range, verbose=verbose)
    
    if not metadata:
        print("[ERROR] No files matched scan criteria.")
        return
    
    # Filter agent types if specified
    agent_types = list(metadata.keys())
    if filter_agents:
        agent_types = [a for a in agent_types if a in filter_agents]
        if not agent_types:
            print(f"[ERROR] None of the filtered agents {filter_agents} found in input.")
            return
    
    if verbose:
        print(f"[INFO] Discovered agent types: {agent_types}")
    
    # Collect all metrics (union across all agents)
    all_metrics = set()
    for metrics in metadata.values():
        all_metrics.update(metrics)
    
    if filter_metrics:
        all_metrics = all_metrics.intersection(set(filter_metrics))
        if not all_metrics:
            print(f"[ERROR] None of the filtered metrics {filter_metrics} found in input.")
            return
    
    all_metrics = sorted(list(all_metrics))
    
    if verbose:
        print(f"[INFO] Discovered metrics: {all_metrics}")
        if stride > 1:
            print(f"[INFO] Stride filtering enabled: keeping every {stride}th row")
    
    # Build file manifest
    file_manifest = build_file_manifest(root_dir, agent_types, set_range, run_range)
    
    if not file_manifest:
        print("[ERROR] No files matched after filtering.")
        return
    
    if verbose:
        print(f"[INFO] Found {len(file_manifest)} source files to process.")
    
    # Create output directories
    for agent_type in agent_types:
        os.makedirs(os.path.join(output_dir, agent_type), exist_ok=True)
    
    # Process in parallel, accumulate by agent_type
    agent_tables = defaultdict(list)
    processed_count = 0
    failed_count = 0
    
    # Prepare task args with all_metrics and stride included
    task_args_list = [
        (fp, sn, rn, at, all_metrics, stride) 
        for fp, sn, rn, at in file_manifest
    ]
    
    with multiprocessing.Pool(processes=num_workers, initializer=init_worker) as pool:
        for result in pool.imap_unordered(process_source_file, task_args_list):
            if result is None:
                failed_count += 1
                continue
            
            agent_type = result['agent_type']
            table = result['table']
            agent_tables[agent_type].append(table)
            
            processed_count += 1
            if verbose and processed_count % 100 == 0:
                print(f"[PROGRESS] Processed {processed_count} files...")
    
    if verbose:
        print(f"[PROGRESS] Processed {processed_count} files total. Failures: {failed_count}")
        
    # Raise failure alert if any source tasks failed processing
    if failed_count:
        raise RuntimeError(f"{failed_count} source files failed to process")
    
    # Write sorted agent outputs
    for agent_type in agent_types:
        tables = agent_tables.get(agent_type, [])
        
        if not tables:
            if verbose:
                print(f"[SKIP] No data for {agent_type}")
            continue
        
        if verbose:
            print(f"[MERGE] Consolidating {len(tables)} tables for {agent_type}...")
        
        unified = pa.concat_tables(tables, promote_options='permissive')
        
        # Sort by (set_num, run_num, time_step, ID)
        sort_indices = pc.sort_indices(unified, sort_keys=[
            ('set_num', 'ascending'),
            ('run_num', 'ascending'),
            ('time_step', 'ascending'),
            ('ID', 'ascending'),
        ])
        unified = unified.take(sort_indices)
        
        # Write Feather only
        output_path = os.path.join(output_dir, agent_type, f'checkpoint_{agent_type}.feather')
        feather.write_feather(unified, output_path)
        
        if verbose:
            print(f"[WRITE] {output_path} ({unified.num_rows} rows)")
        
        del unified
        gc.collect()
    
    if verbose:
        print("[COMPLETE] Unified ETL finished.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Unified ETL: Auto-detect agent types and metrics, single-pass processing."
    )
    parser.add_argument('--input', required=True, 
                       help="Root directory containing set_*/run_*/data_*.parquet")
    parser.add_argument('--output', required=True, 
                       help="Output directory for checkpoint Feather files")
    parser.add_argument('--sets', required=True, 
                       help="Inclusive set range (e.g., '1-100')")
    parser.add_argument('--runs', required=True, 
                       help="Inclusive run range (e.g., '1-50')")
    parser.add_argument('--agent-types', default=None,
                       help="[Optional] Comma-separated agent types to include (default: auto-detect all)")
    parser.add_argument('--metrics', default=None,
                       help="[Optional] Comma-separated metrics to include (default: auto-detect all)")
    parser.add_argument('--stride', type=int, default=1,
                       help="[Optional] Stride for downsampling (keep every Nth row, default: 1 = no downsampling)")
    parser.add_argument('--workers', type=int, default=1, 
                       help="Number of parallel workers (default: 1)")
    parser.add_argument('--verbose', action='store_true', 
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Parse ranges
    set_bounds = [int(x) for x in args.sets.split('-')]
    run_bounds = [int(x) for x in args.runs.split('-')]
    
    # Parse optional filters
    filter_agents = None
    if args.agent_types:
        filter_agents = [a.strip() for a in args.agent_types.split(',')]
    
    filter_metrics = None
    if args.metrics:
        filter_metrics = [m.strip() for m in args.metrics.split(',')]
    
    os.environ.update({"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})
    
    run_unified_etl(
        root_dir=args.input,
        set_range=set_bounds,
        run_range=run_bounds,
        num_workers=args.workers,
        output_dir=args.output,
        verbose=args.verbose,
        stride=args.stride,
        filter_agents=filter_agents,
        filter_metrics=filter_metrics
    )