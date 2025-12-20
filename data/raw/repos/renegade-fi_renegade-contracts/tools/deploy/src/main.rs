use alloy::primitives::Address;
use alloy::signers::local::PrivateKeySigner;
use clap::{Parser, Subcommand};
use eyre::{eyre, Result};
use renegade_circuit_types::elgamal::{DecryptionKey, EncryptionKey};
use renegade_circuit_types::fixed_point::FixedPoint;
use renegade_crypto::fields::jubjub_to_scalar;
use renegade_util::hex::scalar_to_hex_string;
use std::fs::File;
use std::io::Write;
use std::process::Command;
use std::str::FromStr;
use tool_utils::{prompt_for_eth_address as prompt_for_address, prompt_for_f64, run_command};

/// The signature of the `run` function in the `DeployScript` contract
///
/// Args are:
/// - The owner address
/// - The protocol fee encryption key x-coordinate
/// - The protocol fee encryption key y-coordinate  
/// - The protocol fee rate
/// - The protocol fee recipient address
/// - The permit2 contract address
/// - The weth contract address
const DARKPOOL_RUN_SIGNATURE: &str = "run(address,uint256,uint256,uint256,address,address,address)";

/// The signature of the `run` function in the `DeployDarkpoolImplementationScript` contract
const DARKPOOL_IMPLEMENTATION_RUN_SIGNATURE: &str = "run()";

/// The signature of the `run` function in the `DeployGasSponsorScript` contract
///
/// Args are:
/// - owner (both proxy admin and gas sponsor owner)
/// - darkpoolAddress (address of deployed darkpool)
/// - authAddress (gas sponsor auth address)
const GAS_SPONSOR_RUN_SIGNATURE: &str = "run(address,address,address)";

/// The signature of the `run` function in the `DeployGasSponsorImplementationScript` contract
const GAS_SPONSOR_IMPLEMENTATION_RUN_SIGNATURE: &str = "run()";

/// The signature of the `run` function in the `DeployMalleableMatchConnectorScript` contract
///
/// Args are:
/// - admin (proxy admin address)
/// - gasSponsorAddress (address of gas sponsor)
const MALLEABLE_MATCH_CONNECTOR_RUN_SIGNATURE: &str = "run(address,address)";

/// The signature of the `run` function in the `DeployMalleableMatchConnectorImplementationScript` contract
const MALLEABLE_MATCH_CONNECTOR_IMPLEMENTATION_RUN_SIGNATURE: &str = "run()";

/// The path to which we write the decryption key
const DECRYPTION_KEY_PATH: &str = "fee_decryption_key.txt";

/// The path to which we write the gas sponsor auth private key
const GAS_SPONSOR_AUTH_KEY_PATH: &str = "gas_sponsor_auth_key.txt";

// -------
// | CLI |
// -------

/// Deploy Renegade contracts to an EVM chain
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[command(subcommand)]
    command: Commands,
}

/// Common arguments for all commands
#[derive(Parser, Debug, Clone)]
struct CommonArgs {
    /// RPC URL to deploy to
    #[arg(short, long, env = "RPC_URL", default_value = "http://localhost:8545")]
    rpc_url: String,

    /// Private key for signing transactions
    #[arg(long = "pkey", env = "PKEY", hide_env_values = true)]
    private_key: String,

    /// Verbosity level (v, vv, vvv)
    #[arg(long, default_value = "v")]
    verbosity: String,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Deploy the Darkpool contracts
    #[command(name = "deploy-darkpool")]
    DeployDarkpool(DeployDarkpoolArgs),

    /// Deploy the GasSponsor contract
    #[command(name = "deploy-gas-sponsor")]
    DeployGasSponsor(DeployGasSponsorArgs),

    /// Deploy only the Darkpool implementation contract (for proxy upgrades)
    #[command(name = "deploy-darkpool-implementation")]
    DeployDarkpoolImplementation(DeployDarkpoolImplementationArgs),

    /// Deploy only the GasSponsor implementation contract (for proxy upgrades)
    #[command(name = "deploy-gas-sponsor-implementation")]
    DeployGasSponsorImplementation(DeployGasSponsorImplementationArgs),

    /// Deploy the MalleableMatchConnector contract
    #[command(name = "deploy-malleable-match-connector")]
    DeployMalleableMatchConnector(DeployMalleableMatchConnectorArgs),

