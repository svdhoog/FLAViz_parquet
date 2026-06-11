#!/usr/bin/env python3
"""
================================================================================
FLAViz-Engine: Multi-Agent Superimposed Plotting Suite (New Schema Compatible)
================================================================================
Description:
    Implements core plotting routines over unified high-level datasets generated
    by the ETL pipeline script. 
    
    Dynamically identifies data tables via regex pattern matching over agent class
    filenames (e.g. checkpoint_Household.parquet), extracting requested 
    attributes on demand.

Design Rules & Features:
    - Superimposes multiple set configurations into single visualization panels.
    - Completely handles variable isolation, filtering, and cross-variable checks.
    - Operates efficiently on primitive data shapes using optimized DuckDB views.
    - Enforces absolute strictness: missing JSON parameters halt operation instantly.
    - Ranges defined for 'target_iteration' are treated as fully inclusive.

Usage:
    $ python flaviz_parquet_plot.py -i /path/to/unified -c ./config.json
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

class UnifiedSchemaPlotEngine:
    def __init__(self, data_root_dir):
        """Initializes the engine over unified checkpoints via serverless DuckDB driver."""
        self.root_dir = os.path.abspath(data_root_dir)
        self.conn = duckdb.connect()
        if os.path.isdir(self.root_dir):
            self.available_files = os.listdir(self.root_dir)
        else:
            self.available_files = []

    def _resolve_agent_file(self, agent_type):
        """
        Runs pattern matching over file strings to isolate tables without hard-coding rules.
        """
        pattern = re.compile(rf"(?:^|[^a-zA-Z0-9]){re.escape(agent_type)}(?:^|[^a-zA-Z0-9])")
        matched = []

        for f in self.available_files:
            name, ext = os.path.splitext(f)
            if ext.lower() in ['.parquet', '.feather']:
                if pattern.search(name):
                    matched.append(f)

        if not matched:
            print(f"[FATAL ERROR] No unified checkpoint file found matching agent class type: '{agent_type}'")
            print(f"              Folder scanned: {self.root_dir}")
            sys.exit(1)
        elif len(matched) > 1:
            print(f"[FATAL ERROR] Ambiguous match. Multiple checkpoints correlate to agent type '{agent_type}': {matched}")
            sys.exit(1)

        return os.path.join(self.root_dir, matched[0])

    # --------------------------------------------------------------------------
    # CORE QUANTITATIVE AGGREGATORS (NEW SCHEMA LAYOUT COMPATIBLE)
    # --------------------------------------------------------------------------
    def query_time_series(self, sets, agent, var, t_var):
        source = self._resolve_agent_file(agent)
        sets_clause = ", ".join([str(s) for s in sets])
        
        query = f"""
            SELECT 
                set_num,
                {t_var} as iteration, 
                AVG({var}) as mean_val, 
                MIN({var}) as min_val, 
                MAX({var}) as max_val
            FROM '{source}'
            WHERE set_num IN ({sets_clause})
            GROUP BY set_num, {t_var} 
            ORDER BY set_num, {t_var}
        """
        return self.conn.execute(query).df()

    def query_snapshot_data(self, sets, agent, var, t_var, iterations):
        source = self._resolve_agent_file(agent)
        sets_clause = ", ".join([str(s) for s in sets])
        iter_clause = ", ".join([str(i) for i in iterations])
        
        query = f"""
            SELECT 
                set_num,
                {t_var} as iteration,
                {var} as target_value 
            FROM '{source}' 
            WHERE set_num IN ({sets_clause})
              AND {t_var} IN ({iter_clause})
        """
        return self.conn.execute(query).df()

    def query_scatter_data(self, sets, agent, var_x, var_y, t_var, iterations):
        source = self._resolve_agent_file(agent)
        sets_clause = ", ".join([str(s) for s in sets])
        iter_clause = ", ".join([str(i) for i in iterations])
        
        # New schema holds multiple attributes inside the same table, eliminating heavy inner joins
        query = f"""
            SELECT 
                set_num,
                {t_var} as iteration,
                {var_x} as x_val, 
                {var_y} as y_val 
            FROM '{source}'
            WHERE set_num IN ({sets_clause})
              AND {t_var} IN ({iter_clause})
        """
        return self.conn.execute(query).df()

    def query_delay_data(self, sets, agent, var, t_var, lag):
        source = self._resolve_agent_file(agent)
        sets_clause = ", ".join([str(s) for s in sets])
        
        query = f"""
            WITH aggregated AS (
                SELECT 
                    set_num,
                    {t_var} as iteration, 
                    AVG({var}) as avg_val 
                FROM '{source}' 
                WHERE set_num IN ({sets_clause})
                GROUP BY set_num, {t_var}
            )
            SELECT 
                set_num,
                avg_val as current_val, 
                LAG(avg_val, {lag}) OVER (PARTITION BY set_num ORDER BY iteration) as lagged_val
            FROM aggregated
        """
        return self.conn.execute(query).df().dropna()

    # --------------------------------------------------------------------------
    # VISUALIZATION RENDERING SUITE
    # --------------------------------------------------------------------------
    def plot_time_series(self, sets, agent, var, t_var):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_time_series(sets, agent, var, t_var)
        if master_df.empty:
            plt.close(fig)
            return None

        for s in sets:
            df = master_df[master_df['set_num'] == s]
            if df.empty: continue
            line, = ax.plot(df['iteration'], df['mean_val'], label=f"Set {s} Mean", lw=2)
            ax.fill_between(df['iteration'], df['min_val'], df['max_val'], alpha=0.15, color=line.get_color())
            
        ax.set_title(f"Temporal Trend Analysis of {var} ({agent})")
        ax.set_xlabel("Time Step Tracking Vector")
        ax.set_ylabel(var)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

    def plot_box_plot(self, sets, agent, var, t_var, iterations):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_snapshot_data(sets, agent, var, t_var, iterations)
        if master_df.empty:
            plt.close(fig)
            return None

        plot_data, labels = [], []
        for it in iterations:
            for s in sets:
                sub = master_df[(master_df['set_num'] == s) & (master_df['iteration'] == it)]
                if not sub.empty:
                    plot_data.append(sub['target_value'].values)
                    labels.append(f"Set {s}\n(Step {it})")
                    
        if not plot_data:
            plt.close(fig)
            return None
            
        ax.boxplot(plot_data, labels=labels, patch_artist=True, boxprops=dict(facecolor='wheat', color='orange'))
        ax.set_title(f"Cross-Sectional Distribution Profile: {var}")
        ax.set_ylabel(var)
        ax.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        return fig

    def plot_histogram(self, sets, agent, var, t_var, iterations):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_snapshot_data(sets, agent, var, t_var, iterations)
        if master_df.empty:
            plt.close(fig)
            return None
        
        for it in iterations:
            for s in sets:
                sub = master_df[(master_df['set_num'] == s) & (master_df['iteration'] == it)]
                if not sub.empty:
                    ax.hist(sub['target_value'], bins=30, alpha=0.4, label=f"Set {s} (Step {it})", edgecolor='black')
                    
        ax.set_title(f"Superimposed Frequency Matrix: {var} Variables")
        ax.set_xlabel(var)
        ax.set_ylabel("Observation Count Density")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

    def plot_scatter(self, sets, agent, var, sec_var, t_var, iterations):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_scatter_data(sets, agent, var, sec_var, t_var, iterations)
        if master_df.empty:
            plt.close(fig)
            return None
        
        for it in iterations:
            for s in sets:
                sub = master_df[(master_df['set_num'] == s) & (master_df['iteration'] == it)]
                if not sub.empty:
                    ax.scatter(sub['x_val'], sub['y_val'], alpha=0.5, label=f"Set {s} (Step {it})", s=25)
                    
        ax.set_title(f"Stochastic Phase Space Correlation: {var} vs {sec_var}")
        ax.set_xlabel(var)
        ax.set_ylabel(sec_var)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

    def plot_delay(self, sets, agent, var, t_var, lag):
        fig, ax = plt.subplots(figsize=(10, 6))
        master_df = self.query_delay_data(sets, agent, var, t_var, lag)
        if master_df.empty:
            plt.close(fig)
            return None

        for s in sets:
            df = master_df[master_df['set_num'] == s]
            if not df.empty:
                ax.plot(df['lagged_val'], df['current_val'], alpha=0.7, label=f"Set {s} Continuum (Lag={lag})")
                if len(df) > 1:
                    ax.annotate('', xy=(df['current_val'].iloc[-1], df['lagged_val'].iloc[-1]),
                                xytext=(df['current_val'].iloc[-2], df['lagged_val'].iloc[-2]),
                                arrowprops=dict(arrowstyle="->", color="black", lw=1.5))
                                
        ax.set_title(f"Delay Attractor Profile: Mean {var} ($X_{{t}}$ vs $X_{{t-{lag}}}$)")
        ax.set_xlabel(f"Historical Phase ($X_{{t-{lag}}}$)")
        ax.set_ylabel(f"Current State ($X_{{t}}$)")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return fig

def load_config(config_path):
    if not os.path.exists(config_path):
        print(f"[FATAL ERROR] Visualization configuration configuration target missing: '{config_path}'")
        sys.exit(1)
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[FATAL ERROR] Broken JSON syntax inside configuration layout: {e}")
        sys.exit(1)

def _resolve_iterations(target_val):
    if isinstance(target_val, dict):
        try:
            start, stop, step = target_val["start"], target_val["stop"], target_val["step"]
            return list(range(start, stop + step, step))
        except KeyError as e:
            print(f"[FATAL ERROR] Range dictionary definition requires missing element: {e}")
            sys.exit(1)
    elif isinstance(target_val, int):
        return [target_val]
    else:
        print("[FATAL ERROR] 'target_iteration' parameter format validation failed.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FLAViz Production Plotting Utility Engine Instance.")
    parser.add_argument('-i', '--input', required=True, help="Folder location hosting optimized unified checkpoints.")
    parser.add_argument('-c', '--config', default="./config.json", help="Path location mapping configuration bounds.")
    parser.add_argument('-o', '--output-dir', default=None, help="Output folder to dump generated PNG files.")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[FATAL ERROR] Unified checkpoints root path does not exist: {args.input}")
        sys.exit(1)

    cfg = load_config(args.config)
    
    try:
        # Configuration matches integers parsed during optimized ETL execution
        sets = [int(x) for x in cfg["comparison_sets"]]
        t_var = cfg["time_variable"]
        plots = cfg["plots"]
    except KeyError as e:
        print(f"[FATAL ERROR] Global config properties missing parameter: {e}")
        sys.exit(1)

    engine = UnifiedSchemaPlotEngine(args.input)
    total_exported = 0

    for idx, p in enumerate(plots, start=1):
        try:
            style = p["plot_style"]
            agent = p["agent_type"]
            var = p["variable_name"]
            fname = p["output_filename"]
        except KeyError as e:
            print(f"[FATAL ERROR] Plot specifications at block {idx} lacks component parameter: {e}")
            sys.exit(1)
        
        if style in ["box_plot", "histogram", "scatter_plot"]:
            if "target_iteration" not in p:
                print(f"[FATAL ERROR] Plot block index {idx} ('{style}') must declare a 'target_iteration'.")
                sys.exit(1)
            iterations = _resolve_iterations(p["target_iteration"])
        else:
            iterations = [0]

        if style == "scatter_plot" and "secondary_variable" not in p:
            print(f"[FATAL ERROR] Plot index {idx} ('scatter_plot') must include a 'secondary_variable'.")
            sys.exit(1)

        if style == "delay_plot" and "delay_lag" not in p:
            print(f"[FATAL ERROR] Plot index {idx} ('delay_plot') must include a 'delay_lag'.")
            sys.exit(1)

        print(f"[{idx}/{len(plots)}] Building superimposed layout view '{style}' for '{agent}' class...")
        fig = None

        if style == "time_series":
            fig = engine.plot_time_series(sets, agent, var, t_var)
        elif style == "box_plot":
            fig = engine.plot_box_plot(sets, agent, var, t_var, iterations)
        elif style == "histogram":
            fig = engine.plot_histogram(sets, agent, var, t_var, iterations)
        elif style == "scatter_plot":
            fig = engine.plot_scatter(sets, agent, var, p["secondary_variable"], t_var, iterations)
        elif style == "delay_plot":
            fig = engine.plot_delay(sets, agent, var, t_var, p["delay_lag"])

        if fig:
            dest = os.path.join(args.output_dir, fname) if args.output_dir else fname
            dest_dir = os.path.dirname(os.path.abspath(dest))
            if not os.path.exists(dest_dir): 
                os.makedirs(dest_dir)
            fig.savefig(dest, dpi=300)
            plt.close(fig)
            total_exported += 1
            print(f"  -> Saved Superimposed Panel Figure: {dest}")
        else:
            print(f"  [Warning] Zero matching values fell inside specified constraints for index block {idx}.")
            
    print(f"\nExecution sequence terminated. Total figures written to disk: {total_exported}")