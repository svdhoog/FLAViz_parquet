#!/bin/bash

# Usage Examples:
#     # Auto-detect everything
#     python unified_etl.py --input ./data --output ./output --sets 1-100 --runs 1-50 --workers 8 --verbose
    
#     # Filter to specific agents
#     python unified_etl.py --input ./data --output ./output --sets 1-100 --runs 1-50 \
#         --agent-types "Bank,Firm" --workers 8 --verbose
    
#     # Filter to specific metrics with stride downsampling
#     python unified_etl.py --input ./data --output ./output --sets 1-100 --runs 1-50 \
#         --metrics "wealth,revenue,debt" --stride 2 --workers 8 --verbose

# Hierarchy: set_n/run_M/data_Agent.Parquet files
INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/output/pqt'

# Flat data_Agent.Parquet files
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/etl_output/pqt'

# Usage:
python ../unified_etl.py \
  --input "$INPUT_DIR" \
  --output "$OUTPUT_DIR" \
  --sets 1-4 \
  --runs 1-2 \
  --workers 2 \
  --verbose \
  --agent-types "Agent"