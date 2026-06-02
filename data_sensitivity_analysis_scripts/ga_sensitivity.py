#!/usr/bin/env python3
"""
================================================================================
Global Sensitivity Analysis (GSA) Module for Simulation Datasets
================================================================================
Description:
    Scans a structured Parquet mirror directory, extracts aggregate performance 
    metrics across variations (sets) and replications (runs), maps them to a 
    parameter design space, and computes Global Sensitivity Analysis metrics.

    Configured to map the 8 simulation parameters to their explicit economic names:
    - α     : Capital Adequacy Ratio
    - β     : Reserve Requirement Ratio
    - γ     : Price Sensitivity
    - d     : Dividend Ratio
    - φ     : Debt Rescaling Ratio
    - τ     : Tax Rate
    - T     : Debt Repayment (months)
    - r^ecb : Base Interest Rate

Usage Syntax:
    $ python sensitivity_analysis.py --input ./parquet_mirror_output \
        --parameters sample_513_mode_3.csv \
        --table Agent_n \
        --metric wealth
================================================================================
"""

import os
import re
import argparse
import pandas as pd
import numpy as np

def load_parameter_design(csv_path):
    """
    Loads the headerless design matrix (e.g., sample_513_mode_3.csv).
    Maps column 0 to 'set_id' and explicitly maps columns 1-8 to the 
    defined 8 economic parameters.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Parameter design file not found at: {csv_path}")
    
    # Read without a header row to capture all 513 rows of data cleanly
    df = pd.read_csv(csv_path, header=None)
    
    # Structural definition matching the order of variables in the design space
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
    
    # Create descriptive column headers (e.g., "α (Capital Adequacy Ratio)")
    param_names = [f"{p['symbol']} ({p['name']})" for p in param_definitions]
    
    rename_dict = {0: 'set_id'}
    for i, name in enumerate(param_names):
        rename_dict[i + 1] = name
        
    df.rename(columns=rename_dict, inplace=True)
    df['set_id'] = df['set_id'].astype(str).str.strip()
    
    return df, param_names

def aggregate_simulation_outputs(root_dir, table_name, metric_name):
    """
    Traverses the structured output directory to collect and aggregate metrics.
    Maps root_dir/set_x/run_y/data_[table_name].parquet into a grouped dataframe.
    """
    records = []
    target_file = f"data_{table_name}.parquet"
    
    print(f"Scanning target mirror for output files: {target_file}")
    
    for root, dirs, files in os.walk(root_dir):
        if target_file in files:
            file_path = os.path.join(root, target_file)
            parts = root.replace("\\", "/").split("/")
            
            # Identify path tokens corresponding to simulation sets and runs
            set_match = [p for p in parts if re.match(r'^set_[a-zA-Z0-9]+$', p)]
            run_match = [p for p in parts if re.match(r'^run_[a-zA-Z0-9]+$', p)]
            
            if set_match and run_match:
                set_id = set_match[-1]
                run_id = run_match[-1]
                
                try:
                    df = pd.read_parquet(file_path, columns=[metric_name])
                    if df.empty:
                        continue
                    
                    # Compute mean performance metric for this specific run replication
                    mean_value = df[metric_name].mean()
                    
                    records.append({
                        'set_id': set_id,
                        'run_id': run_id,
                        'output_value': mean_value
                    })
                except Exception as e:
                    print(f"  [Warning] Could not read {file_path}. Reason: {e}")
                    
    if not records:
        raise ValueError(f"No aggregated records found for table '{table_name}' and metric '{metric_name}'.")

    df_raw = pd.DataFrame(records)
    df_set_aggregated = df_raw.groupby('set_id')['output_value'].mean().reset_index()
    return df_set_aggregated

def perform_gsa(df_merged, parameter_columns):
    """
    Executes a Global Sensitivity Analysis contribution evaluation.
    """
    print("\n" + "="*85 + "\nExecuting Global Sensitivity Analysis\n" + "="*85)
    
    X = df_merged[parameter_columns].values
    Y = df_merged['output_value'].values
    
    if np.var(Y) == 0:
        print("[ERROR] Output metric has zero variance across sets. Sensitivity analysis cannot proceed.")
        return

    print("Parameter Boundaries Analyzed:")
    for col in parameter_columns:
        print(f"  * {col:<35} : [{df_merged[col].min():>12.4f}, {df_merged[col].max():>12.4f}]")

    try:
        print("\n--- Feature Correlation / Variance Contribution Proxy ---")
        correlations = {}
        for col in parameter_columns:
            corr = df_merged[col].corr(pd.Series(Y))
            correlations[col] = corr if not np.isnan(corr) else 0.0
            
        total_sq_corr = sum(c**2 for c in correlations.values())
        
        print(f"{'Economic Parameter Name':<40} | {'Pearson R':<12} | {'Estimated Variance Contribution':<30}")
        print("-" * 90)
        for param, r_val in correlations.items():
            # Variance contribution proxy using normalized R-squared values
            contribution = (r_val**2 / total_sq_corr * 100) if total_sq_corr > 0 else 0.0
            print(f"{param:<40} | {r_val:>11.4f} | {contribution:>28.2f}%")
            
    except Exception as e:
        print(f"[ERROR] Statistical computation failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Global Sensitivity Analysis Module")
    parser.add_argument('-i', '--input', required=True, help="Path to the mirrored Parquet output folder root.")
    parser.add_argument('-p', '--parameters', required=True, help="Path to CSV containing input parameter configs per set.")
    parser.add_argument('-t', '--table', required=True, help="Name of the inner agent database table to extract.")
    parser.add_argument('-m', '--metric', required=True, help="Column name within the table to use as performance target.")
    
    args = parser.parse_args()
    
    try:
        # 1. Load setup parameter matrix
        df_params, verified_param_cols = load_parameter_design(args.parameters)
        
        # 2. Extract and pool outcomes from parquet files across sets and runs
        df_outputs = aggregate_simulation_outputs(args.input, args.table, args.metric)
        
        # 3. Join design variables with outcomes
        df_merged = pd.merge(df_params, df_outputs, on='set_id', how='inner')
        
        # String normalization fallback logic if file uses 'set_1' but folder paths use 'set_01' formatting
        if df_merged.empty:
            df_params['set_id'] = df_params['set_id'].apply(lambda x: f"set_{int(re.search(r'\d+', x).group()):02d}" if re.search(r'\d+', x) else x)
            df_merged = pd.merge(df_params, df_outputs, on='set_id', how='inner')
            
            if df_merged.empty:
                print("[FATAL] Intersection between parameter CSV 'set_id' and Parquet path 'set_x' IDs is empty.")
                return
            
        print(f"\nSuccessfully matched {len(df_merged)} simulation sets for GSA.")
        
        # 4. Compute Sensitivity
        perform_gsa(df_merged, verified_param_cols)
        
    except Exception as err:
        print(f"\n[FATAL ERROR] {err}")

if __name__ == "__main__":
    main()