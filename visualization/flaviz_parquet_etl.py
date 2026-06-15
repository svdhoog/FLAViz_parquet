#!/usr/bin/env python3
"""
================================================================================
FLAViz-Engine: High-Performance Unified Agent-Type ETL Suite
================================================================================
Description:
    Processes hierarchical simulation folder structures using flexible wildcard 
    masks (*{AgentType}.parquet) to swallow filename variations while relying on 
    the simulation's pre-sorted agent file hierarchy.

Optimizations:
    - Streams records in 50k row chunks via PyArrow.
    - Low-precision downcasting: metadata to int16, floating points to float32.
    - Combines unordered multi-processing with a fast final coordinate sort.
================================================================================
"""

import os
import re
import gc
import sys
import time
import argparse
import glob
import multiprocessing
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

def init_worker():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def process_single_agent_file(args):
    """
    Transforms a single pre-sorted agent file into standardized memory segments.
    """
    file_path, set_num, run_num, agent_type = args
    try:
        parquet_file = pq.ParquetFile(file_path)
        column_names = parquet_file.schema.names
        
        time_col = None
        for candidate in ['time_step', 'iteration', 'tick']:
            if candidate in column_names:
                time_col = candidate
                break
        if not time_col:
            return None

        id_col = None
        for candidate in ['ID', 'id', 'agent_id']:
            if candidate in column_names:
                id_col = candidate
                break

        reserved = {time_col, id_col if id_col else '', 'set_num', 'run_num', 'id', 'ID', 'time_step'}
        metric_columns = [col for col in column_names if col not in reserved]

        batches_processed = []
        for batch in parquet_file.iter_batches(batch_size=50_000):
            total_rows = batch.num_rows
            if total_rows == 0:
                continue

            set_arr = pa.array(np.repeat(set_num, total_rows).astype(np.int16))
            run_arr = pa.array(np.repeat(run_num, total_rows).astype(np.int16))
            time_arr = batch.column(time_col).cast(pa.int16())
            
            if id_col:
                id_arr = batch.column(id_col).cast(pa.int16() if pa.types.is_integer(batch.column(id_col).type) else pa.int64())
            else:
                id_arr = pa.array(np.arange(total_rows, dtype=np.int16))

            final_arrays = [set_arr, run_arr, time_arr, id_arr]
            final_names = ['set_num', 'run_num', 'time_step', 'ID']

            for m in metric_columns:
                col_type = batch.column(m).type
                if pa.types.is_floating(col_type):
                    final_arrays.append(batch.column(m).cast(pa.float32()))
                elif pa.types.is_integer(col_type):
                    final_arrays.append(batch.column(m).cast(pa.int16()))
                else:
                    final_arrays.append(batch.column(m))
                final_names.append(m)

            batches_processed.append(pa.RecordBatch.from_arrays(final_arrays, names=final_names))

        if not batches_processed:
            return None
            
        return pa.Table.from_batches(batches_processed)
    except Exception:
        return None

def run_etl_pipeline(root_dir, agent_type, set_range, run_range, num_workers, output_path, verbose):
    if verbose:
        print(f"[{time.strftime('%H:%M:%S')}] [START] Scanning for Agent Class: '{agent_type}'...")
        
    # Wildcard mask safely processes files given the pre-sorted structure of the hierarchy
    target_pattern = f"*{agent_type}.parquet"
    scan_queue = []

    glob_path = os.path.join(root_dir, "set_*", "run_*", target_pattern).replace("\\", "/")
    for file_path in glob.iglob(glob_path):
        parts = file_path.replace("\\", "/").split("/")
        s_val = int(re.search(r'\d+', parts[-3]).group())
        r_val = int(re.search(r'\d+', parts[-2]).group())
        if (set_range[0] <= s_val <= set_range[1]) and (run_range[0] <= r_val <= run_range[1]):
            scan_queue.append((file_path, s_val, r_val, agent_type))

    if not scan_queue:
        print(f"  [Warning] No files matched filters for '{agent_type}'.")
        return

    if verbose:
        print(f"[{time.strftime('%H:%M:%S')}] [INGEST] Staging {len(scan_queue)} partitions...")

    collected_tables = []
    processed_count = 0

    with multiprocessing.Pool(processes=num_workers, initializer=init_worker) as pool:
        for processed_table in pool.imap_unordered(process_single_agent_file, scan_queue):
            if processed_table is not None:
                collected_tables.append(processed_table)
                processed_count += 1
                if processed_count % 500 == 0:
                    gc.collect()

    if collected_tables:
        if verbose:
            print(f"[{time.strftime('%H:%M:%S')}] [MERGE] Concatenating tables...")
        
        unified_table = pa.concat_tables(collected_tables, promote_options='permissive')
        
        if verbose:
            print(f"[{time.strftime('%H:%M:%S')}] [SORT] Organizing rows into unified coordinates...")
        sort_indices = pc.sort_indices(unified_table, sort_keys=[
            ("set_num", "ascending"),
            ("run_num", "ascending"),
            ("time_step", "ascending"),
            ("ID", "ascending")
        ])
        unified_table = unified_table.take(sort_indices)
        
        if verbose:
            print(f"[{time.strftime('%H:%M:%S')}] [WRITE] Compressing final matrix -> {output_path}")
            
        pq.write_table(unified_table, output_path, compression='SNAPPY', use_dictionary=True)
        
        del unified_table
        del collected_tables
        gc.collect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="FLAViz Architectural ETL Extraction Pipeline.")
    parser.add_argument('-i', '--input', required=True)
    parser.add_argument('-o', '--output', required=True)
    parser.add_argument('--agent-types', required=True)
    parser.add_argument('--sets', required=True)
    parser.add_argument('--runs', required=True)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    os.environ.update({"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})
    
    set_bounds = [int(x) for x in args.sets.split('-')]
    run_bounds = [int(x) for x in args.runs.split('-')]
    agents = [a.strip() for a in args.agent_types.split(',')]
    
    os.makedirs(args.output, exist_ok=True)

    for agent in agents:
        out_file = os.path.join(args.output, f"checkpoint_{agent}.parquet")
        t0 = time.time()
        run_etl_pipeline(args.input, agent, set_bounds, run_bounds, args.workers, out_file, args.verbose)
        if args.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] [COMPLETE] '{agent}' completed in {time.time() - t0:.2f}s.\n")