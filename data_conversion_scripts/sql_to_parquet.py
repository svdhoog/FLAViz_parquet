#!/usr/bin/env python3
"""
================================================================================
SQL to Parquet Hierarchical Dataset Converter (With Auto-Numeric Casting)
================================================================================
Description:
    Recursively travels down an input folder tree to locate simulation database
    files (.db, .sqlite, .sqlite3), extracts each internal table as a distinct 
    agent data set, and mirrors the entire folder hierarchy into an isolated,
    parallel target directory using compressed Apache Parquet format.

    Automatically detects text-encoded (VARCHAR) numeric columns inherited from
    legacy FLAME loggers and converts them to true numeric types on disk.

Prerequisites / Dependencies:
    $ pip install pandas pyarrow sqlalchemy

Usage Syntax:
    $ python sql_to_parquet.py --input ./legacy_sql_runs --output ./parquet_mirror
================================================================================
"""

import os
import argparse
from sqlalchemy import create_engine, inspect
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

def convert_sqlite_to_parquet(db_path, root_input_dir, root_output_dir):
    """
    Connects to a single SQLite database file, extracts all tables, optimizes
    column text-to-numeric data types, and saves each table as a compressed Parquet
    file inside a mirrored parallel output directory structure.
    """
    db_abs_path = os.path.abspath(db_path)
    input_dir_abs = os.path.abspath(root_input_dir)
    output_dir_abs = os.path.abspath(root_output_dir)
    
    current_db_dir = os.path.dirname(db_abs_path)
    rel_subpath = os.path.relpath(current_db_dir, input_dir_abs)
    target_output_dir = os.path.normpath(os.path.join(output_dir_abs, rel_subpath))
    
    engine = create_engine(f"sqlite:///{db_abs_path}")
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    if not table_names:
        print(f"  [Skipped] No tables found inside: {os.path.basename(db_path)}")
        engine.dispose()
        return

    print(f"  Processing {os.path.basename(db_path)}:")
    
    for table_name in table_names:
        df = pd.read_sql_table(table_name, con=engine)
        
        if df.empty:
            continue

        # --- AUTO-CASTING LOGIC: Fix VARCHAR-encoded numbers ---
        for col in df.columns:
            # Check if column is stored as text/object type
            if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
                # Strip potential whitespace
                stripped_col = df[col].astype(str).str.strip()
                
                # Check if the non-empty rows are purely numeric
                # (Handles both integers and floating points)
                sample = stripped_col[stripped_col != '']
                if not sample.empty and sample.str.match(r'^-?\d+(?:\.\d+)?$').all():
                    # Attempt safe dynamic conversion to numeric
                    # 'coerce' turns invalid entries to NaN safely
                    converted = pd.to_numeric(df[col], errors='coerce')
                    
                    # If conversion succeeded without losing the whole column, commit it
                    if not converted.isna().all():
                        df[col] = converted
                        print(f"    * Auto-cast column '{col}' in table '{table_name}' from VARCHAR to Numeric")
        
        # Convert the cleaned, optimized dataframe to an immutable Apache Arrow Table
        arrow_table = pa.Table.from_pandas(df)
        
        parquet_filename = f"data_{table_name}.parquet"
        parquet_path = os.path.join(target_output_dir, parquet_filename)
        
        if not os.path.exists(target_output_dir):
            os.makedirs(target_output_dir)
            
        pq.write_table(arrow_table, parquet_path, compression='SNAPPY')
        print(f"    -> Extracted table '{table_name}' into mirror: .../{rel_subpath}/{parquet_filename}")
        
    engine.dispose()

def count_database_files(root_input_dir, extensions):
    """Scans the directory tree beforehand to determine the total number of DB files."""
    count = 0
    for root, _, files in os.walk(root_input_dir):
        for file in files:
            if file.endswith(extensions):
                count += 1
    return count

def traverse_and_transform(root_input_dir, root_output_dir):
    """Recursively converts hierarchical SQLite database files to typed Parquet structures."""
    if not os.path.exists(root_input_dir):
        print(f"[FATAL ERROR] The specified input folder '{root_input_dir}' does not exist.")
        return

    db_extensions = ('.db', '.sqlite', '.sqlite3')
    total_files = count_database_files(root_input_dir, db_extensions)
    
    print(f"Starting parallel batch transformation\n" + "="*70)
    print(f"Source Root: {os.path.abspath(root_input_dir)}")
    print(f"Target Mirror Root: {os.path.abspath(root_output_dir)}")
    print(f"Total Database Files Found: {total_files}")
    print("="*70)
    
    if total_files == 0:
        print("No target database files detected to transform.")
        return

    processed_count = 0
    total_converted = 0
    
    for root, dirs, files in os.walk(root_input_dir):
        for file in files:
            if file.endswith(db_extensions):
                full_db_path = os.path.join(root, file)
                processed_count += 1
                
                progress_percentage = (processed_count / total_files) * 100
                rel_path = os.path.relpath(full_db_path, root_input_dir)
                print(f"\n[{progress_percentage:6.2f}%] [Found Database {processed_count}/{total_files}] {rel_path}")
                
                try:
                    convert_sqlite_to_parquet(full_db_path, root_input_dir, root_output_dir)
                    total_converted += 1
                except Exception as e:
                    print(f"  [ERROR] Failed processing {file}. Reason: {e}")
                    
    print("\n" + "="*70 + f"\nTransformation complete! Successfully processed {total_converted} database clusters.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract tables from a hierarchical SQLite tree and mirror it into a parallel Parquet dataset tree with automatic type casting."
    )
    parser.add_argument(
        '-i', '--input', 
        required=True, 
        help="Top-level folder containing the legacy simulation database hierarchy."
    )
    parser.add_argument(
        '-o', '--output', 
        default="./parquet_mirror_output", 
        help="Target folder where the parallel mirrored Parquet hierarchy will be generated."
    )
    
    args = parser.parse_args()
    traverse_and_transform(args.input, args.output)