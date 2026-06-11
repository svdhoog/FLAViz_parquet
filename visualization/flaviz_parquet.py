#!/usr/bin/env python3
"""
================================================================================
FLAViz-Engine: Superimposed Multi-Iteration Plotting Suite (Strict & Inclusive)
================================================================================
Description:
    Implements native FLAViz core plotting routines over unified high-level
    datasets. Dynamically resolves data files by running boundary-safe pattern
    matching on variable names, allowing fluid support for 'checkpoint_$var',
    'data_$var', or '$var' files in both .parquet and .feather formats.
    
    Automatically superimposes multiple iteration values onto a single chart
    axis when a JSON range object is provided for 'target_iteration'.

    Enforces strict validation: any missing parameters in a range definition
    or plot configuration will halt execution immediately.
    
    Treats the range 'stop' parameter as fully inclusive.

Dependencies:
    $ pip install duckdb pandas matplotlib numpy pyarrow
================================================================================
"""

import os
import sys
import json
import re
import argparse
import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class UnifiedFlavizEngine:
    def __init__(self, data_root_dir):
        """Initializes the engine using an active serverless DuckDB driver."""
        self.root_dir = os.path.abspath(data_root_dir)
        self.conn = duckdb.connect()
        # Cache available files in the input folder to speed up regex evaluations
        if os.path.isdir(self.root_dir):
            self.available_files = os.listdir(self.root_dir)
        else:
            self.available_files = []

    def _resolve_metric_source(self, var_name):
        """
        Scans available directory contents using regex pattern matching to bind
        variables to their respective files regardless of prefix (e.g. data_ or checkpoint_).
        """
        # Matches the variable name bounded by string limits, hyphens, or underscores
        pattern = re.compile(rf"(?:^|[^a-zA-Z0-9]){re.escape(var_name)}(?:^|[^a-zA-Z0-9])")
        matched_files = []

        for f in self.available_files:
            name, ext = os.path.splitext(f)
            if ext.lower() in ['.parquet', '.feather']:
                if pattern.search(name):
                    matched_files.append(f)

        if not matched_files:
            print(f"[FATAL ERROR] No matching Parquet or Feather data source found for metric: '{var_name}'")
            print(f"              Directory scanned: {self.root_dir}")
            sys.exit(1)
        elif len(matched_files) > 1:
            print(f"[FATAL ERROR] Ambiguous metric assignment. Multiple files match pattern for '{var_name}':")
            for mf in matched_files:
                print(f"              -> {mf}")
            print("              Please ensure your metric files have distinct bounding names.")
            sys.exit(1)

        return os.path.join(self.root_dir, matched_files[0])

    # --------------------------------------------------------------------------
    # DATA EXTRACTION AGGREGATORS (DUAL FORMAT & PATTERN MATCHING DRIVEN)
    # --------------------------------------------------------------------------
    def query_time_series(self, p_sets, agent, var, t_var):
        p_sets_clause = ", ".join([f"'{p}'" for p in p_sets])
        source_path = self._resolve_metric_source(var)
        
        query = f"""
            SELECT 
                parameter_set,
                {t_var} as iteration, 
                AVG({var}) as mean_val, 
                MIN({var}) as min_val, 
                MAX({var}) as max_val
            FROM '{source_path}'
            WHERE parameter_set IN ({p_sets_clause})
              AND agent_type = '{agent}'
            GROUP BY parameter_set, {t_var} 
            ORDER BY parameter_set, {t_var}
        """
        return self.conn.execute(query).df()

    def query_snapshot_data(self, p_sets, agent, var, t_var, iterations):
        p_sets_clause = ", ".join([f"'{p}'" for p in p_sets])
        iter_clause = ", ".join([str(i) for i in iterations])
        source_path = self._resolve_metric_source(var)
        
        query = f"""
            SELECT 
                parameter_set,
                {t_var} as iteration,
                {var} as target_value 
            FROM '{source_path}' 
            WHERE parameter_set IN ({p_sets_clause})
              AND agent_type = '{agent}'
              AND {t_var} IN ({iter_clause})
        """
        return self.conn.execute(query).df()

    def query_scatter_data(self, p_sets, agent, var_x, var_y, t_var, iterations):
        p_sets_clause = ", ".join([f"'{p}'" for p in p_sets])
        iter_clause = ", ".join([str(i) for i in iterations])
        
        source_x = self._resolve_metric_source(var_x)
        source_y = self._resolve_metric_source(var_y)
        
        query = f"""
            SELECT 
                x.parameter_set,
                x.{t_var} as iteration,
                x.{var_x} as x_val, 
                y.{var_y} as y_val 
            FROM '{source_x}' x
            INNER JOIN '{source_y}' y
               ON x.parameter_set = y.parameter_set
              AND x.run_id = y.run_id
              AND x.{t_var} = y.{t_var}
              AND x.agent_id = y.agent_id
            WHERE x.parameter_set IN ({p_sets_clause})
              AND x.agent_type = '{agent}'
              AND x.{t_var} IN ({iter_clause})
        """
        return self.conn.execute(query).df()

    def query_delay_data(self, p_sets, agent, var, t_var, lag):
        p_sets_clause = ", ".join([f"'{p}'" for p in p_sets])
        source_path = self._resolve_metric_source(var)
        
        query = f"""
            WITH aggregated AS (
                SELECT 
                    parameter_set,
                    {t_var} as iteration, 
                    AVG({var}) as avg_val 
                FROM '{source_path}' 
                WHERE parameter_set IN ({p_sets_clause})
                  AND agent_type = '{agent}'
                GROUP BY parameter_set, {t_var}
            )
            SELECT 
                parameter_set,
                avg_val as current_val, 
                LAG(avg_val, {lag}) OVER (PARTITION BY parameter_set ORDER BY iteration) as lagged_val
            FROM aggregated
        """
        df = self.conn.execute(query).df()
        return df.dropna()

    # --------------------------------------------------------------------------
    # VISUALIZATION GRAPHICS ENGINES
    # --------------------------------------------------------------------------
    def plot_time_series(self, p_sets, agent, var, t_var):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_time_series(p_sets, agent, var, t_var)
        
        if master_df.empty:
            plt.close(fig)
            return None

        for p_set in p_sets:
            df = master_df[master_df['parameter_set'] == p_set]
            if df.empty: continue
            line, = ax.plot(df['iteration'], df['mean_val'], label=f"Mean: {p_set}", lw=2)
            ax.fill_between(df['iteration'], df['min_val'], df['max_val'], alpha=0.15, color=line.get_color())
            
        ax.set_title(f"Evolution of {var} ({agent} Agents)")
        ax.set_xlabel("Simulation Iteration")
        ax.set_ylabel(var)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

    def plot_box_plot(self, p_sets, agent, var, t_var, iterations):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_snapshot_data(p_sets, agent, var, t_var, iterations)
        
        if master_df.empty:
            plt.close(fig)
            return None

        plot_data = []
        labels = []
        
        for iteration in iterations:
            for p_set in p_sets:
                subset = master_df[(master_df['parameter_set'] == p_set) & (master_df['iteration'] == iteration)]
                if not subset.empty:
                    plot_data.append(subset['target_value'].values)
                    labels.append(f"{p_set}\n(Iter {iteration})")
                    
        if not plot_data: 
            plt.close(fig)
            return None
            
        ax.boxplot(plot_data, labels=labels, patch_artist=True, boxprops=dict(facecolor='lightblue', color='blue'))
        ax.set_title(f"Distribution Over Time: {var} ({agent} Agents)")
        ax.set_ylabel(var)
        ax.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        return fig

    def plot_histogram(self, p_sets, agent, var, t_var, iterations):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_snapshot_data(p_sets, agent, var, t_var, iterations)
        
        if master_df.empty:
            plt.close(fig)
            return None
        
        for iteration in iterations:
            for p_set in p_sets:
                subset = master_df[(master_df['parameter_set'] == p_set) & (master_df['iteration'] == iteration)]
                if not subset.empty:
                    ax.hist(subset['target_value'], bins=30, alpha=0.4, label=f"{p_set} (Iter {iteration})", edgecolor='black')
                    
        ax.set_title(f"Superimposed Frequency Distribution of {var} ({agent} Agents)")
        ax.set_xlabel(var)
        ax.set_ylabel("Frequency Count")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

    def plot_scatter(self, p_sets, agent, var, sec_var, t_var, iterations):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_scatter_data(p_sets, agent, var, sec_var, t_var, iterations)
        
        if master_df.empty:
            plt.close(fig)
            return None
        
        for iteration in iterations:
            for p_set in p_sets:
                subset = master_df[(master_df['parameter_set'] == p_set) & (master_df['iteration'] == iteration)]
                if not subset.empty:
                    ax.scatter(subset['x_val'], subset['y_val'], alpha=0.5, label=f"{p_set} (Iter {iteration})", s=20)
                    
        ax.set_title(f"Superimposed Phase Scatter: {var} vs {sec_var}")
        ax.set_xlabel(var)
        ax.set_ylabel(sec_var)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

    def plot_delay(self, p_sets, agent, var, t_var, lag):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_delay_data(p_sets, agent, var, t_var, lag)
        
        if master_df.empty:
            plt.close(fig)
            return None

        for p_set in p_sets:
            df = master_df[master_df['parameter_set'] == p_set]
            if not df.empty:
                ax.plot(df['lagged_val'], df['current_val'], alpha=0.7, label=f"{p_set} (Lag={lag})")
                if len(df) > 1:
                    ax.annotate('', xy=(df['current_val'].iloc[-1], df['lagged_val'].iloc[-1]),
                                xytext=(df['current_val'].iloc[-2], df['lagged_val'].iloc[-2]),
                                arrowprops=dict(arrowstyle="->", color="red", lw=2))
                                
        ax.set_title(f"Delay Phase Portrait: Mean {var} ($X_{{t}}$ vs $X_{{t-{lag}}}$)")
        ax.set_xlabel(f"Historical Value ($X_{{t-{lag}}}$)")
        ax.set_ylabel(f"Current Value ($X_{{t}}$)")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