    /// Deploy only the MalleableMatchConnector implementation contract (for proxy upgrades)
    #[command(name = "deploy-malleable-match-connector-implementation")]
    DeployMalleableMatchConnectorImplementation(DeployMalleableMatchConnectorImplementationArgs),
}

/// Arguments for deploying Darkpool contracts
#[derive(Parser, Debug)]
struct DeployDarkpoolArgs {
    /// Common arguments
    #[command(flatten)]
    common: CommonArgs,

    /// Owner address for the contracts
    #[arg(long)]
    owner: Option<String>,

    /// Permit2 contract address
    #[arg(long)]
    permit2: Option<String>,

    /// WETH contract address
    #[arg(long)]
    weth: Option<String>,

    /// The protocol fee rate
    #[arg(long)]
    protocol_fee_rate: Option<f64>,

    /// Protocol fee recipient address
    #[arg(long)]
    fee_recipient: Option<String>,

    /// Optional fee decryption key as hex string
    #[arg(long)]
    fee_dec_key: Option<String>,
}

/// Arguments for deploying GasSponsor contract
#[derive(Parser, Debug)]
struct DeployGasSponsorArgs {
    /// Common arguments
    #[command(flatten)]
    common: CommonArgs,

    /// Owner address - serves as both proxy admin and GasSponsor contract owner
    #[arg(long)]
    owner: Option<String>,

    /// Darkpool contract address
    #[arg(long)]
    darkpool: Option<String>,

    /// Auth address for gas sponsorship
    #[arg(long)]
    auth_address: Option<String>,
}

/// Arguments for deploying only the Darkpool implementation contract
#[derive(Parser, Debug)]
struct DeployDarkpoolImplementationArgs {
    /// Common arguments
    #[command(flatten)]
    common: CommonArgs,
}

/// Arguments for deploying only the GasSponsor implementation contract
#[derive(Parser, Debug)]
struct DeployGasSponsorImplementationArgs {
    /// Common arguments
    #[command(flatten)]
    common: CommonArgs,
}

/// Arguments for deploying MalleableMatchConnector contract
#[derive(Parser, Debug)]
struct DeployMalleableMatchConnectorArgs {
    /// Common arguments
    #[command(flatten)]
    common: CommonArgs,

    /// Admin address - serves as proxy admin
    #[arg(long)]
    admin: Option<String>,

    /// Gas sponsor contract address
    #[arg(long)]
    gas_sponsor: Option<String>,
}

/// Arguments for deploying only the MalleableMatchConnector implementation contract
#[derive(Parser, Debug)]
struct DeployMalleableMatchConnectorImplementationArgs {
    /// Common arguments
    #[command(flatten)]
    common: CommonArgs,
}

fn main() -> Result<()> {
    let args = Args::parse();

    match args.command {
        Commands::DeployDarkpool(args) => deploy_darkpool(args),
        Commands::DeployGasSponsor(args) => deploy_gas_sponsor(args),
        Commands::DeployDarkpoolImplementation(args) => deploy_darkpool_implementation(args),
        Commands::DeployGasSponsorImplementation(args) => deploy_gas_sponsor_implementation(args),
        Commands::DeployMalleableMatchConnector(args) => deploy_malleable_match_connector(args),
        Commands::DeployMalleableMatchConnectorImplementation(args) => {
            deploy_malleable_match_connector_implementation(args)
        }
    }
}

