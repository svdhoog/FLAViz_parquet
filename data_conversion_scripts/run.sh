#!/bin/bash

#python sql_to_parquet.py --input ./legacy_sql_runs --output ./parquet_mirror

#Circles test model
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/test_data/input/sql'
#OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/test_data/output/pqt'

#ABM small
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql'
#OUTPUT_FILE='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/output/pqt'

#ABM large
INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql_multiple_sets_runs_200MB/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/sql'
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql_multiple_sets_runs_200MB/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/pqt'

python sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR
