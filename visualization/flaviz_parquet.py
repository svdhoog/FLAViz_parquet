#!/usr/bin/env python3
"""
================================================================================
FLAViz-Engine: Superimposed Multi-Iteration Plotting Suite (Strict & Inclusive)
================================================================================
Description:
    Implements native FLAViz core plotting routines over a Parquet dataset.
    Automatically superimposes multiple iteration values onto a single chart
    axis when a JSON range object is provided for 'target_iteration'.

    Enforces strict validation: any missing parameters in a range definition
    or plot configuration will halt execution immediately.
    
    Treats the range 'stop' parameter as fully inclusive.

Dependencies:
    $ pip install duckdb pandas matplotlib numpy
================================================================================
"""

import os
import sys
import json
import argparse
import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class ParquetFlavizEngine:
    def __init__(self, parquet_root_dir):
        """Initializes the engine using an active serverless DuckDB driver."""
        self.root_dir = os.path.abspath(parquet_root_dir)
        self.conn = duckdb.connect()

    def _get_path(self, parameter_set, agent_type):
        return os.path.join(self.root_dir, parameter_set, "*", f"data_{agent_type}.parquet")

    # --------------------------------------------------------------------------
    # DATA EXTRACTION AGGREGATORS
    # --------------------------------------------------------------------------
    def query_time_series(self, p_set, agent, var, t_var):
        query = f"""
            SELECT {t_var} as iteration, AVG({var}) as mean_val, MIN({var}) as min_val, MAX({var}) as max_val
            FROM '{self._get_path(p_set, agent)}' GROUP BY {t_var} ORDER BY {t_var}
        """
        return self.conn.execute(query).df()

    def query_snapshot_data(self, p_set, agent, var, t_var, iteration):
        query = f"""
            SELECT {var} as target_value FROM '{self._get_path(p_set, agent)}' WHERE {t_var} = {iteration}
        """
        return self.conn.execute(query).df()

    def query_scatter_data(self, p_set, agent, var_x, var_y, t_var, iteration):
        query = f"""
            SELECT {var_x} as x_val, {var_y} as y_val FROM '{self._get_path(p_set, agent)}' WHERE {t_var} = {iteration}
        """
        return self.conn.execute(query).df()

    def query_delay_data(self, p_set, agent, var, t_var, lag):
        query = f"""
            WITH aggregated AS (
                SELECT {t_var} as iteration, AVG({var}) as avg_val 
                FROM '{self._get_path(p_set, agent)}' GROUP BY {t_var}
            )
            SELECT avg_val as current_val, LAG(avg_val, {lag}) OVER (ORDER BY iteration) as lagged_val
            FROM aggregated
        """
        df = self.conn.execute(query).df()
        return df.dropna()

    # --------------------------------------------------------------------------
    # VISUALIZATION GRAPHICS ENGINES (SUPERIMPOSED)
    # --------------------------------------------------------------------------
    def plot_time_series(self, p_sets, agent, var, t_var):
        fig, ax = plt.subplots(figsize=(10, 6))
        for p_set in p_sets:
            df = self.query_time_series(p_set, agent, var, t_var)
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
        plot_data = []
        labels = []
        
        for iteration in iterations:
            for p_set in p_sets:
                df = self.query_snapshot_data(p_set, agent, var, t_var, iteration)
                if not df.empty:
                    plot_data.append(df['target_value'].values)
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
        data_found = False
        
        for iteration in iterations:
            for p_set in p_sets:
                df = self.query_snapshot_data(p_set, agent, var, t_var, iteration)
                if not df.empty:
                    data_found = True
                    ax.hist(df['target_value'], bins=30, alpha=0.4, label=f"{p_set} (Iter {iteration})", edgecolor='black')
                    
        if not data_found:
            plt.close(fig)
            return None
            
        ax.set_title(f"Superimposed Frequency Distribution of {var} ({agent} Agents)")
        ax.set_xlabel(var)
        ax.set_ylabel("Frequency Count")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

    def plot_scatter(self, p_sets, agent, var, sec_var, t_var, iterations):
        fig, ax = plt.subplots(figsize=(10, 6))
        data_found = False
        
        for iteration in iterations:
            for p_set in p_sets:
                df = self.query_scatter_data(p_set, agent, var, sec_var, t_var, iteration)
                if not df.empty:
                    data_found = True
                    ax.scatter(df['x_val'], df['y_val'], alpha=0.5, label=f"{p_set} (Iter {iteration})", s=20)
                    
        if not data_found:
            plt.close(fig)
            return None
            
        ax.set_title(f"Superimposed Phase Scatter: {var} vs {sec_var}")
        ax.set_xlabel(var)
        ax.set_ylabel(sec_var)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

    def plot_delay(self, p_sets, agent, var, t_var, lag):
        fig, ax = plt.subplots(figsize=(10, 6))
        for p_set in p_sets:
            df = self.query_delay_data(p_set, agent, var, t_var, lag)
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
    """
    Parses the target_iteration property from the configuration file.
    Enforces strict key presence and treats the 'stop' boundary as fully inclusive.
    """
    if isinstance(target_val, dict):
        try:
            start = target_val["start"]
            stop = target_val["stop"]
            step = target_val["step"]
            
            # stop + step makes the range execution boundary mathematically inclusive
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
    parser = argparse.ArgumentParser(description="FLAViz Parquet Batch Plot Processing Suite.")
    parser.add_argument('-i', '--input', required=True, help="Path to Parquet output mirror.")
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

    engine = ParquetFlavizEngine(args.input)
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
        
        # Enforce that snapshot styles must declare a target_iteration
        if style in ["box_plot", "histogram", "scatter_plot"]:
            if "target_iteration" not in p:
                print(f"[FATAL ERROR] Plot block index {idx} ('{style}') must declare a 'target_iteration'.")
                sys.exit(1)
            iterations = _resolve_iterations(p["target_iteration"])
        else:
            iterations = [0] 

        # Enforce that scatter_plot must declare its secondary variable axis
        if style == "scatter_plot" and "secondary_variable" not in p:
            print(f"[FATAL ERROR] Plot block index {idx} ('scatter_plot') must declare a 'secondary_variable'.")
            sys.exit(1)

        # Enforce that delay_plot must declare its delay lag value
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
    