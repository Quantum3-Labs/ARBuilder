//! Utilities for reading deployment addresses from a JSON file
//!

use alloy::primitives::Address;
use eyre::Result;
use serde_json::Value;
use std::fs;
use std::path::PathBuf;
use std::str::FromStr;

/// The deployments file key for the Darkpool proxy contract
pub(crate) const DARKPOOL_PROXY_DEPLOYMENT_KEY: &str = "DarkpoolProxy";

/// Read an address from the deployments.json file
///
/// Returns the address for the given key, or an error if not found
pub fn read_deployment(key: &str, deployments_path: &PathBuf) -> Result<Address> {
    // Read the deployments file
    let content = fs::read_to_string(deployments_path).map_err(|e| {
        eyre::eyre!(
            "Failed to read deployments file at {}: {}",
            deployments_path.display(),
            e
        )
    })?;
    let json: Value = serde_json::from_str(&content)?;

    // Get the address string
    let addr_str = json
        .get(key)
        .and_then(|v| v.as_str())
        .ok_or_else(|| eyre::eyre!("Key {} not found in deployments file", key))?;

    // Parse into Address
    Address::from_str(addr_str)
        .map_err(|e| eyre::eyre!("Failed to parse address {}: {}", addr_str, e))
}
