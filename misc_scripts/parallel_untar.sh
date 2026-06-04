#!/usr/bin/env bash
# ================================================================================
# Parallel, Idempotent Tar Extraction Pipeline Framework (Production Version)
# ================================================================================
# Description:
#     Recursively extracts simulation .tar files concurrently using GNU Parallel.
#     Includes an active verification gate that skips extraction if all 1,000 
#     expected database files (set_x_run_y_iters.db) are present in the target folder.
#     Tracks overall execution via a percentage progress indicator.
#
# Usage Syntax:
#     $ ./parallel_untar.sh --input /data/tars --output /data/unpacked \
#         --sets 1-256 --workers 8 --force
# ================================================================================

set -e 

show_help() {
    echo "Usage: $0 -i|--input <dir> -o|--output <dir> [options]"
    echo "Options:"
    echo "  -s, --sets <start-end>   Inclusive range of sets to extract (e.g., 1-256)"
    echo "  -w, --workers <num>      Max concurrent extraction workers (Default: 4)"
    echo "  -f, --force              Disable skipping; overwrite existing directories"
    exit 1
}

# Configured parameters (Default tracking flags preserved without empty root stubs)
WORKERS=4
FORCE_OVERWRITE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input)     INPUT_DIR="$2"; shift 2 ;;
        -o|--output)    OUTPUT_DIR="$2"; shift 2 ;;
        -s|--sets)      SET_RANGE="$2"; shift 2 ;;
        -w|--workers)   WORKERS="$2"; shift 2 ;;
        -f|--force)     FORCE_OVERWRITE=1; shift ;;
        -h|--help)      show_help ;;
        *) echo "Unknown option: $1"; show_help ;;
    esac
done

# Validate that parameters were successfully provided at runtime
if [[ -z "${INPUT_DIR+x}" || -z "${OUTPUT_DIR+x}" ]]; then
    echo "[FATAL] Missing required arguments: --input and --output must be explicitly provided."
    show_help
fi

if [[ ! -d "$INPUT_DIR" ]]; then
    echo "[FATAL] Input directory does not exist: $INPUT_DIR"
    exit 1
fi
mkdir -p "$OUTPUT_DIR"

START_SET=1
END_SET=1000000
USE_STRICT_RANGE=0

if [[ -n "${SET_RANGE+x}" && -n "$SET_RANGE" ]]; then
    if [[ "$SET_RANGE" =~ ^([0-9]+)-([0-9]+)$ ]]; then
        START_SET="${BASH_REMATCH[1]}"
        END_SET="${BASH_REMATCH[2]}"
        USE_STRICT_RANGE=1
        if (( START_SET > END_SET )); then
            echo "[FATAL] Invalid range: start range ($START_SET) cannot exceed end ($END_SET)."
            exit 1
        fi
    else
        echo "[FATAL] Invalid format for --sets. Expected 'start-end' (e.g. 1-256). Got: '$SET_RANGE'"
        exit 1
    fi
fi

if ! command -v parallel &> /dev/null; then
    echo "[FATAL] GNU Parallel is required but not installed."
    echo " -> Install via package manager: 'sudo apt-get install parallel'"
    exit 1
fi

LOG_DIR="$OUTPUT_DIR/extraction_logs"
PROGRESS_DIR="$LOG_DIR/progress_tokens"
mkdir -p "$PROGRESS_DIR"

ERROR_LOG="$LOG_DIR/extraction_errors.log"
true > "$ERROR_LOG" 

# Export workspace state indicators to subshells
export INPUT_DIR OUTPUT_DIR LOG_DIR PROGRESS_DIR ERROR_LOG FORCE_OVERWRITE

