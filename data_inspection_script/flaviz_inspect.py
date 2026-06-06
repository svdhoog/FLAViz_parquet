#!/usr/bin/env python3
"""
================================================================================
FLAViz Data Pipeline Inspector (Dynamic Range & Column Alignment Mode)
================================================================================
Description:
    Recursively scans a hierarchical Parquet tree to provide architectural 
    insights into your simulation output files. Maps out parameter sets, 
    stochastic run counts, unified iteration scopes, active agent tables, and 
    associated attribute schemas.

    Cleans output arrays by purging internal tracking tables like '_iters_' 
    and stripping structural index properties like '_ITERATION_NO' from schemas.
    Dynamically sizes column spaces to prevent overlap on long variable names.

    Supports targeted subset profiling via range constraints on sets and runs.

Command Line Arguments (argparse):
    -i, --input  (Required) : Path leading to the top-level mirrored Parquet 
                             directory hierarchy.
    -o, --output (Optional) : File path/name destination to write a summary 
                             report file instead of printing to the terminal.
    --sets       (Optional) : Target parameter subset range index limit block 
                             selection rule. Fully inclusive. (e.g., '1-256' or '12').
    --runs       (Optional) : Target stochastic simulation run count boundary 
                             rule constraints. Fully inclusive. (e.g., '1-500' or '1000').

Usage Syntax Examples:
    $ python flaviz_inspect.py -i ./parquet_mirror_output
    $ python flaviz_inspect.py -i ./parquet_mirror_output -o ./summary.txt
    $ python flaviz_inspect.py -i ./parquet_mirror_output --sets 1-256 --runs 1-500
================================================================================
"""

import os
import sys
import re
import argparse
import duckdb

