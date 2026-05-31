#!/bin/bash

#Usage:
#python flaviz_parquet.py --input ./parquet_folder_hierarchy --output ./png_folder

#Circles test model
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/test_data/output/pqt'
#OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/test_data/output/png'

#ABM small-scale
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/output/pqt'
#OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/output/png'

#ABM large
INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql_multiple_sets_runs_200MB/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/pqt'
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql_multiple_sets_runs_200MB/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/png'


python flaviz_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --config ./config/test_config_1.json
