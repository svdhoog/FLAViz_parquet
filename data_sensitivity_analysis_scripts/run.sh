#!/bin/bash


INPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/pqt'
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAME-HPC/xparser@svdhoog/sandbox_parquet_integration/test_models/ABM/calibration_data/output'
#OUTPUT_FILE='gsa_summary.txt'

SAMPLE_DIR='/home/sander/Documents/GIT/GitHub/FLAME-HPC/xparser@svdhoog/sandbox_parquet_integration/test_models/ABM/calibration_data'
SAMPLE_FILE='sample_513_mode_3.csv'

METRICS="unemployment_rate, monthly_output, price_index, total_debt"
#METRICS="unemployment_rate"

# Usage:
# python global_sensitivity_analysis.py \
#	--input ./parquet_output \
#   --parameters sample_513_mode_3.csv \
#	--table Agent_n \
#	--metric var_names \
#   --output "$OUTPUT_DIR/$OUTPUT_FILE" \
#	--style [color|greyscale|color-and-greyscale] \
#	--sets 1-10 \
#	--runs 1-100 \
#	--workers 4 \
#   --stride 5 \
#   --checkpoint \
#   --format ['feather'|'parquet']

# GSA for all metrics in $METRICS
# Optimized for Memory Stability
time python global_sensitivity_analysis.py \
    --input "$INPUT_DIR" \
    --parameters "$SAMPLE_DIR/$SAMPLE_FILE" \
    --table Eurostat \
    --metric "$METRICS" \
    --output "$OUTPUT_DIR" \
    --style greyscale \
    --sets 1-513 \
    --runs 1-200 \
    --workers 1 \
    --stride 5 \
    --checkpoint \
    --format 'parquet'
