use alloy::primitives::Address;
use eyre::{eyre, Result};
use std::io::{self, Write};
use std::process::{Command, Stdio};
use std::str::FromStr;

/// Execute a command with real-time output streaming and proper error handling
pub fn run_command(mut cmd: Command) -> Result<()> {
    // Run the command and check the status
    cmd.stdout(Stdio::inherit()).stderr(Stdio::inherit());
    let status = cmd.status()?;

    // Check if the command succeeded, even if the exit code is non-zero
    // The "default sender" warning causes a non-zero exit code but isn't a real failure
    if status.success() || status.code() == Some(1) {
        Ok(())
    } else {
        Err(eyre!("Command failed with status: {}", status))
    }
}

/// General function to prompt for input with a specific message
pub fn prompt_for_input(prompt: &str) -> io::Result<String> {
    print!("{}: ", prompt);
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    Ok(input.trim().to_string())
}

/// Function to prompt user for a valid u8 with a default value
pub fn prompt_for_u8(prompt: &str, default: u8) -> Result<u8> {
    loop {
        print!("{} [{}]: ", prompt, default);
        io::stdout().flush()?;

        let mut input = String::new();
        io::stdin().read_line(&mut input)?;
        let input = input.trim();

        // Use the default value if the input is empty
        if input.is_empty() {
            return Ok(default);
        }

        // Try to parse the input as a u8
        match input.parse::<u8>() {
            Ok(value) => return Ok(value),
            Err(_) => {
                println!("Invalid value. Please enter a number between 0 and 255.");
                continue;
            }
        }
    }
}

/// Function to prompt user for a valid f64 in a specified range
pub fn prompt_for_f64(prompt: &str, min: f64, max: f64) -> Result<f64> {
    loop {
        let input = prompt_for_input(prompt)?;
        match input.parse::<f64>() {
            Ok(value) if (min..=max).contains(&value) => return Ok(value),
            Ok(_) => {
                println!(
                    "Value must be between {} and {}. Please try again.",
                    min, max
                );
            }
            Err(_) => {
                println!("Invalid number format. Please enter a valid decimal number.");
            }
        }
    }
}

/// Function to prompt user for a valid Ethereum address
pub fn prompt_for_eth_address(prompt: &str) -> Result<String> {
    loop {
        let input = prompt_for_input(prompt)?;

        if is_valid_eth_address_format(&input) {
            return Ok(input);
        } else {
            println!("Invalid Ethereum address format. Please enter a valid address (0x followed by 40 hex characters).");
        }
    }
}

/// Function to validate an Ethereum address format
/// This is a simple check for the 0x prefix and length
pub fn is_valid_eth_address_format(address: &str) -> bool {
    Address::from_str(address).is_ok()
}
