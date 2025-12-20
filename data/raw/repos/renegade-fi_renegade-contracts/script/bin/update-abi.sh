#!/bin/bash

# Default output directory to current directory
OUTPUT_DIR="./abi"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --out)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Generate ABI and save to output directory
forge inspect src/libraries/interfaces/IDarkpool.sol:IDarkpool abi --json > "$OUTPUT_DIR/IDarkpool.json"