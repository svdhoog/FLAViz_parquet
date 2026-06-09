# Feature Overview: Global Sensitivity Analysis Engine

This document provides a technical overview of the architectural optimizations implemented within the Global Sensitivity Analysis (GSA) and Bifurcation engine. These strategies are designed to minimize disk I/O, reduce memory (RAM) utilization, and guarantee absolute protection against Out-of-Memory (OOM) crashes when processing exceptionally large (XL) simulation datasets.

---

## Technical Optimization Strategies

### 1. Low-Memory Iterative Chunk Streaming (`iter_batches`)
The engine completely avoids loading or materializing monolithic data tables in memory during both the ingestion and visualization phases. 
* Data is read off disk sequentially in small, configurable slices (typically 100,000 to 250,000 rows) using PyArrow's `iter_batches()` loop construct.
* This limits active execution space to a strict, flat memory ceiling, regardless of whether the underlying file is megabytes or gigabytes on disk.

### 2. Upstream Stride Subsampling
To reduce down-stream memory allocations and eliminate unnecessary computational overhead, data is filtered at the initial disk read stage.
* The script applies a configurable `--stride` interval step directly during the streaming batch loop using zero-copy NumPy array slicing (`y_raw[::stride]`).
* This eliminates up to 80% or more of raw, redundant intermediate simulation steps before they ever populate intermediate operational lists.

### 3. Primitive Integer Key Mapping
To prevent the multi-gigabyte memory inflation associated with string-based tracking IDs (such as long scenario folder names), the script normalizes indexing categories into memory-efficient formats.
* Variable-length path identifiers are parsed out using regex and mapped directly to 16-bit integer sequences (`np.int16`) via `np.repeat(clean_set_num, len(item['y']))`.
* This replaces heavy, duplicated string object structures with compact, contiguous primitive arrays.

### 4. Single-Precision Floating-Point Downcasting
Analytical measurements often default to 64-bit precision, which unnecessarily doubles memory consumption.
* The script forces numerical measurements to downcast immediately to 32-bit single-precision floats (`pa.float32()` / `np.float32`) during extraction.
* This achieves an immediate, structural 50% memory reduction across all primary analytical data columns.

### 5. High-Fidelity Plotting Downsampling Guardrail
Rendering scatter plots with tens of millions of independent points overtaxes graphical engine canvas memory matrices, leading to immediate thrashing or segmentation faults.
* The scatter rendering path incorporates an immutable ceiling (`MAX_PLOT_POINTS = 5_000_000`) paired with a reproducible, pseudo-random seed generator (`np.random.default_rng(seed=42)`).
* When thresholds are breached, coordinates are downsampled using low-overhead numpy masks prior to canvas exposure, protecting Matplotlib from memory exhaustion.

### 6. 2D Density Histogram Overlays
For ultra-dense dataset representations where traditional scatter plots experience severe point occlusion, the engine leverages a 2D density grid.
* Coordinates are mapped onto a static 500x500 mesh resolution via `ax.hist2d()`, employing `mcolors.LogNorm()` to ensure low-density tracking paths remain visible alongside core attractors.
* Because the canvas overhead is bound by the fixed resolution matrix rather than the individual point count, rendering a billion points requires the exact same visual memory allocation as a few thousand.

### 7. Core Thread Concurrency Affinity
Parallel process tasks can experience execution bottlenecks if worker threads context-switch aggressively across all available system threads.
* The environment initialization locks structural processing parameters (`OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`) to `"1"`.
* This ensures core process allocation remains predictable and keeps CPU pipelines operating at maximum efficiency under sustained multi-worker data transfers.

### 8. Asynchronous Telemetry Logging
Real-time tracking is vital for system monitoring and logging without interrupting critical performance pipelines.
* A detached, low-priority background logging thread (`LiveMemoryProfiler`) profiles the application's physical Resident Set Size (RSS), swap utilization, and global RAM percentages every 2.0 seconds.
* This telemetry data is written asynchronously directly to `gsa_memory_profile.csv` to allow full architectural transparency without blocking execution paths.

### 9. Proactive Canvas and Garbage Collection Hygiene
Memory-mapped files and deep graphical arrays can linger in memory if references are not actively cleared by Python's scoped interpreter.
* Explicit decoupling directives (`batch = None`, `sets = None`, `mask = None`) operate inside loop frames to ensure PyArrow's underlying C++ memory blocks release immediately.
* Furthermore, `plt.clf()`, `plt.close('all')`, and `gc.collect()` execute at the conclusion of every parameter generation loop to dump image arrays before advancing to the next metric.

---
