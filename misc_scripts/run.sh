#!/bin/bash

SRC_LOCAL='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/sandbox_parquet_integration/test_data/flat'
SRC_BKUP='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data'

SUB_1='sets-1-256/calibration-mode-3-stage-1-sets-1-256-tarballs-part-1/tarballs'
SUB_2='sets-257-513/calibration-mode-3-stage-1-sets-257-513-tarballs-part-2/tarballs'

OUT_1='sets-1-513/db'

## 1. Rename original downloaded files

#echo "Unpacking from: $SRC_BKUP, writing to: $SRC_BKUP"
#cd "$SRC_BKUP"
#echo "Now in: $PWD"

# File 1: calibration-mode-3-stage-1-sets-1-256-tarballs-part-1 - is tar.bz2, rename, unpack with: tar -xvfz file -C output
# mv calibration-mode-3-stage-1-sets-1-256-tarballs-part-1 calibration-mode-3-stage-1-sets-1-256-tarballs-part-1.tar.bz2

# File 2: calibration-mode-3-stage-1-sets-257-513-tarballs-part-2 - is tar.gz, rename, unpack with: gzip -d 
# mv calibration-mode-3-stage-1-sets-257-513-tarballs-part-2 calibration-mode-3-stage-1-sets-257-513-tarballs-part-2.tar.gz

## 2. Decompression

# File 1: this unpacks to: sets-1-256/calibration-mode-3-stage-1-sets-1-256-tarballs-part-1/tarballs
# tar -xvfz calibration-mode-3-stage-1-sets-1-256-tarballs-part-1.tar.bz2 -C sets-1-256/

# File 2: this unpacks to: sets-257-513/calibration-mode-3-stage-1-sets-257-513-tarballs-part-1/tarballs
# gzip -d calibration-mode-3-stage-1-sets-257-513-tarballs-part-2.tar.gz
#tar -xvf calibration-mode-3-stage-1-sets-257-513-tarballs-part-2.tar -C flat/sets-257-513/ >stdout_untar_1.txt >>stderr_untar_1.txt &

## 3. Unpack tar archives to .db files

# INPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/tar'
# OUTPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/db'

# # Run the pipeline across all 513 sets matching your target path matrices
# ./parallel_untar.sh \
#   --input $INPUT_DIR \
#   --output $OUTPUT_DIR \
#   --sets 1-513 \
#   --workers 4

## 4. Convert .db files to parquet files
# INPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/db'
# OUTPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/pqt'

# SRC='/home/sander/Documents/GIT/GitHub/FLAViz@svdhoog/FLAViz_parquet/data_conversion_scripts'

# # Test small:
# #python $SRC/sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --sets 1-2 --runs 1-2 #--force

# # Test medium:
# #python $SRC/sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --sets 1-2 --runs 1-1000 #--force

# # Full:
# python $SRC/sql_to_parquet.py --input $INPUT_DIR --output $OUTPUT_DIR --sets 3-513 --runs 1-1000 #--force


## 5. Tar archive the folder hierarchy of parquet files
INPUT_DIR='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/flat/sets-1-513/pqt'
OUTPUT_FILE='/media/sander/FE428397428352F71/Data/Estimation_and_Calibration_Dataset/Data/calibration-data/calibration-mode-3-stage-1-sets-1-513-parquet-files.tar'

tar -cf "$OUTPUT_FILE" "$INPUT_DIR"
