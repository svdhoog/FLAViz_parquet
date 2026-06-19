#!/bin/bash

# Hierarchy: set_n/run_M/data_Agent.Parquet files
INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/output/pqt'

# Flat data_Agent.Parquet files
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/etl_output/pqt'
#OUTPUT_FILE='gsa_summary.txt'

SAMPLE_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data'
SAMPLE_FILE='sample_with_headers.csv'

METRICS=("r" "a" "b")


## REFACTORED VERSION (15 June 2026)
# Usage:
python global_sensitivity_analysis.py \
  --checkpoint "$OUTPUT_DIR/Bank/checkpoint_Agent.feather" \
  --parameters "$SAMPLE_DIR/$SAMPLE_FILE" \
  --metric "a" \
  --output "$OUTPUT_DIR" \
  --percentile 95 \
  --verbose
>"logs/${m}_stdout.log" 2>"logs/${m}_stderr.log"

#   Changes needed:
#   - change --checkpoint into --input
#   - add input parameters:
#    --style [color|greyscale|color-and-greyscale] 
#   --sets 1-513 \
#   --runs 1-1000 \
#   --workers 2 \
#   --stride [1|2|5|10] \

## OLD VERSION
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
        --table Agent \
        --metric "$m" \
        --output "$OUTPUT_DIR" \
        --no-plot \
        --style color-and-greyscale \
        --percentile 100 \
        --sets 1-4 \
        --runs 1-2 \
        --workers 2 \
        --stride 1 \
        --checkpoint \
        --format 'feather' \
        --verbose \
        >"logs/${m}_stdout.log" 2>"logs/${m}_stderr.log"
done
