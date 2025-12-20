use regex::Regex;
use std::env;
use std::path::PathBuf;
use std::process::Command;
use std::str::FromStr;

mod project;

use alloy::primitives::Address;

use project::get_wasm;
use project::read_pkg_name;

fn get_wasm_path() -> PathBuf {
    let manifest_dir = env::current_dir().unwrap();
    let name = read_pkg_name(&manifest_dir).unwrap();
    get_wasm(&name).unwrap()
}

pub async fn setup(priv_key: &str, rpc_url: &str) -> eyre::Result<Address> {
    let wasm_file = get_wasm_path();
    println!("stylus check: ...");

    // First run cargo stylus check
    let check_output = Command::new("cargo")
        .arg("stylus")
        .arg("check")
        .output()
        .expect("Failed to execute check command");

    if !check_output.status.success() {
        eprintln!("Check command failed with status: {}", check_output.status);
        eprintln!("stderr: {}", String::from_utf8_lossy(&check_output.stderr));
        return Err(eyre::eyre!("Stylus check failed"));
    }

    let output = Command::new("cargo")
        .arg("stylus")
        .arg("deploy")
        .arg(format!("--wasm-file={}", wasm_file.to_str().unwrap()))
        .arg(format!("--private-key={}", priv_key))
        .arg(format!("--endpoint={}", rpc_url))
        .arg("--no-verify")
        .output()
        .expect("Failed to execute command");

    if !output.status.success() {
        panic!("Command failed with status: {}", output.status);
    }

    let output_str = String::from_utf8_lossy(&output.stdout);
    let ansi_escape_regex = Regex::new(r"\u{1b}\[[0-9;]*[a-zA-Z]").unwrap();
    let clean_output = ansi_escape_regex.replace_all(&output_str, "");
    let address_regex = Regex::new(r"deployed code at address:\s*(0x[a-fA-F0-9]{40})").unwrap();
    if let Some(caps) = address_regex.captures(&clean_output) {
        Ok(Address::from_str(&caps[1]).unwrap())
    } else {
        panic!("not able to get contract address created in deployment")
    }
}
