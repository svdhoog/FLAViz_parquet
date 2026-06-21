#!/usr/bin/env python3
"""
================================================================================
Unified ETL: Single-Pass Agent Data Pipeline with Auto-Detection & Harmonization
================================================================================
Description:
    Processes hierarchical simulation folder structures (set_*/run_*) containing
    data_{agent_type}.parquet files. Automatically discovers agent types and
    metrics from input files, normalizes heterogenous schemas across legacy run 
    folders, then performs a single folder traversal to:
    
    1. Standardize schemas: [set_num, run_num, time_step, ID, metric1, metric2, ...]
    2. Handle schema drift: Map string sentinels ("NaN", "null") to proper types
    3. Optimize types: int16/float32/int64 for downstream computation
    4. Apply optional stride filtering for downsampling
    5. Sort outputs: (set_num, run_num, time_step, ID)
    6. Generate Feather files: One per agent_type for fast queries

Usage Examples:
    # Auto-detect everything
    python unified_etl.py --input ./data --output ./output --sets 1-100 --runs 1-50 --workers 8 --verbose
================================================================================
"""

import os
import sys

# Configure environment variables before loading native compiled libraries
os.environ.update({"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})

import re
import glob
import gc
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
    Quick scan to discover all agent_types present in input and build a master
    target data type map for all metrics across files to prevent schema drift.
    
    Returns:
        tuple: (dict of {agent_type: [metrics]}, dict of {agent_type: {metric: pa.type}})
    """
    manifest = {}
    type_registry = {}
    glob_pattern = os.path.join(root_dir, "set_*", "run_*", "data_*.parquet")
    
    for file_path in glob.iglob(glob_pattern.replace("\\", "/")):
        parts = file_path.replace("\\", "/").split("/")
        
        set_match = re.fullmatch(r"set_(\d+)", parts[-3])
        run_match = re.fullmatch(r"run_(\d+)", parts[-2])
        filename = parts[-1]
        
        m = re.fullmatch(r"data_(.+)\.parquet", filename)
        if not (set_match and run_match and m):
            continue
        
        agent_type = m.group(1)
        set_num = int(set_match.group(1))
        run_num = int(run_match.group(1))
        
        if not (set_range[0] <= set_num <= set_range[1] and
                run_range[0] <= run_num <= run_range[1]):
            continue
        
        if agent_type not in manifest:
            try:
                pf = pq.ParquetFile(file_path)
                schema = pf.schema.to_arrow_schema()
                col_names = schema.names
                
                # Reserved columns to exclude from analytical metrics
                reserved = {'set_num', 'run_num', 'time_step', 'ID', 'id', 'agent_id', 'iteration', 'tick'}
                metrics = [c for c in col_names if c not in reserved]
                
                manifest[agent_type] = metrics
                type_registry[agent_type] = {}
                
                # Register expected clean target types
                for metric in metrics:
                    field_type = schema.field(metric).type
                    # If initialized as a string due to legacy data anomalies, default to float32
                    if pa.types.is_string(field_type):
                        type_registry[agent_type][metric] = pa.float32()
                    elif pa.types.is_floating(field_type):
                        type_registry[agent_type][metric] = pa.float32()
                    elif pa.types.is_integer(field_type):
                        type_registry[agent_type][metric] = pa.int64()
                    else:
                        type_registry[agent_type][metric] = field_type
                
                if verbose:
                    print(f"[DISCOVER] {agent_type}: metrics = {metrics}")
            except Exception as e:
                print(f"[WARNING] Could not read schema from {file_path}: {e}", file=sys.stderr)
                continue
                
    return manifest, type_registry


def build_file_manifest(root_dir, agent_types, set_range, run_range):
    """Build list of (file_path, set_num, run_num, agent_type) for processing."""
    manifest = []
    glob_pattern = os.path.join(root_dir, "set_*", "run_*", "data_*.parquet")
    
    for file_path in glob.iglob(glob_pattern.replace("\\", "/")):
        parts = file_path.replace("\\", "/").split("/")
        
        set_match = re.fullmatch(r"set_(\d+)", parts[-3])
        run_match = re.fullmatch(r"run_(\d+)", parts[-2])
        filename = parts[-1]
        
        m = re.fullmatch(r"data_(.+)\.parquet", filename)
        if not (set_match and run_match and m):
            continue
        
        agent_type = m.group(1)
        set_num = int(set_match.group(1))
        run_num = int(run_match.group(1))
        
        if agent_type not in agent_types:
            continue
        if not (set_range[0] <= set_num <= set_range[1] and
                run_range[0] <= run_num <= run_range[1]):
            continue
        
        manifest.append((file_path, set_num, run_num, agent_type))
        
    return manifest


def clean_and_harmonize_column(column_data, expected_type):
    """
    Uses vector pyarrow compute kernels to sanitize legacy non-numeric
    string tokens before executing analytical numeric transformations.
    """
    current_type = column_data.type
    
    if current_type == expected_type:
        return column_data
        
    # If the column arrived as a string but expects a float/integer layout
    if pa.types.is_string(current_type) and (pa.types.is_floating(expected_type) or pa.types.is_integer(expected_type)):
        null_sentinels = pa.array(["NaN", "null", "inf", "-inf", "None", "", "nan"])
        is_sentinel = pc.is_in(column_data, value_set=null_sentinels)
        # Convert literal string placeholders directly to true PyArrow Null scalars
        sanitized = pc.if_else(is_sentinel, pa.scalar(None, type=current_type), column_data)
        return pc.cast(sanitized, expected_type)
        
    return pc.cast(column_data, expected_type)


def process_source_file(task_args):
    """
    Process one data_{agent_type}.parquet file.
    Standardizes schema, cleans legacy data anomalies, and returns structured table.
    """
    file_path, set_num, run_num, agent_type, metrics, expected_types, stride = task_args
    
    try:
        pf = pq.ParquetFile(file_path)
        schema = pf.schema.to_arrow_schema()
        col_names = schema.names
        
        time_col = next((c for c in ['time_step', 'iteration', 'tick', '_ITERATION_NO'] if c in col_names), None)
        id_col = next((c for c in ['ID', 'id', 'agent_id'] if c in col_names), None)
        
        if not time_col:
            return None
        
        batches_processed = []
        
        for batch in pf.iter_batches(batch_size=50_000):
            total_rows = batch.num_rows
            if total_rows == 0:
                continue
                
            if stride > 1:
                indices = np.arange(0, total_rows, stride, dtype=np.int64)
                batch = batch.take(indices)
                total_rows = batch.num_rows
                
            if total_rows == 0:
                continue
                
            # Build baseline index arrays safely
            arrays = [
                pa.array(np.full(total_rows, set_num, dtype=np.int32)),
                pa.array(np.full(total_rows, run_num, dtype=np.int32)),
                pc.cast(batch.column(time_col), pa.int64()),
            ]
            names = ['set_num', 'run_num', 'time_step']
            
            if id_col:
                arrays.append(pc.cast(batch.column(id_col), pa.int64()))
                names.append('ID')
            else:
                # Fallback index array matching structural row allocations
                arrays.append(pa.array(np.arange(total_rows, dtype=np.int64())))
                names.append('ID')
                
            # Harmonize all structural metrics to prevent downstream concatenation alignment crashes
            for metric in metrics:
                if metric in col_names:
                    raw_col = batch.column(metric)
                    target_type = expected_types.get(metric, pa.float32())
                    harmonized_col = clean_and_harmonize_column(raw_col, target_type)
                    arrays.append(harmonized_col)
                else:
                    # Pad missing column with structurally casted null values
                    target_type = expected_types.get(metric, pa.float32())
                    arrays.append(pa.array([None] * total_rows, type=target_type))
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
    """Unified ETL entry runner."""
    if verbose:
        print("[SCAN] Discovering agent types and metrics...")
        
    metadata, type_registry = scan_metadata(root_dir, set_range, run_range, verbose=verbose)
    
    if not metadata:
        print("[ERROR] No files matched scan criteria.")
        return
        
    agent_types = list(metadata.keys())
    if filter_agents:
        agent_types = [a for a in agent_types if a in filter_agents]
        if not agent_types:
            print(f"[ERROR] None of the filtered agents {filter_agents} found.")
            return
            
    file_manifest = build_file_manifest(root_dir, agent_types, set_range, run_range)
    if not file_manifest:
        print("[ERROR] No files matched after filtering.")
        return
        
    for agent_type in agent_types:
        os.makedirs(os.path.join(output_dir, agent_type), exist_ok=True)
        
    agent_tables = defaultdict(list)
    processed_count = 0
    failed_count = 0
    
    # Bundle tasks with schema-mapping registers appended
    task_args_list = [
        (fp, sn, rn, at, sorted(metadata[at]), type_registry[at], stride) 
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
                
    if failed_count:
        raise RuntimeError(f"{failed_count} source files failed processing.")
        
    for agent_type in agent_types:
        tables = agent_tables.get(agent_type, [])
        if not tables:
            continue
            
        if verbose:
            print(f"[MERGE] Consolidating {len(tables)} tables for {agent_type}...")
            
        # Standardized schema maps allow safe consolidation execution sweeps
        unified = pa.concat_tables(tables, promote_options='permissive')
        
        sort_indices = pc.sort_indices(unified, sort_keys=[
            ('set_num', 'ascending'),
            ('run_num', 'ascending'),
            ('time_step', 'ascending'),
            ('ID', 'ascending'),
        ])
        unified = unified.take(sort_indices)
        
        output_path = os.path.join(output_dir, agent_type, f'checkpoint_{agent_type}.feather')
        feather.write_feather(unified, output_path)
        
        if verbose:
            print(f"[WRITE] {output_path} ({unified.num_rows} rows)")
            
        del unified
        gc.collect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Unified ETL configuration runner.")
    parser.add_argument('--input', required=True, help="Root folder tree containing input targets.")
    parser.add_argument('--output', required=True, help="Target storage checkpoint folder path.")
    parser.add_argument('--sets', required=True, help="Inclusive range limits (e.g. 1-100)")
    parser.add_argument('--runs', required=True, help="Inclusive range limits (e.g. 1-50)")
    parser.add_argument('--agent-types', default=None, help="Comma-separated target list.")
    parser.add_argument('--metrics', default=None, help="Comma-separated validation columns.")
    parser.add_argument('--stride', type=int, default=1, help="Integer stride logic size configuration.")
    parser.add_argument('--workers', type=int, default=1, help="System worker threshold allocation.")
    parser.add_argument('--verbose', action='store_true', help="Verbose logging trace updates.")
    
    args = parser.parse_args()
    
    set_bounds = [int(x) for x in args.sets.split('-')]
    run_bounds = [int(x) for x in args.runs.split('-')]
    
    filter_agents = [a.strip() for a in args.agent_types.split(',')] if args.agent_types else None
    filter_metrics = [m.strip() for m in args.metrics.split(',')] if args.metrics else None
    
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