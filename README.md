
## Main goal
The main goal of this project is to re-engineer the FLAViz FLAME vizualization library to use Apache Arrow and Parquet data files.
A third element is to use duckDB to use SQL-like query statements to perform ETL processes.

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
