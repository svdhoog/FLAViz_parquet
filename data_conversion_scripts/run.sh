#!/bin/bash

# Usage:
# python sql_to_parquet.py --input ./legacy_sql_runs --output ./parquet_output --sets 1-513 --runs 1-1000

# Circles test model
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/test_data/input/sql'
#OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/test_data/output/pqt'

# ABM small
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql'
#OUTPUT_FILE='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/output/pqt'

# ABM large
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql_multiple_sets_runs_200MB/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/sql'
#OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql_multiple_sets_runs_200MB/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/pqt'

# ABM Calibration Sets 1-256
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAME-HPC/xparser@svdhoog/sandbox_parquet_integration/test_data/flat/calibration-mode-3-stage-1-sets-1-256-tarballs-part-1'
#OUTPUT_FILE='/home/sander/Documents/GIT/GitHub/FLAME-HPC/xparser@svdhoog/sandbox_parquet_integration/test_data/flat/calibration-mode-3-stage-1-sets-1-256-tarballs-part-1/pqt'

# ABM Calibration Sets 257-513
INPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/db'
OUTPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/pqt'

echo "Data conversion from: $INPUT_DIR, writing Parquet files to: $OUTPUT_FILE"
# Use --force: when you want to overwrite already processed files. This can be useful if the previous process halted unexpectedly.

# Test small:
#python sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --sets 1-2 --runs 1-2 #--force

# Test medium:
python sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --sets 1-1 --runs 1-1000 #--force

# Full:
#python sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --sets 1-513 --runs 1-1000 #--force
