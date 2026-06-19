#!/bin/bash


INPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/pqt'
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/calibration_data/output'
#OUTPUT_FILE='gsa_summary.txt'

SAMPLE_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/calibration_data'
SAMPLE_FILE='sample_513_mode_3_with_headers.csv'

METRICS=("unemployment_rate" "monthly_output" "price_index" "total_debt")
#METRICS=("monthly_output" "price_index" "total_debt")
#METRICS=("unemployment_rate")

## REFACTORED VERSION (15 June 2026)
# python global_sensitivity_analysis.py \
#   --checkpoint ./etl_output/Bank/checkpoint_Bank.feather \
#   --parameters ./params.csv \
#   --metric wealth \
#   --output ./plots \
#   --percentile 95 \
#   --verbose

#   Changes needed:
#   - change --checkpoint into --input
#   - add input parameters:
#    --style [color|greyscale|color-and-greyscale] 
#   --sets 1-513 \
#   --runs 1-1000 \
#   --workers 2 \
#   --stride [1|2|5|10] \


# Usage:
# python global_sensitivity_analysis.py \
#	--input ./parquet_output \
#   --parameters sample_513_mode_3_with_headers.csv \
#	--table Agent_n \
#	--metric var_names \
#   --output "$OUTPUT_DIR/$OUTPUT_FILE" \
#   --no-plot \
#	--style [color|greyscale|color-and-greyscale] \
#   --percentile 99 \
#   --sets 1-513 \
#   --runs 1-1000 \
#	--workers 2 \
#   --stride [1|2|5|10] \
#   --checkpoint \
#   --format ['feather'|'parquet'] \
#   --verbose
#   >"logs/stdout.log" \
#  2>"logs/stderr.log"

# GSA for all metrics in $METRICS
# Optimized for Memory Stability
# Execute metrics one by one to keep memory deterministic
echo "[BASH] Start processing metrics: ${METRICS[@]}"
for m in "${METRICS[@]}"; do
    echo "[BASH] Start process for metric: $m"
    #python global_sensitivity_analysis.py \
    time python global_sensitivity_analysis.py \
        --input "$INPUT_DIR" \
        --parameters "$SAMPLE_DIR/$SAMPLE_FILE" \
        --table Eurostat \
        --metric "$m" \
        --output "$OUTPUT_DIR" \
        --no-plot \
        --style color-and-greyscale \
        --percentile 99 \
        --sets 1-513 \
        --runs 1-1000 \
        --workers 2 \
        --stride 10 \
        --checkpoint \
        --format 'feather' \
        --verbose \
        >"logs/${m}_stdout.log" 2>"logs/${m}_stderr.log"
done
