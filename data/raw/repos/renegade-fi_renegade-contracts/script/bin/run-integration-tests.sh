#!/bin/bash

# Default anvil private key
ANVIL_PKEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Print help message
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Start a local Anvil node, deploy contracts, and run integration tests."
    echo
    echo "Options:"
    echo "  --test TEST_NAME    Run a specific integration test"
    echo "  --anvil-logs       Show Anvil node logs (default: hidden)"
    echo "  --no-tests         Skip running tests, just start Anvil and deploy contracts"
    echo "  --v1               Run v1 integration tests (default: v2)"
    echo "  -r, --release      Run tests in release mode"
    echo "  -h, --help         Show this help message"
    echo
    echo "Example:"
    echo "  $0                     # Run all v2 tests with hidden Anvil logs"
    echo "  $0 --v1               # Run all v1 tests with hidden Anvil logs"
    echo "  $0 --anvil-logs        # Run all v2 tests with visible Anvil logs"
    echo "  $0 --test test_name    # Run a specific v2 test with hidden Anvil logs"
    echo "  $0 --v1 --test test_name  # Run a specific v1 test with hidden Anvil logs"
    echo "  $0 --anvil-logs --test test_name  # Run a specific v2 test with visible Anvil logs"
    echo "  $0 --no-tests          # Start Anvil and deploy contracts without running tests"
    echo "  $0 -r                  # Run all v2 tests in release mode"
}

# Parse command line arguments
TEST_NAME=""
SHOW_ANVIL_LOGS=false
SKIP_TESTS=false
RELEASE_MODE=false
VERSION="v2"
while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            TEST_NAME="$2"
            shift 2
            ;;
        --anvil-logs)
            SHOW_ANVIL_LOGS=true
            shift
            ;;
        --no-tests)
            SKIP_TESTS=true
            shift
            ;;
        --v1)
            VERSION="v1"
            shift
            ;;
        -r|--release)
            RELEASE_MODE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Run '$0 --help' for usage information"
            exit 1
            ;;
    esac
done

# Function to cleanup anvil process
cleanup() {
    echo "Cleaning up anvil process..."
    if [ ! -z "$ANVIL_PID" ]; then
        kill $ANVIL_PID
    fi
}

# Set up trap for cleanup on script exit
trap cleanup EXIT

# Start anvil in the background
echo "Starting anvil node..."
if [ "$SHOW_ANVIL_LOGS" = true ]; then
    anvil &
else
    anvil > /dev/null 2>&1 &
fi
ANVIL_PID=$!

# Wait for anvil to start
sleep 2

# Run the deployment script
echo "Running deployment script..."
if ! forge script script/v1/DeployDev.s.sol \
    --ffi \
    --rpc-url http://localhost:8545 \
    --private-key $ANVIL_PKEY \
    --broadcast; then
    echo "Forge script failed. Cleaning up and exiting..."
    exit 1
fi

# Run the Rust integration tests if not skipped
if [ "$SKIP_TESTS" = false ]; then
    echo "Running Rust integration tests ($VERSION)..."
    CARGO_ARGS=""
    if [ "$RELEASE_MODE" = true ]; then
        CARGO_ARGS="--release"
    fi
    if [ -n "$TEST_NAME" ]; then
        echo "Running specific test: $TEST_NAME"
        if ! (cd integration/$VERSION && cargo run $CARGO_ARGS -- --test "$TEST_NAME"); then
            echo "Integration tests failed. Cleaning up and exiting..."
            exit 1
        fi
    else
        if ! (cd integration/$VERSION && cargo run $CARGO_ARGS); then
            echo "Integration tests failed. Cleaning up and exiting..."
            exit 1
        fi
    fi
    echo "Tests completed successfully. Exiting..."
    exit 0
fi

# If we're not running tests, keep the script running until interrupted
echo "Anvil node is running. Press Ctrl+C to exit..."
while true; do
    sleep 1
done 