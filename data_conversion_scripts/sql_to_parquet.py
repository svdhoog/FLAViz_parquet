#!/usr/bin/env python3
"""
================================================================================
SQL to Parquet Hierarchical Dataset Converter (Production Parallel Version)
================================================================================
Description:
    Recursively converts legacy SQLite simulation outputs into a mirrored 
    compressed Apache Parquet hierarchy using a parallel, fault-tolerant worker 
    pool. Features include safe keyboard interrupt termination, incremental up-to-date 
    skipping logic, and system memory leak protections.

Usage Syntax:
    $ python sql_to_parquet.py --input ./legacy_sql_runs \
        --output ./parquet_mirror --sets 1-513 --runs 1-1000 --force

Command-Line Arguments & Flags:
    -i, --input    [Required] Top-level folder containing the legacy simulation
                              database hierarchy.
    -o, --output   [Optional] Target folder where the parallel mirrored Parquet
                              hierarchy will be generated.
                              Default: "./parquet_mirror_output"
    --sets         [Optional] Inclusive range of sets to process (e.g., 1-5).
    --runs         [Optional] Inclusive range of runs to process (e.g., 1-1000).
    -w, --workers  [Optional] Number of parallel process workers to spawn.
                              Default: Host logical core count.
    --force        [Optional] Overwrite existing targets, disabling skipping
                              logic optimization.
================================================================================
"""

import os
import re
import sys
import signal
import argparse
import multiprocessing
from sqlalchemy import create_engine, inspect
import pandas as pd
import pyarrow as pa
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
        raise argparse.ArgumentTypeError(f"Invalid range: start ({start}) cannot exceed end ({end}).")
    return (start, end)

def is_in_range(value_str, range_tuple):
    if range_tuple is None:
        return True
    match = re.search(r'\d+', value_str)
    if not match:
        return False
    return range_tuple[0] <= int(match.group()) <= range_tuple[1]

