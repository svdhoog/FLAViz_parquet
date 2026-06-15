#!/bin/bash

#Usage:
#python flaviz_parquet.py --input ./parquet_folder_hierarchy --output ./png_folder

#Circles test model
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/input/pqt'
#OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/output/pqt_flat'

#ABM small-scale
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/output/pqt'
#OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/output/png'

#ABM large
INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/test_data/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/db'
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/test_data/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/png'


python flaviz_parquet_etl.py \
		--input "$INPUT_DIR" \
		--output "$OUTPUT_DIR" \
        --agent-types "Bank,Firm" \
        --sets 1-10 \
        --runs 1-10 \
        --workers 2 \
        --verbose

# python flaviz_parquet_plot.py \
# 		--input "$INPUT_DIR" \
# 		--output-dir "$OUTPUT_DIR" \
# 		--config ./config/test_config_1.json