/// Deploy the Darkpool contracts
fn deploy_darkpool(mut args: DeployDarkpoolArgs) -> Result<()> {
    // Prompt for required arguments if not provided
    prompt_for_darkpool_args(&mut args)?;

    // Unwrap the Option values now that we're sure they're present and valid
    let owner = args.owner.unwrap();
    let permit2 = args.permit2.unwrap();
    let weth = args.weth.unwrap();
    let fee_recipient = args.fee_recipient.unwrap();
    let fee_rate = args.protocol_fee_rate.unwrap();
    println!("Deploying Darkpool to RPC URL: {}", args.common.rpc_url);
    println!("\tOwner address: {}", owner);
    println!("\tPermit2 address: {}", permit2);
    println!("\tWETH address: {}", weth);
    println!("\tFee recipient: {}", fee_recipient);
    println!("\tProtocol fee rate: {}", fee_rate);

    // Get the fee encryption key
    let enc_key = get_fee_key(args.fee_dec_key.as_deref())?;
    println!("Fee encryption key");
    println!("\tx: {}", enc_key.x);
    println!("\ty: {}", enc_key.y);

    // Convert the protocol fee rate to a fixed point value
    let protocol_fee_fp = FixedPoint::from_f64_round_down(fee_rate);
    let protocol_fee_repr = protocol_fee_fp.repr;

    // Build the forge script command
    let mut cmd = Command::new("forge");
    cmd.arg("script")
        .arg("script/v1/Deploy.s.sol:DeployScript") // Specify contract name with path
        .arg("--rpc-url")
        .arg(&args.common.rpc_url)
        .arg("--sig")
        .arg(DARKPOOL_RUN_SIGNATURE)
        .arg(&owner)
        .arg(format!("{}", enc_key.x))
        .arg(format!("{}", enc_key.y))
        .arg(format!("{protocol_fee_repr}"))
        .arg(&fee_recipient)
        .arg(&permit2)
        .arg(&weth)
        .arg("--ffi") // Add FFI flag to allow external commands (huffc)
        .arg("--broadcast") // Always use broadcast
        .arg("--private-key")
        .arg(&args.common.private_key)
        .arg(format!("-{}", args.common.verbosity));

    // Execute the command
    run_command(cmd)?;

    println!("\nDarkpool deployment completed successfully!");
    Ok(())
}

/// Deploy the GasSponsor contract
fn deploy_gas_sponsor(mut args: DeployGasSponsorArgs) -> Result<()> {
    // Prompt for required arguments if not provided
    prompt_for_gas_sponsor_args(&mut args)?;

    // Unwrap the Option values now that we're sure they're present and valid
    let owner = args.owner.unwrap();
    let darkpool = args.darkpool.unwrap();
    let auth_address = args.auth_address.unwrap();

    println!("Deploying GasSponsor to RPC URL: {}", args.common.rpc_url);
    println!("\tOwner/Admin address: {}", owner);
    println!("\tDarkpool address: {}", darkpool);
    println!("\tAuth address: {}", auth_address);

    // Build the forge script command
    let mut cmd = Command::new("forge");
    cmd.arg("script")
        .arg("script/v1/DeployGasSponsor.s.sol:DeployGasSponsorScript") // Specify contract name with path
        .arg("--rpc-url")
        .arg(&args.common.rpc_url)
        .arg("--sig")
        .arg(GAS_SPONSOR_RUN_SIGNATURE)
        .arg(&owner)
        .arg(&darkpool)
        .arg(&auth_address)
        .arg("--broadcast") // Always use broadcast
        .arg("--private-key")
        .arg(&args.common.private_key)
        .arg(format!("-{}", args.common.verbosity));

    // Execute the command
    run_command(cmd)?;

    println!("\nGasSponsor deployment completed successfully!");
    Ok(())
}

/// Deploy only the Darkpool implementation contract (no proxy, no libraries)
fn deploy_darkpool_implementation(args: DeployDarkpoolImplementationArgs) -> Result<()> {
    println!(
        "Deploying Darkpool implementation to RPC URL: {}",
        args.common.rpc_url
    );

    // Build the forge script command
    let mut cmd = Command::new("forge");
    cmd.arg("script")
        .arg("script/v1/DeployDarkpoolImplementation.s.sol:DeployDarkpoolImplementationScript")
        .arg("--rpc-url")
        .arg(&args.common.rpc_url)
        .arg("--sig")
        .arg(DARKPOOL_IMPLEMENTATION_RUN_SIGNATURE)
        .arg("--broadcast") // Always use broadcast
        .arg("--private-key")
        .arg(&args.common.private_key)
        .arg(format!("-{}", args.common.verbosity));

    // Execute the command
    run_command(cmd)?;

    println!("\nDarkpool implementation deployment completed successfully!");
    Ok(())
}

