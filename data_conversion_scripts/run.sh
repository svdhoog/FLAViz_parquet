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
# INPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/db'
# OUTPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/pqt'

# echo "Data conversion from: $INPUT_DIR, writing Parquet files to: $OUTPUT_FILE"
# Use --force: when you want to overwrite already processed files. This can be useful if the previous process halted unexpectedly.

# Test small:
#python sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --sets 1-2 --runs 1-2 #--force

# Test medium:
#python sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --sets 1-1 --runs 1-1000 #--force

# Full:
#python sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --sets 1-513 --runs 1-1000 #--force

# Conversion from feather 2 parquet
INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/calibration_data/output'
PYTHON_SCRIPT="feather_to_parquet.py"

echo "Data conversion from : $INPUT_DIR"
echo "Scanning '$INPUT_DIR' for Feather files..."
echo "----------------------------------------"

# Recursively find and process files
# Using -print0 and read -r -d '' safely handles filenames with spaces or newlines
find "$INPUT_DIR" -type f -name "*.feather" -print0 | while IFS= read -r -d '' file; do
    echo "Processing: $file"
    
	# Predict the expected .parquet file path
    # ${file%.feather} strips the '.feather' extension from the end of the string
    expected_parquet="${file%.feather}.parquet"
    
    # Run the python script on the file
    python3 "$PYTHON_SCRIPT" --input "$file" --output "$expected_parquet" --quiet
    python_status=$?
    
    # Check both the Python exit code AND the existence of the .parquet file
    if [ $python_status -eq 0 ] && [ -s "$expected_parquet" ]; then
        echo "SUCCESS: Converted to $expected_parquet"
    else
        echo "ERROR: Failed to convert $file" >&2
        if [ ! -s "$expected_parquet" ]; then
            echo "       Reason: Expected output file '$expected_parquet' was not created or is empty." >&2
        fi
    fi
    echo "----------------------------------------"
done
echo "Traversal complete."

# Conversion from parquet 2 feather
# INPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_models/ABM/calibration_data/output'

# PYTHON_SCRIPT="parquet_to_feather.py"

# echo "Data conversion from : $INPUT_DIR"
# echo "Scanning '$INPUT_DIR' for Parquet files..."
# echo "----------------------------------------"

# # Recursively find and process files
# # Using -print0 and read -r -d '' safely handles filenames with spaces or newlines
# find "$INPUT_DIR" -type f -name "*.parquet" -print0 | while IFS= read -r -d '' file; do
#     echo "Processing: $file"
	  
# 	  # Predict the expected .feather file path
#     # ${file%.parquet} strips the '.parquet' extension from the end of the string
#     expected_feather="${file%.parquet}.feather"
    
#     # Run the python script on the file
#     python3 "$PYTHON_SCRIPT" --input "$file" --output "$expected_feather" --quiet
#     python_status=$?
    
#     # Check both the Python exit code AND the existence of the .feather file
#     if [ $python_status -eq 0 ] && [ -s "$expected_feather" ]; then
#         echo "SUCCESS: Converted to $expected_feather"
#     else
#         echo "ERROR: Failed to convert $file" >&2
#         if [ ! -s "$expected_feather" ]; then
#             echo "       Reason: Expected output file '$expected_feather' was not created or is empty." >&2
#         fi
#     fi
#     echo "----------------------------------------"
# done
# echo "Traversal complete."