extract_set() {
    local set_num="$1"
    local total_jobs="$2"
    local tar_file="$INPUT_DIR/calibration-mode-3_set_${set_num}.tar"
    local set_target_dir="$OUTPUT_DIR/set_${set_num}"
    local set_stdout="$LOG_DIR/set_${set_num}.stdout.log"
    local set_stderr="$LOG_DIR/set_${set_num}.stderr.log"
    local token_file="$PROGRESS_DIR/$set_num"
    
    if [[ ! -f "$tar_file" ]]; then
        # Even if a file is skipped or missing, create a token to maintain accurate completion math
        touch "$token_file"
        return 0 
    fi

    # Advanced Verification Gate
    local execution_needed=1
    if [[ "$FORCE_OVERWRITE" -eq 0 && -d "$set_target_dir" ]]; then
        local missing_files=0
        for run_num in {1..1000}; do
            if [[ ! -f "$set_target_dir/set_${set_num}_run_${run_num}_iters.db" ]]; then
                missing_files=$((missing_files + 1))
                break 
            fi
        done

        if [[ "$missing_files" -eq 0 ]]; then
            echo " -> [SKIPPED] Set $set_num: All 1,000 files already exist."
            execution_needed=0
        fi
    fi

    if [[ "$execution_needed" -eq 1 ]]; then
        echo " -> [STARTING] Extracting Set $set_num..."
        mkdir -p "$set_target_dir"
        
        if tar -xf "$tar_file" -C "$set_target_dir" >"$set_stdout" 2>"$set_stderr"; then
            echo " -> [SUCCESS] Finished Set $set_num"
            rm -f "$set_stdout" "$set_stderr"
        else
            local exit_code=$?
            echo "[CRITICAL FAILURE] Set $set_num failed with exit code $exit_code" | tee -a "$ERROR_LOG"
            echo "Check details in: $set_stderr" >> "$ERROR_LOG"
            touch "$token_file"
            return 1
        fi
    fi

    # Update thread-safe progress calculations
    touch "$token_file"
    local completed_jobs
    completed_jobs=$(ls -1 "$PROGRESS_DIR" | wc -l)
    
    # Calculate progress using basic shell arithmetic strings
    local percentage
    percentage=$(awk -v c="$completed_jobs" -v t="$total_jobs" 'BEGIN { printf "%.2f", (c/t)*100 }')
    
    echo " -> [PROGRESS] ${percentage}% Complete (${completed_jobs}/${total_jobs} sets processed)"
}

export -f extract_set

echo "================================================================================"
echo "Starting Parallel Tar Extraction Pipeline Infrastructure"
echo "================================================================================"
echo "Source Matrix:      $INPUT_DIR"
echo "Target Destination: $OUTPUT_DIR"
echo "Worker Core Lanes:  $WORKERS"
[[ "$USE_STRICT_RANGE" -eq 1 ]] && echo "Filter Scope:       Sets $START_SET to $END_SET (inclusive)"
echo "================================================================================"

WORK_QUEUE=()
for tar_path in "$INPUT_DIR"/calibration-mode-3_set_*.tar; do
    if [[ -f "$tar_path" ]]; then
        filename=$(basename "$tar_path")
        if [[ "$filename" =~ _set_([0-9]+)\.tar$ ]]; then
            set_idx="${BASH_REMATCH[1]}"
            if [[ "$USE_STRICT_RANGE" -eq 1 ]]; then
                if (( set_idx >= START_SET && set_idx <= END_SET )); then
                    WORK_QUEUE+=("$set_idx")
                fi
            else
                WORK_QUEUE+=("$set_idx")
            fi
        fi
    fi
done

TOTAL_JOBS=${#WORK_QUEUE[@]}
echo "Found $TOTAL_JOBS valid target archives to process."

if [[ $TOTAL_JOBS -eq 0 ]]; then
    echo "No work tasks identified. Exiting pipeline workspace cleanly."
    rm -rf "$LOG_DIR"
    exit 0
fi

# Run tasks concurrently using GNU Parallel
# Pass TOTAL_JOBS as a constant second argument ($2) into the worker function
printf "%s\n" "${WORK_QUEUE[@]}" | parallel -j "$WORKERS" extract_set {} "$TOTAL_JOBS"

if [[ -s "$ERROR_LOG" ]]; then
    echo "================================================================================"
    echo "[WARNING] Extraction pipeline finished with errors. Review failures inside:"
    echo " -> $ERROR_LOG"
    echo "================================================================================"
    exit 1
else
    echo "================================================================================"
    echo "[COMPLETE] All target simulation sets extracted successfully with zero errors."
    echo "================================================================================"
    rm -rf "$LOG_DIR"
    exit 0
fi