def load_config(config_path):
    if not os.path.exists(config_path):
        print(f"[FATAL ERROR] Configuration file missing at: '{config_path}'")
        sys.exit(1)
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[FATAL ERROR] Malformed JSON file syntax in '{config_path}':\nReason: {e}")
        sys.exit(1)

def _resolve_iterations(target_val):
    if isinstance(target_val, dict):
        try:
            start = target_val["start"]
            stop = target_val["stop"]
            step = target_val["step"]
            return list(range(start, stop + step, step))
        except KeyError as e:
            print(f"[FATAL ERROR] Malformed config: The range object under 'target_iteration' is missing required key: {e}")
            sys.exit(1)
    elif isinstance(target_val, int):
        return [target_val]
    else:
        print("[FATAL ERROR] Malformed config: 'target_iteration' must be either a single integer or a complete range object dictionary.")
        sys.exit(1)

# ================================================================================
# Main Execution Entry Pipeline
# ================================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FLAViz Multi-Format Unified Pattern-Matching Plot Suite.")
    parser.add_argument('-i', '--input', required=True, help="Path to directory containing unified metric files.")
    parser.add_argument('-c', '--config', default="./config.json", help="Path to json configurations setup.")
    parser.add_argument('-o', '--output-dir', default=None, help="Output target directory folder.")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[FATAL ERROR] Input directory absent: {args.input}")
        sys.exit(1)

    cfg = load_config(args.config)
    
    try:
        p_sets = cfg["comparison_sets"]
        t_var = cfg["time_variable"]
        plots = cfg["plots"]
    except KeyError as e:
        print(f"[FATAL ERROR] Global configuration block is missing required parameter: {e}")
        sys.exit(1)

    engine = UnifiedFlavizEngine(args.input)
    total_exported = 0

    for idx, p in enumerate(plots, start=1):
        try:
            style = p["plot_style"]
            agent = p["agent_type"]
            var = p["variable_name"]
            fname = p["output_filename"]
        except KeyError as e:
            print(f"[FATAL ERROR] Plot block index {idx} is missing a required parameter: {e}")
            sys.exit(1)
        
        if style in ["box_plot", "histogram", "scatter_plot"]:
            if "target_iteration" not in p:
                print(f"[FATAL ERROR] Plot block index {idx} ('{style}') must declare a 'target_iteration'.")
                sys.exit(1)
            iterations = _resolve_iterations(p["target_iteration"])
        else:
            iterations = [0] 

        if style == "scatter_plot" and "secondary_variable" not in p:
            print(f"[FATAL ERROR] Plot block index {idx} ('scatter_plot') must declare a 'secondary_variable'.")
            sys.exit(1)

        if style == "delay_plot" and "delay_lag" not in p:
            print(f"[FATAL ERROR] Plot block index {idx} ('delay_plot') must declare a 'delay_lag'.")
            sys.exit(1)

        print(f"[{idx}/{len(plots)}] Constructing superimposed '{style}' layout for {agent} ({var})...")
        fig = None

        if style == "time_series":
            fig = engine.plot_time_series(p_sets, agent, var, t_var)
        elif style == "box_plot":
            fig = engine.plot_box_plot(p_sets, agent, var, t_var, iterations)
        elif style == "histogram":
            fig = engine.plot_histogram(p_sets, agent, var, t_var, iterations)
        elif style == "scatter_plot":
            fig = engine.plot_scatter(p_sets, agent, var, p["secondary_variable"], t_var, iterations)
        elif style == "delay_plot":
            fig = engine.plot_delay(p_sets, agent, var, t_var, p["delay_lag"])

        if fig:
            dest = os.path.join(args.output_dir, fname) if args.output_dir else fname
            dest_dir = os.path.dirname(os.path.abspath(dest))
            if not os.path.exists(dest_dir): os.makedirs(dest_dir)
            fig.savefig(dest, dpi=300)
            plt.close(fig)
            total_exported += 1
            print(f"  -> Exported Strict Superimposed Figure: {dest}")
        else:
            print(f"  [Warning] No records matched data thresholds for plot block index {idx}.")
            
    print(f"\nBatch processing completed. Total figures strictly exported: {total_exported}")