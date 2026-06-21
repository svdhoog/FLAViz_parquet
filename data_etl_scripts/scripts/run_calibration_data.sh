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

# ABM small, sets 4-5 runs 1-2
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/test_data/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/pqt'
#OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/test_data/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/etl_output'

# Estimation_and_Calibration_Data
INPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/pqt'
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/calibration_data/etl_output'

# Usage:
python ../unified_etl.py \
  --sets 1-1 \
  --runs 1-1 \
  --agent-types "Eurostat" \
  --input "$INPUT_DIR" \
  --output "$OUTPUT_DIR" \
  --workers 2 \
  --verbose
#  --sets 1-513 \
#  --runs 1-1000 \
#  --agent-types "Bank, Firm"