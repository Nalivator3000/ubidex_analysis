#!/bin/bash
# Helper script to run analysis scripts in Docker container

SCRIPT_NAME=$1
shift  # Remove first argument, rest are script arguments

if [ -z "$SCRIPT_NAME" ]; then
    echo "Usage: ./run_analysis.sh <script_name> [arguments...]"
    echo "Example: ./run_analysis.sh calculate_bid_coefficients.py"
    echo "Example: ./run_analysis.sh analyze_period.py \"Period_Name\" \"2025-11-18\" \"2025-11-23\""
    exit 1
fi

docker exec -it ubidex_analysis python scripts/$SCRIPT_NAME "$@"