class ParquetDatasetInspector:
    def __init__(self, root_dir, output_file=None, sets_range=None, runs_range=None):
        self.root_dir = os.path.abspath(root_dir)
        self.conn = duckdb.connect()
        self.output_file = output_file
        self.sets_filter = self._parse_range_string(sets_range)
        self.runs_filter = self._parse_range_string(runs_range)
        self._output_buffer = []

    def _parse_range_string(self, range_str):
        """
        Parses strings like '1-256', '5', or '100-200' into a set of integers.
        Returns None if no range string is provided, implying no constraint.
        """
        if not range_str:
            return None
        
        allowed_indices = set()
        # Match a single number or a bounding range block
        pattern = re.compile(r'^(\d+)(?:-(\d+))?$')
        match = pattern.match(str(range_str).strip())
        
        if not match:
            print(f"[FATAL ERROR] Invalid range constraint expression: '{range_str}'")
            print("Please use standard formatting integers or boundary bounds (e.g., '5' or '1-256').")
            sys.exit(1)
            
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
        
        if start > end:
            start, end = end, start
            
        return set(range(start, end + 1))

    def _should_include(self, entry_name, filter_set):
        """
        Extracts the numeric suffix identifier from directory names like 
        'set_513' or 'run_1000' and evaluates it against target range limits.
        """
        if filter_set is None:
            return True
            
        # Extract trailing digits using a generic regular expression match
        num_match = re.search(r'(\d+)$', entry_name)
        if not num_match:
            return False # Skip directories lacking structured numeric indexing definitions
            
        idx_val = int(num_match.group(1))
        return idx_val in filter_set

    def log(self, text=""):
        """Buffers text lines to output to file or terminal dynamically."""
        if self.output_file:
            self._output_buffer.append(text)
        else:
            print(text)

    def flush_buffer(self):
        """Writes buffered output logs to the targeted summary text file."""
        if not self.output_file:
            return
        
        out_abs_path = os.path.abspath(self.output_file)
        out_dir = os.path.dirname(out_abs_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        try:
            with open(out_abs_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self._output_buffer) + "\n")
            print(f"Inspection complete. Summary log successfully exported to: {out_abs_path}")
        except IOError as e:
            print(f"[FATAL ERROR] Failed to write summary file to disk. Reason: {e}")
            sys.exit(1)

    def inspect(self):
        self.log("=" * 80)
        self.log("FLAVIZ DATASET ARCHITECTURE REPORT")
        self.log(f"Target Directory: {self.root_dir}")
        if self.sets_filter or self.runs_filter:
            self.log(f"Scope Filters: Sets Filter={bool(self.sets_filter)} | Runs Filter={bool(self.runs_filter)}")
        self.log("=" * 80)

        # 1. Detect and Filter Parameter Sets (Top-level Subdirectories)
        all_subdirs = [d for d in os.listdir(self.root_dir) if os.path.isdir(os.path.join(self.root_dir, d))]
        subdirs = [d for d in all_subdirs if self._should_include(d, self.sets_filter)]
        
        if not subdirs:
            print("[FATAL ERROR] No matching parameter sets or subdirectories found under provided range guidelines.")
            sys.exit(1)

        self.log(f"\n[+] Parameter Sets Filtered & Selected ({len(subdirs)} of {len(all_subdirs)} total):")
        for s in sorted(subdirs):
            self.log(f"    - {s}")

        agent_schemas = {}
        global_run_count = 0

        self.log("\n" + "-" * 80)
        self.log("DIAGNOSTIC MATRIX BY PARAMETER SET")
        self.log("-" * 80)

        for p_set in sorted(subdirs):
            p_set_path = os.path.join(self.root_dir, p_set)
            
            # 2. Count and Filter Stochastic Monte Carlo Runs per set
            all_runs = [r for r in os.listdir(p_set_path) if os.path.isdir(os.path.join(p_set_path, r))]
            runs = [r for r in all_runs if self._should_include(r, self.runs_filter)]
            global_run_count += len(runs)
            
            self.log(f"\n* Parameter Set: {p_set}")
            self.log(f"  └── Matching Monte Carlo Runs (Seeds): {len(runs)} (out of {len(all_runs)} total)")

            if not runs:
                self.log("  └── [Warning] No run folders matching constraint located inside this set.")
                continue

            # Target the first available run matching range selection criteria to check file schemas
            sample_run_path = os.path.join(p_set_path, sorted(runs)[0])
            parquet_files = [f for f in os.listdir(sample_run_path) if f.endswith('.parquet')]
            
            # Filter file names immediately to exclude non-agent files and metadata placeholders
            valid_parquet_files = []
            for f in parquet_files:
                if "_iters_" in f:
                    continue
                if f.startswith("data_") and f.endswith(".parquet"):
                    valid_parquet_files.append(f)

            if not valid_parquet_files:
                self.log("  └── [Warning] No valid agent Parquet files located inside sample run data nodes.")
                continue

            # 3. Calculate Unified Timeline Scope at the Run-Level
            first_file_path = os.path.join(sample_run_path, valid_parquet_files[0])
            try:
                iter_info = self.conn.execute(f"""
                    SELECT 
                        MIN(_ITERATION_NO) as min_i, 
                        MAX(_ITERATION_NO) as max_i, 
                        COUNT(DISTINCT _ITERATION_NO) as count_i 
                    FROM '{first_file_path}'
                """).fetchone()
                timeline_str = f"Iterations: {iter_info[0]} to {iter_info[1]} ({iter_info[2]} discrete ticks)"
            except Exception:
                timeline_str = "Iterations: Meta tracking variable (_ITERATION_NO) not found"

            self.log(f"  ├── Timeline Profile: {timeline_str}")

            # 4. Process Individual Agent Types
            for p_file in sorted(valid_parquet_files):
                agent_type = p_file.replace("data_", "").replace(".parquet", "")
                full_file_path = os.path.join(sample_run_path, p_file)
                
                self.log(f"  │   ├── Agent Found: '{agent_type}'")

                # 5. Extract Structural Column Fields (Variables)
                if agent_type not in agent_schemas:
                    try:
                        columns_meta = self.conn.execute(f"DESCRIBE SELECT * FROM '{full_file_path}'").fetchall()
                        
                        variables = []
                        for col in columns_meta:
                            col_name = col[0]
                            if col_name == "_ITERATION_NO":
                                continue
                            variables.append(col_name)
                            
                        agent_schemas[agent_type] = variables
                    except Exception as e:
                        agent_schemas[agent_type] = [f"Error extracting columns: {e}"]

        # 6. Global Variable Schema Manifest printout with Dynamic Scaling
        self.log("\n" + "=" * 80)
        self.log("COMPREHENSIVE AGENT ATTRIBUTE SCHEMA MANIFEST")
        self.log("=" * 80)
        
        for agent_type, vars_list in sorted(agent_schemas.items()):
            self.log(f"\n[Agent Class: {agent_type}]")
            self.log(f"Total Columns/Variables (Excl. Iteration Indices): {len(vars_list)}")
            self.log("-" * 40)
            
            if not vars_list:
                self.log("  (No variables found)")
                continue

            # Find longest string in the current agent variable array
            max_var_len = max(len(v) for v in vars_list)
            col_width = max_var_len + 4 # Pad out with a clean 4-space gap element
            
            for i in range(0, len(vars_list), 3):
                chunk = vars_list[i:i+3]
                formatted_row = "".join(f"{v:<{col_width}}" for v in chunk)
                self.log(f"  {formatted_row}")
                
        self.log("\n" + "=" * 80)
        self.log(f"Inspection complete. Total unique Monte Carlo cells traversed: {global_run_count}")
        self.log("=" * 80)

        self.flush_buffer()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inspect and profile your FLAME Parquet simulation schema metrics with range control limits."
    )
    parser.add_argument(
        '-i', '--input', 
        required=True, 
        help="Path leading to the top-level mirrored Parquet directory hierarchy."
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help="Optional file path/name destination to write a summary report file instead of printing to terminal."
    )
    parser.add_argument(
        '--sets',
        default=None,
        help="Target parameter subset range index limit block selection rule (e.g., '1-256' or '12')."
    )
    parser.add_argument(
        '--runs',
        default=None,
        help="Target stochastic simulation run count boundary rule constraints (e.g., '1-500' or '1000')."
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"[FATAL ERROR] Target folder directory path does not exist: {args.input}")
        sys.exit(1)
        
    inspector = ParquetDatasetInspector(
        root_dir=args.input, 
        output_file=args.output, 
        sets_range=args.sets, 
        runs_range=args.runs
    )
    inspector.inspect()
    