/// Deploy only the GasSponsor implementation contract (no proxy, no libraries)
fn deploy_gas_sponsor_implementation(args: DeployGasSponsorImplementationArgs) -> Result<()> {
    println!(
        "Deploying GasSponsor implementation to RPC URL: {}",
        args.common.rpc_url
    );

    // Build the forge script command
    let mut cmd = Command::new("forge");
    cmd.arg("script")
        .arg("script/v1/DeployGasSponsorImplementation.sol:DeployGasSponsorImplementationScript")
        .arg("--rpc-url")
        .arg(&args.common.rpc_url)
        .arg("--sig")
        .arg(GAS_SPONSOR_IMPLEMENTATION_RUN_SIGNATURE)
        .arg("--broadcast") // Always use broadcast
        .arg("--private-key")
        .arg(&args.common.private_key)
        .arg(format!("-{}", args.common.verbosity));

    // Execute the command
    run_command(cmd)?;
    println!("\nGasSponsor implementation deployment completed successfully!");
    Ok(())
}

/// Deploy the MalleableMatchConnector contract
fn deploy_malleable_match_connector(mut args: DeployMalleableMatchConnectorArgs) -> Result<()> {
    // Prompt for required arguments if not provided
    prompt_for_malleable_match_connector_args(&mut args)?;

    // Unwrap the Option values now that we're sure they're present and valid
    let admin = args.admin.unwrap();
    let gas_sponsor = args.gas_sponsor.unwrap();

    println!(
        "Deploying MalleableMatchConnector to RPC URL: {}",
        args.common.rpc_url
    );
    println!("\tAdmin address: {}", admin);
    println!("\tGas Sponsor address: {}", gas_sponsor);

    // Build the forge script command
    let mut cmd = Command::new("forge");
    cmd.arg("script")
        .arg("script/v1/DeployMalleableMatchConnector.s.sol:DeployMalleableMatchConnectorScript")
        .arg("--rpc-url")
        .arg(&args.common.rpc_url)
        .arg("--sig")
        .arg(MALLEABLE_MATCH_CONNECTOR_RUN_SIGNATURE)
        .arg(&admin)
        .arg(&gas_sponsor)
        .arg("--broadcast") // Always use broadcast
        .arg("--private-key")
        .arg(&args.common.private_key)
        .arg(format!("-{}", args.common.verbosity));

    // Execute the command
    run_command(cmd)?;

    println!("\nMalleableMatchConnector deployment completed successfully!");
    Ok(())
}

/// Deploy only the MalleableMatchConnector implementation contract (no proxy)
fn deploy_malleable_match_connector_implementation(
    args: DeployMalleableMatchConnectorImplementationArgs,
) -> Result<()> {
    println!(
        "Deploying MalleableMatchConnector implementation to RPC URL: {}",
        args.common.rpc_url
    );

    // Build the forge script command
    let mut cmd = Command::new("forge");
    cmd.arg("script")
        .arg(
            "script/v1/DeployMalleableMatchConnectorImplementation.sol:DeployMalleableMatchConnectorImplementationScript",
        )
        .arg("--rpc-url")
        .arg(&args.common.rpc_url)
        .arg("--sig")
        .arg(MALLEABLE_MATCH_CONNECTOR_IMPLEMENTATION_RUN_SIGNATURE)
        .arg("--broadcast") // Always use broadcast
        .arg("--private-key")
        .arg(&args.common.private_key)
        .arg(format!("-{}", args.common.verbosity));

    // Execute the command
    run_command(cmd)?;
    println!("\nMalleableMatchConnector implementation deployment completed successfully!");
    Ok(())
}

// -----------
// | Helpers |
// -----------

/// Prompt for missing Darkpool arguments
fn prompt_for_darkpool_args(args: &mut DeployDarkpoolArgs) -> Result<()> {
    if args.owner.is_none() || !is_valid_eth_address(args.owner.as_ref().unwrap()) {
        let addr = prompt_for_address("Enter owner address")?;
        args.owner = Some(addr);
    }

    if args.permit2.is_none() || !is_valid_eth_address(args.permit2.as_ref().unwrap()) {
        let addr = prompt_for_address("Enter Permit2 contract address")?;
        args.permit2 = Some(addr);
    }

    if args.weth.is_none() || !is_valid_eth_address(args.weth.as_ref().unwrap()) {
        let addr = prompt_for_address("Enter WETH contract address")?;
        args.weth = Some(addr);
    }

    if args.fee_recipient.is_none() || !is_valid_eth_address(args.fee_recipient.as_ref().unwrap()) {
        let addr = prompt_for_address("Enter protocol fee recipient address")?;
        args.fee_recipient = Some(addr);
    }

    if args.protocol_fee_rate.is_none() {
        let rate = prompt_for_f64("Enter protocol fee rate", 0.0, 1.0)?;
        args.protocol_fee_rate = Some(rate);
    }

    Ok(())
}

