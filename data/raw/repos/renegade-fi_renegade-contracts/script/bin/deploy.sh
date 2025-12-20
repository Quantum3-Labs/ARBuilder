#!/bin/bash
set -e

# Navigate to the project root
cd "$(dirname "$0")/../../"
cargo run --manifest-path tools/deploy/Cargo.toml -- "$@"
