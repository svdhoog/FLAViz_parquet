#!bin/bash

#Usage:
#python flaviz_inspect.py -i ./parquet_mirror_output -o ./dataset_summary.txt

#Figure out what is in a single parquet file:
#python -c "import duckdb; print(duckdb.query(\"DESCRIBE SELECT * FROM '$INPUT_DIR/**/*.parquet' LIMIT 1\").df())"

#Circles test model
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/output/pqt'
#OUTPUT_FILE='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/circle/test_data/output/dataset_summary.txt'

#ABM small
#INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/output/pqt'
#OUTPUT_FILE='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/output/dataset_summary.txt'

#ABM large
INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql_multiple_sets_runs_200MB/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/pqt'
OUTPUT_FILE='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/test_models/ABM/test_data/input/sql_multiple_sets_runs_200MB/data_input_1600_stable_gamma_12_for_5_cases_eurostat_firms_banks/dataset_summary.txt'

python flaviz_inspect.py --input $INPUT_DIR --output $OUTPUT_FILE