/// Prompt for missing GasSponsor arguments
fn prompt_for_gas_sponsor_args(args: &mut DeployGasSponsorArgs) -> Result<()> {
    if args.owner.is_none() || !is_valid_eth_address(args.owner.as_ref().unwrap()) {
        let addr = prompt_for_address("Enter owner address (also used as proxy admin)")?;
        args.owner = Some(addr);
    }

    if args.darkpool.is_none() || !is_valid_eth_address(args.darkpool.as_ref().unwrap()) {
        let addr = prompt_for_address("Enter Darkpool contract address")?;
        args.darkpool = Some(addr);
    }

    if args.auth_address.is_none() {
        println!("No auth address provided. Generating a new key pair...");
        let address = generate_auth_key_pair()?;
        println!("Generated auth address: {}", address);
        args.auth_address = Some(address);
    } else if !is_valid_eth_address(args.auth_address.as_ref().unwrap()) {
        let addr = prompt_for_address("Enter auth address for gas sponsorship")?;
        args.auth_address = Some(addr);
    }

    Ok(())
}

/// Prompt for missing MalleableMatchConnector arguments
fn prompt_for_malleable_match_connector_args(
    args: &mut DeployMalleableMatchConnectorArgs,
) -> Result<()> {
    if args.admin.is_none() || !is_valid_eth_address(args.admin.as_ref().unwrap()) {
        let addr = prompt_for_address("Enter admin address (proxy admin)")?;
        args.admin = Some(addr);
    }

    if args.gas_sponsor.is_none() || !is_valid_eth_address(args.gas_sponsor.as_ref().unwrap()) {
        let addr = prompt_for_address("Enter Gas Sponsor contract address")?;
        args.gas_sponsor = Some(addr);
    }

    Ok(())
}

/// Generate a random private key and derive the corresponding Ethereum address
/// Returns the address
fn generate_auth_key_pair() -> Result<String> {
    // Create a random wallet
    let wallet = PrivateKeySigner::random();
    let address = wallet.address();

    // Get the private key bytes
    let private_key_bytes = wallet.credential().to_bytes();
    let private_key_hex = hex::encode(private_key_bytes);
    let address_hex = format!("{address:?}");

    // Write the private key to a file
    let mut file = File::create(GAS_SPONSOR_AUTH_KEY_PATH)?;
    file.write_all(private_key_hex.as_bytes())?;
    println!("Private key saved to {}", GAS_SPONSOR_AUTH_KEY_PATH);

    Ok(address_hex)
}

// Function to validate Ethereum address using Alloy
fn is_valid_eth_address(address: &str) -> bool {
    Address::from_str(address).is_ok()
}

/// Get the fee encryption key either by generating a new one or deriving from provided decryption key
///
/// Returns the encryption key to use for the protocol fee
fn get_fee_key(fee_dec_key: Option<&str>) -> Result<EncryptionKey> {
    if let Some(hex_key) = fee_dec_key {
        derive_fee_encryption_key(hex_key)
    } else {
        generate_fee_encryption_key()
    }
}

/// Generate a random encryption key
///
/// Writes the decryption key to a file and returns the encryption key
fn generate_fee_encryption_key() -> Result<EncryptionKey> {
    // Generate a random key pair
    println!("Generating random fee encryption key");
    let mut rng = rand::thread_rng();
    let (dec_key, enc_key) = DecryptionKey::random_pair(&mut rng);

    // Write the decryption key to a file
    let key_inner = jubjub_to_scalar(dec_key.key);
    let dec_key_str = scalar_to_hex_string(&key_inner);
    let mut file = File::create(DECRYPTION_KEY_PATH)?;
    file.write_all(dec_key_str.as_bytes())?;

    println!("Decryption key written to {}", DECRYPTION_KEY_PATH);
    Ok(enc_key)
}

/// Derive an encryption key from a provided decryption key hex string
///
/// This does not write the decryption key to a file
fn derive_fee_encryption_key(hex_key: &str) -> Result<EncryptionKey> {
    println!("Using provided fee decryption key");
    let dec_key = DecryptionKey::from_hex_str(hex_key)
        .map_err(|e| eyre!("Failed to parse fee decryption key: {e}"))?;
    Ok(dec_key.public_key())
}
