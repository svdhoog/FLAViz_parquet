#!/bin/sh

cat << 'EOF' > manual_checkpoint_storage.md

## Technical Reference: Checkpoint Storage & Lifecycle

When utilizing the on-demand caching engine via the `--checkpoint` flag, the script isolates data tracking environments by metric. This prevents memory degradation and allows fast, decoupled re-runs of the visualization pipeline.

### Directory Structure & Naming Convention

Checkpoint files are stored directly inside **metric-specific subfolders** within your designated output root. The system names files dynamically using the target metric name and your chosen serialization standard extension:

    {output_dir}/{metric}/checkpoint_{metric}.{ext}

* **{output_dir}**: The base destination directory derived from your `--output` path configuration.
* **{metric}**: The sanitized name of the target variable being processed (e.g., `unemployment_rate`).
* **{ext}**: The explicit file standard selected via your command arguments (`feather` or `parquet`).

#### Structural Production Example
When executing the pipeline across multiple metrics with caching enabled, your project's output folder tree automatically organizes itself into the following layout:

    results_dir/
    ├── unemployment_rate/
    │   ├── checkpoint_unemployment_rate.feather  <-- Intermediate Cached Data Block (~369 MB)
    │   ├── bifurcation_unemployment_rate_alpha_color.png
    │   ├── bifurcation_unemployment_rate_beta_color.png
    │   └── ... (isolated single-parameter plots)
    │
    └── inflation/
        ├── checkpoint_inflation.feather          <-- Intermediate Cached Data Block (~369 MB)
        ├── bifurcation_inflation_alpha_color.png
        └── ...

---

### Cache Lifecycle and Cache-Busting

The pipeline enforces strict conditional checks at runtime to determine whether it should hit the filesystem or perform a folder traversal:

1. **Cache Hit:** If `--checkpoint` is passed and a file matching `checkpoint_{metric}.{ext}` is present in the subfolder, the engine completely bypasses the raw, metadata-heavy hierarchical directory scan. It populates your data frames from the single cached binary block in milliseconds.
2. **Cache Miss / Invalidation:** If no checkpoint file exists, or if the `--checkpoint` flag is omitted entirely, the script falls back to crawling the raw source directories to compile the data.

#### How to Force a Fresh Data Reload
The checkpoint files do not automatically detect shifts in your source simulation data folders. If you add new stochastic runs (e.g., expanding from `--runs 1-200` to `--runs 1-500`) or generate fresh data sets, you must manually invalidate the cache. 

To clear the cache and force a complete re-read of your data files, simply delete the checkpoint asset from the metric directory:

    rm results_dir/unemployment_rate/checkpoint_unemployment_rate.feather

#### Table

File sizes for checkpoint files (for 4 metrics) in parquet and feather format.

| Case | Sets & Runs | Parquet | Feather |
| :--- | :--- | :--- | :--- |
| **S** | (sets 1-513, runs 1-200, stride 5) | $\sim 94.6\text{ MB}$ – $103.2\text{ MB}$ | $\sim 177.6\text{ MB}$ |
| **M** | (sets 1-513, runs 1-1000, stride 5) | $\sim 473.0\text{ MB}$ – $516.0\text{ MB}$ | $\sim 888.0\text{ MB}$ |
| **L** | (sets 1-513, runs 1-200, stride 1) | $\sim 473.0\text{ MB}$ – $516.0\text{ MB}$ | $\sim 888.0\text{ MB}$ |
| **XL** | (sets 1-513, runs 1-1000, stride 1) | $\sim 2.37\text{ GB}$ – $2.58\text{ GB}$ | $\sim 4.44\text{ GB}$ |
EOF