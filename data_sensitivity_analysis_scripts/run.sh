#!/bin/bash


INPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/pqt'
OUTPUT_DIR='/home/sander/Documents/GIT/GitHub/FLAME-HPC/xparser@svdhoog/sandbox_parquet_integration/test_models/ABM/calibration_data'
OUTPUT_FILE='gsa_summary.txt'

SAMPLE_DIR='/home/sander/Documents/GIT/GitHub/FLAME-HPC/xparser@svdhoog/sandbox_parquet_integration/test_models/ABM/calibration_data'
SAMPLE_FILE='sample_513_mode_3.csv'

METRICS="unemployment_rate, monthly_output, price_index, total_debt"

# Usage:
# python global_sensitivity_analysis.py --input ./parquet_mirror_output \
#        --parameters sample_513_mode_3.csv --table Agent_n --metric var_names \
#		 --sets 1-10 --runs 1-100 --workers 4 --style color-and-greyscale

#GSA for 'unemployment_rate':
time python global_sensitivity_analysis.py --input $INPUT_DIR --output $OUTPUT_DIR/$OUTPUT_FILE \
        --parameters "$SAMPLE_DIR/$SAMPLE_FILE" --table Eurostat --metric $METRICS \
         --sets 1-513 --runs 1-1000 --workers 4 \
         --style color-and-greyscale
