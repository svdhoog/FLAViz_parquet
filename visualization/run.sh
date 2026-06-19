#!/bin/bash

#Usage:
#python unified_etl.py --input ./parquet_folder_hierarchy --output ./pqt_folder

#Circles test model
INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/input/pqt'
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/output/png_flat'

#ABM large, --sets 4-5 --runs 1-2
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/test_data/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/pqt'
#OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/test_data/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/png'

## REFACTORED VERSION (15 June 2026)
# python unified_etl.py \
# 		--input "$INPUT_DIR" \
# 		--output "$OUTPUT_DIR" \
#         --sets 1-10 \
#         --runs 1-10 \
#         --stride 10 \
#         --workers 2 \
#         --verbose
#   >"logs/stdout.log" \
#  2>"logs/stderr.log"
#       --agent-types "Eurostat,Bank,Firm" \


## OLD VERSION
# python flaviz_parquet_etl.py \
# 		--input "$INPUT_DIR" \
# 		--output "$OUTPUT_DIR" \
#         --agent-types "Bank,Firm" \
#         --sets 1-10 \
#         --runs 1-10 \
#         --workers 2 \
#         --verbose

python flaviz_parquet_plot.py \
		--input "$INPUT_DIR" \
		--output-dir "$OUTPUT_DIR" \
		--config ./config/test_config_1.json

