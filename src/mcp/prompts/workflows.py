"""
Prompt templates for Stylus development workflows.

These templates guide the AI IDE through common development tasks
with structured, step-by-step instructions.
"""

BUILD_CONTRACT_PROMPT = """# Build Stylus Contract Workflow

You are helping the user build a Stylus smart contract. Follow these steps:

## Pre-flight Checks
1. Verify Rust toolchain is installed: `rustup --version`
2. Check WASM target exists: `rustup target list --installed | grep wasm32`
3. Verify cargo-stylus is installed: `cargo stylus --version`

If any are missing, provide installation commands.

## Project Validation
Check the project structure:
- `Cargo.toml` exists with correct configuration
- `src/lib.rs` has `#![cfg_attr(not(feature = "export-abi"), no_main)]`
- `crate-type = ["cdylib"]` is set

## Build Steps
{release_mode_section}

### Step 1: Build for WASM
```bash
cargo build {release_flag} --target wasm32-unknown-unknown
```

### Step 2: Validate with Stylus
```bash
cargo stylus check
```

If validation fails, analyze the error and suggest fixes.

### Step 3: Export ABI (if needed)
```bash
cargo stylus export-abi
```

## Common Build Errors
- **"unresolved import `std`"**: Add `#![no_std]` or check feature flags
- **"linking with `cc` failed"**: Install WASM target
- **"contract exceeds size limit"**: Enable release optimizations

Project path: {project_path}
"""

DEPLOY_CONTRACT_PROMPT = """# Deploy Stylus Contract Workflow

You are helping the user deploy a Stylus contract to {network}.

## Network Configuration
{network_config}

## Pre-deployment Checklist
1. ✅ Contract builds successfully (`cargo stylus check` passes)
2. ✅ Wallet has sufficient ETH for gas
3. ✅ Private key is securely prepared
4. ✅ Correct network selected

## Deployment Steps

### Step 1: Prepare Private Key
{key_method_instructions}

**Security Reminder**:
- NEVER commit private keys to git
- Add `key.txt` to `.gitignore`
- Use `chmod 600 key.txt` for file permissions

### Step 2: Verify Wallet Balance
```bash
cast balance YOUR_ADDRESS --rpc-url {rpc_url}
```

Ensure you have at least 0.01 ETH for testnet deployment.

### Step 3: Estimate Gas (Optional)
```bash
cargo stylus deploy --estimate-gas --private-key-path=./key.txt --endpoint={rpc_url}
```

### Step 4: Deploy
```bash
cargo stylus deploy --private-key-path=./key.txt --endpoint={rpc_url}
```

### Step 5: Verify Deployment
After deployment, save these details:
- Contract Address
- Deployment Transaction Hash
- Activation Transaction Hash

Verify on explorer: {explorer_url}

## Post-Deployment
1. Export ABI: `cargo stylus export-abi > abi.json`
2. Test contract: `cast call CONTRACT_ADDRESS 'functionName()' --rpc-url {rpc_url}`
3. Update frontend/documentation with contract address
"""

DEBUG_ERROR_PROMPT = """# Debug Stylus Error

You are helping diagnose and fix a Stylus development error.

## Error Received
```
{error_message}
```

## Context
{context}

## Diagnostic Steps

### 1. Categorize the Error
Determine if this is:
- **Build error**: Rust/WASM compilation issue
- **Validation error**: cargo stylus check failure
- **Deployment error**: On-chain transaction failure
- **Runtime error**: Contract execution failure

### 2. Common Solutions by Category

#### Build Errors
- Missing imports → Check `use` statements and dependencies
- Type mismatches → Verify function signatures match Solidity ABI
- No std → Ensure `#![no_std]` or proper std feature

#### Validation Errors
- Size too large → Enable release optimizations, LTO
- Invalid imports → Remove unsupported WASM features
- Memory issues → Use stylus-sdk allocator

#### Deployment Errors
- Insufficient funds → Add ETH to wallet
- Nonce issues → Wait for pending transactions
- Gas estimation failed → Contract may revert on construction

#### Runtime Errors
- Revert with message → Decode error using `cast 4byte-decode`
- Out of gas → Optimize contract or increase gas limit
- Invalid state → Check storage layout and initialization

### 3. Recommended Fix
Based on the error, provide:
1. Explanation of root cause
2. Specific code or config changes needed
3. Commands to verify the fix
"""

OPTIMIZE_GAS_PROMPT = """# Optimize Stylus Contract for Gas Efficiency

You are helping optimize a Stylus contract for gas efficiency and size.

## Contract Code to Optimize
```rust
{contract_code}
```

## Optimization Focus: {focus}

## Optimization Strategies

### Size Optimization (affects deployment cost)
1. **Cargo.toml settings**:
```toml
[profile.release]
opt-level = "s"  # or "z" for even smaller
lto = true
codegen-units = 1
panic = "abort"
strip = true
```

2. **Code changes**:
- Remove unused dependencies
- Avoid string formatting (use byte literals)
- Minimize generic code (causes bloat)
- Use `#[inline(never)]` for rarely-called functions

### Compute Optimization (affects call cost)
1. **Batch operations**: Combine multiple storage reads/writes
2. **Cache storage values**: Read once, operate in memory
3. **Use efficient types**: `U256` operations are optimized in WASM
4. **Avoid unnecessary checks**: Trust internal state when safe

### Storage Optimization (highest gas impact)
1. **Pack storage slots**: Group small values together
2. **Use events for historical data**: Don't store what you can emit
3. **Lazy initialization**: Don't initialize zero values
4. **Clear unused storage**: Get gas refunds

## Specific Recommendations
Analyze the provided code and suggest:
1. Specific lines to change
2. Expected gas/size savings
3. Any trade-offs (readability, functionality)

## Verification
After optimization:
```bash
cargo stylus check --release
```
Compare WASM size before/after.
"""

GENERATE_CONTRACT_PROMPT = """# Generate Stylus Smart Contract

Generate a Stylus smart contract based on these requirements:

## Description
{description}

## Contract Type: {contract_type}

## Requirements
- Use Stylus SDK best practices
- Include proper error handling
- Add doc comments for all public functions
- Follow Rust naming conventions

## Template Structure

```rust
#![cfg_attr(not(feature = "export-abi"), no_main)]
extern crate alloc;

use stylus_sdk::{{alloy_primitives::{{Address, U256}}, prelude::*, storage::*}};

sol_storage! {{
    #[entrypoint]
    pub struct ContractName {{
        // Storage fields here
    }}
}}

#[public]
impl ContractName {{
    // Public functions here
}}

// Internal implementation
impl ContractName {{
    // Private helper functions here
}}
```

## Include Tests: {include_tests}

{test_section}

## Generated Contract
Generate the complete contract code following the template above.
Ensure all imports are correct and the code compiles with `cargo stylus check`.
"""
