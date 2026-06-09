# Global Sensitivity Analysis (GSA) & Isolated Bifurcation Engine

## DESIGN DECISIONS & ARCHITECTURAL EVOLUTION:

1. **[Shift to Bifurcation Mapping]**: Preserves every individual stochastic run against the parameter continuum to uncover phase transitions.

2. **[I/O Optimization via Stride Filters]**: Loads only N-th simulation steps natively at the worker stage to drop data footprints by 80%+.

3. **[Strict Worker Scaling Strategy]**: Throttles concurrency to maintain stable memory footprints under high data-load volumes.

4. **[Percentile Clipping]**: Integrates a `--percentile` threshold filter to truncate extreme stochastic outliers (e.g., 1e285) that would otherwise obfuscate bifurcation attractors.

5. **[Integer Key Optimization]**: Replaces high-overhead string tracking IDs ('set_id') with primitive 16-bit integers ('set_num') inside both Parquet and Feather file schemas. This eliminates multi-gigabyte string object bloat.

6. **[Direct Arrow Zero-Copy Plotting]**: Bypasses Pandas DataFrames and relational merge lookups entirely during plotting. Memory-mapped PyArrow tables supply data vectors directly to Matplotlib using fast, zero-copy NumPy views.

7. **[Single-Precision Downcasting]**: Enforces float32 downcasting across all floating-point analytical columns to instantly half computational memory layouts.

8. **[Two-Pass Streaming Plotting]**: Eliminates monolithic table materialization by decoupling percentile threshold calculation (via sampling) from rendering.

9. **[Streaming Histogram Accumulation]**: Updates a static 500x500 grid buffer batch-by-batch. This architecture decouples memory usage from dataset size, ensuring that RAM usage remains flat regardless of whether the dataset is 1 GB or 100 GB.
