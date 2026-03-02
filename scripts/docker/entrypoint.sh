#!/bin/bash
set -e

# Auto-install Rust toolchain from rust-toolchain.toml if present
if [ -f rust-toolchain.toml ] || [ -f rust-toolchain ]; then
    # rustup auto-detects and installs the required toolchain
    TOOLCHAIN=$(rustup show active-toolchain 2>/dev/null | awk '{print $1}' || true)
    if [ -n "$TOOLCHAIN" ]; then
        echo "[docker] Using toolchain: $TOOLCHAIN"
        # Install wasm32 target for this specific toolchain
        rustup target add wasm32-unknown-unknown --toolchain "$TOOLCHAIN" 2>/dev/null || true
    fi
else
    echo "[docker] No rust-toolchain file, using default: $(rustc --version)"
fi

# Execute the requested command
exec "$@"