def parse_legacy_flat_filename(filename):
    pattern = r'^(set_[a-zA-Z0-9]+)_(run_[a-zA-Z0-9]+)(?:_.*)?\.(?:db|sqlite|sqlite3)$'
    match = re.match(pattern, filename, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    return None

def convert_single_sqlite_to_parquet(task_args):
    db_path, root_input, root_output, set_range, run_range, overwrite_flag = task_args
    
    try:
        db_abs = os.path.abspath(db_path)
        filename = os.path.basename(db_abs)
        current_dir = os.path.dirname(db_abs)
        
        legacy_components = parse_legacy_flat_filename(filename)
        rel_subpath = os.path.relpath(current_dir, os.path.abspath(root_input))
        
        if legacy_components:
            set_dir, run_dir = legacy_components
            path_parts = rel_subpath.replace("\\", "/").split("/")
            
            out_parts = [root_output]
            if rel_subpath != '.':
                out_parts.append(rel_subpath)
            if set_dir not in path_parts:
                out_parts.append(set_dir)
            if run_dir not in path_parts:
                out_parts.append(run_dir)
                
            target_out = os.path.normpath(os.path.join(*out_parts))
        else:
            # If folders already match set_*/run_*, rel_subpath natively contains them.
            target_out = os.path.normpath(os.path.join(root_output, rel_subpath))
        
        if not overwrite_flag and os.path.exists(target_out):
            if any(f.endswith('.parquet') for f in os.listdir(target_out) if os.path.isfile(os.path.join(target_out, f))):
                return "SKIPPED"

        engine = create_engine(f"sqlite:///{db_abs}")
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        if not table_names:
            engine.dispose()
            return "EMPTY"
        
        os.makedirs(target_out, exist_ok=True)
        
        for table_name in table_names:
            df = pd.read_sql_table(table_name, con=engine)
            if df.empty:
                continue

            for col in df.columns:
                if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
                    stripped_col = df[col].astype(str).str.strip()
                    sample = stripped_col[stripped_col != '']
                    if not sample.empty and sample.str.match(r'^-?\d+(?:\.\d+)?$').all():
                        converted = pd.to_numeric(df[col], errors='coerce')
                        if not converted.isna().all():
                            df[col] = converted
            
            arrow_table = pa.Table.from_pandas(df)
            pq.write_table(arrow_table, os.path.join(target_out, f"data_{table_name}.parquet"), compression='SNAPPY')
            
        engine.dispose()
        return "CONVERTED"
    except Exception as e:
        return f"ERROR: {e}"

def main():
    parser = argparse.ArgumentParser(description="Production Parallel SQL to Parquet pipeline configuration.")
    parser.add_argument('-i', '--input', required=True, help="Top-level folder containing the legacy simulation database hierarchy.")
    parser.add_argument('-o', '--output', default="./parquet_mirror_output", help="Target folder where the parallel mirrored Parquet hierarchy will be generated.")
    parser.add_argument('--sets', type=parse_range_arg, help="Inclusive range of sets to process (e.g., 1-5)")
    parser.add_argument('--runs', type=parse_range_arg, help="Inclusive range of runs to process (e.g., 1-1000)")
    parser.add_argument('-w', '--workers', type=int, default=multiprocessing.cpu_count(), help="Number of parallel process workers to spawn (defaults to host logical core count).")
    parser.add_argument('--force', action='store_true', help="Overwrite existing targets, disabling skipping logic optimization.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"[FATAL] Root path '{args.input}' does not exist.")
        sys.exit(1)
        
    print("Scoping filesystem files matching bounds...")
    db_exts = ('.db', '.sqlite', '.sqlite3')
    task_queue = []
    
    for root, _, files in os.walk(args.input):
        for file in files:
            if file.endswith(db_exts):
                legacy_components = parse_legacy_flat_filename(file)
                if legacy_components:
                    if not is_in_range(legacy_components[0], args.sets) or not is_in_range(legacy_components[1], args.runs):
                        continue
                else:
                    rel_sub = os.path.relpath(root, args.input)
                    parts = rel_sub.replace("\\", "/").split("/")
                    set_p = [p for p in parts if re.match(r'^set_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
                    run_p = [p for p in parts if re.match(r'^run_[a-zA-Z0-9]+$', p, re.IGNORECASE)]
                    if set_p and not is_in_range(set_p[-1], args.sets): continue
                    if run_p and not is_in_range(run_p[-1], args.runs): continue
                
                task_queue.append((os.path.join(root, file), args.input, args.output, args.sets, args.runs, args.force))

    total_jobs = len(task_queue)
    print(f"Queue established. Found {total_jobs} active targets configuration. Initializing system execution workers...")
    
    stats = {"CONVERTED": 0, "SKIPPED": 0, "EMPTY": 0, "ERROR": 0}
    
    with multiprocessing.Pool(processes=args.workers, initializer=init_worker, maxtasksperchild=200) as pool:
        try:
            results = pool.imap_unordered(convert_single_sqlite_to_parquet, task_queue, chunksize=10)
            for idx, res in enumerate(results, 1):
                if res.startswith("ERROR"):
                    stats["ERROR"] += 1
                    print(f"\n  [Worker Alert] {res}")
                else:
                    stats[res] += 1
                
                if idx % max(1, total_jobs // 50) == 0 or idx == total_jobs:
                    print(f" -> Progression: [{idx}/{total_jobs}] ({(idx / total_jobs) * 100:.2f}%) Complete. (Converted: {stats['CONVERTED']} | Skipped: {stats['SKIPPED']})", flush=True)
        except KeyboardInterrupt:
            print("\n[CRITICAL ALERT] User sent interrupt via termination control (Ctrl+C). Cleaning context matrices and shutting down pools...")
            pool.terminate()
            pool.join()
            print("System components cleared safely.")
            sys.exit(130)

    print(f"\nExecution finished.\n -> Converted: {stats['CONVERTED']}\n -> Skipped: {stats['SKIPPED']}\n -> Errors/Failed: {stats['ERROR']}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()