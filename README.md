
## Main goal
The main goal of this project is to re-engineer the FLAViz FLAME vizualization library to use Apache Arrow and Parquet columnar storage formats.
A third element is to use duckDB to use SQL-like query statements to perform ETL processes.

AI proposed this summary (which is longer):

The primary objective of this project is to re-engineer the data backend of the FLAME simulation environment and its companion visualization tool, FLAViz, to utilize Apache Arrow and Parquet columnar storage formats. A secondary milestone integrates DuckDB to execute high-speed, SQL-driven ETL (Extract, Transform, Load) operations directly on the generated dataset, optimizing the data pipeline for real-time visualization and analytics.

## Problem addressed
While the FLAME simulation community knew XML output was a bottleneck and experimented with HDF5 or raw binary matrix arrays, in this project we want to integrate an Apache Arrow + Parquet + DuckDB data pipeline. This architecture brings three distinct innovations to the FLAME ecosystem:

* **In-Memory Zero-Copy Alignment**: By linking libarrow and libparquet into xparser.c, we are creating direct binary streams straight out of the xmachine memory space into a structured columnar file.

* **The DuckDB Serverless Advantage**: Prior big-data attempts in agent-based modeling often required setting up a heavy external database cluster (like MySQL or NoSQL/MongoDB) to query the simulation data. Our use of DuckDB allows a researcher to open a terminal, point a local python script at a directory of .parquet files, and instantly run complex relational SQL queries without any server overhead.

* **Modernized ETL for FLAViz**: Instead of forcing FLAViz to read massive, un-indexed files row-by-row, DuckDB acts as an ultra-fast data processor that filters and downsamples the data before handing it to FLAViz, solving the rendering lag inherent in large multi-agent plots.

## Main changes to data pipeline architecture

  1. **The core switch in FLAME data output (from XML to Parquet)**: It establishes that you are moving from high-overhead serialization (XML) to compressed, high-performance columnar files (.parquet).

  2. **The memory layer (Apache Arrow)**: It highlights that data isn't just fast on disk, but efficiently structured in-memory for the visualization tool.

  3. **The data analytics engine (DuckDB)**: It leverages DuckDB's exact strength—acting as an embedded vectorization engine that runs incredibly fast SQL queries directly on top of Parquet files without needing to spin up a heavy database server.

## Component diagram

The project can be visualized by this component diagram:

```
+--------------------------------------------------+
|               FLAME Core Engine                  |
|  (C-Based State Machine Execution Environment)   |
+----------------------------------------+---------+
                     |
Hook Invocation      v
+--------------------------------------------------+
|          High-Performance Data Backend           |
|   (C++ / Apache Arrow / Columnar Parquet API)    |
+----------------------------------------+---------+
                     |
High-Speed Disk I/O  v
+--------------------------------------------------+
|           FLAViz Visualization Layer             |
|   (Dynamic Agent Tracking, Ingestion & Rendering) |
+--------------------------------------------------+
```

## 🗺️ Project Roadmap

### Phase 1: FLAViz Visualization Layer
* **Ingestion Tuning:** Configure rendering pipelines to directly consume simulation outputs over time.
* **Agent Attribute Mapping:** Establish geometric mappings and state tracking protocols to dynamically update agent visual properties across time ticks.
* **Temporal Tracking:** Synchronize multi-agent coordinates and state differentials inside the rendering engine.

### Phase 2: High-Performance Data Backend (Apache Arrow / Parquet)
* **Storage Optimization:** Transition the data layer from unstructured, repetitive XML files to compressed, self-describing columnar Parquet files.
* **Dependency Binding:** Resolve environment-specific C/C++ linker directives (`-larrow`, `-lparquet`) to bridge system development libraries with the code generator templates.
* **Target Isolation:** Account for underlying distribution layers when deploying to specific derivatives like Linux Mint.

### Phase 3: Core Engine Integration (`xparser`)
* **AST Template Modification:** Augment framework templates (`main.tmpl`, `header.tmpl`, `parquet.cpp.tmpl`) to inject binary file emission logic directly into the simulation loop lifecycle.
* **Grammar Alignment:** Reconcile template block loops with the customized text tokenization rules of your specialized `xparser.c`.
* **Compilation Pipeline Updates:** Modernize object dependency graphs inside the template Makefiles to link isolated compilation outputs securely.

---

## ⚙️ Installation & Dependency Setup

### 1. Host System Requirements
Because the official Apache Arrow binaries are hosted on decentralized Artifactory servers, automated dependency retrieval scripts on systems such as Linux Mint 22 (`zena`) must be explicitly forced to target the appropriate foundational distribution layer.

### 2. Package Registration & Installation
Execute the following clean sequence to register the official secure repository and deploy the development toolkits for Arrow and Parquet:

```bash
# Remove previous broken deployment attempts
rm -f apache-arrow-apt-source-latest-*.deb

# Retrieve the configuration package explicitly mapped to the Ubuntu 24.04 (noble) base
wget [https://packages.apache.org/artifactory/arrow/ubuntu/apache-arrow-apt-source-latest-noble.deb](https://packages.apache.org/artifactory/arrow/ubuntu/apache-arrow-apt-source-latest-noble.deb)

# Install the configuration package to map keys and repository records
sudo apt-get install -y ./apache-arrow-apt-source-latest-noble.deb

# Force an index refresh and pull down the development definitions
sudo apt-get update
sudo apt-get install -y libarrow-dev libparquet-dev

# Cleanup the installation artifact
rm apache-arrow-apt-source-latest-noble.deb´´´

# Verify System Path Linkage
# Confirm the host compiler and linker flags are recognized by querying the package configuration definitions:

pkg-config --cflags --libs arrow parquet
```
