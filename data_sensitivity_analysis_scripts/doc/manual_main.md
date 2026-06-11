# User Manual: Global Sensitivity Analysis Engine

# Architectural Summary: The GSA Data Transformation and ETL Process

## 1. Overview of the Data Architecture
The current data transformation process represents a specialized **Two-Pass Streaming Extract, Transform, Load (ETL)** pipeline. It bridges the gap between two opposing computational needs:
1. **Simulation Generation (High Parallelism, Low Coordination)**: Maximizing raw computing power across multiple nodes without file locking or write bottlenecks.
2. **Global Sensitivity Analysis (High Aggregation, Columnar Access)**: Streaming millions of records across hundreds of parameter continuum sets to construct isolated bifurcation maps and time series plots.

---

## 2. The Current Granular Storage Layout
The raw simulation data is organized within a highly nested directory hierarchy on disk:

```text
root_dir/
└── set_n/
    └── run_m/
        └── data_Eurostat.parquet
```
### Key Analytical Insights from Inspection:

    Uniform Time Steps: Each data_Eurostat.parquet file captures exactly 1,000 discrete ticks (mapped from simulation timeline iterations 6020 to 26000).

    Variable Run Densities: The stochastic engine generates an asymmetrical number of Monte Carlo seeds per parameter configuration (e.g., set_1 completes 1001 runs, set_10 completes 969 runs, and set_103 completes 983 runs).

## 3. Core Reasons for Rejecting a Single Monolithic File Format

While it is technically possible to combine all variables, agent types, parameter sets, and runs into a single massive file format (such as an enormous multi-terabyte Parquet dataset, HDF5 hierarchy, or Zarr array store), doing so introduces severe architectural bottlenecks:

### A. The Multi-Dimensional Sparsity Problem

Because the number of runs varies across parameter sets (e.g., 1001 vs. 969), forcing the data into a strict dense tensor format (like HDF5 or NetCDF) would require empty runs to be padded with arbitrary values (e.g., NaN or 0). This practice introduces significant metadata bloat and wastes large blocks of storage.

### B. Analytical Access Patterns and Columnar I/O

When calculating a bifurcation map or a global sensitivity index, the analytical access pattern is highly exclusive: the system reads exactly one economic variable across all parameter sets simultaneously. Packing all metrics and agent types into a single monolithic file means that to analyze a single variable (e.g., unemployment_rate), the processing engine would still have to parse or step past the storage blocks containing all other unreferenced data tables.

### C. OS Memory Saturation Boundaries

Under high workloads, the data streams push systems directly against physical memory constraints (e.g., a 16 GB RAM boundary). Reading from one giant file format requires the underlying layout libraries to hold file maps, compression page dictionaries, and global indices in active memory. For multi-terabyte datasets, this tracking metadata alone can trigger Out-Of-Memory (OOM) failures before raw rows are even processed.

### D. Write Independence and Fault Tolerance

    No File Contention: During execution, independent worker nodes write their small data_Eurostat.parquet files simultaneously without competing for file locks or requiring a central coordinating system.

    Granular Fault Tolerance: If a worker node suffers a hardware fault at step 900, only that isolated set_n/run_m directory is corrupted. In contrast, an ungraceful termination or fault during parallel writes to a single monolithic file risks corrupting the entire database.

## 4. The Two-Pass Reorganization Mechanism

To resolve these limitations, the Global Sensitivity Analysis script converts the low-granularity distributed files into an optimized high-granularity format tailored for downstream calculations:

[Simulation Stage]                  [ETL Ingestion Pass]                 [Target Analytical Layout]
Low-Granularity Files       ───►    Streaming Multi-Process      ───►    High-Granularity Checkpoints
(All economic variables             Ingestion (Downcasts data,           (Isolates data into flat, single-
grouped per single run folder)      tracks run/time metadata)            variable streams across ALL sets)

### Structural Transformation:

    * Pass 1 (Ingestion & Re-indexing): The script streams rows from the scattered folders, downcasts floating-point columns to single-precision (float32), and appends memory-efficient 16-bit integers (int16) to explicitly track set_num, run_num, and time_step.

    * Pass 2 (Zero-Copy Plotting): The reorganized checkpoint files allow the script to slice data for an isolated metric instantaneously using fast memory maps, bypassing heavy Pandas dataframes and streaming rows in controlled, predictable blocks (e.g., 50,000 records per iteration) to guarantee a flat RAM profile.
