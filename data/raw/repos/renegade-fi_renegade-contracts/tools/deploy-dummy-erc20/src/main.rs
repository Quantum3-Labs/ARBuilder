use clap::Parser;
use eyre::Result;
use std::process::Command;
use tool_utils::{prompt_for_input, prompt_for_u8, run_command};

// Signatures for the Forge scripts
const RUN_ERC20_SIGNATURE: &str = "run(string,string,uint8)";
const RUN_WETH_SIGNATURE: &str = "deployWeth()";

// -------
// | CLI |
// -------

/// Deploy Dummy ERC20 tokens for testing
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// RPC URL to deploy to
    #[arg(short, long, env = "RPC_URL", default_value = "http://localhost:8545")]
    rpc_url: String,
    /// Deploy WETH instead of a regular ERC20
    #[arg(long)]
    weth: bool,
    /// ERC20 token name (only used for regular ERC20)
    #[arg(long)]
    name: Option<String>,
    /// ERC20 token symbol (only used for regular ERC20)
    #[arg(long)]
    symbol: Option<String>,
    /// Number of decimals (only used for regular ERC20)
    #[arg(long)]
    decimals: Option<u8>,
    /// Private key for signing transactions
    #[arg(long = "pkey", env = "PKEY")]
    private_key: String,
    /// Verbosity level (v, vv, vvv)
    #[arg(long, default_value = "v")]
    verbosity: String,
}

fn main() -> Result<()> {
    // Parse arguments
    let mut args = Args::parse();

    // Determine whether to deploy WETH or regular ERC20
    if args.weth {
        println!("Deploying WETH to RPC URL: {}", args.rpc_url);
        deploy_weth(&args)?;
    } else {
        // Prompt for missing arguments if not deploying WETH
        prompt_for_missing_erc20_args(&mut args)?;

        // Unwrap the Option values now that we're sure they're present
        let name = args.name.as_ref().unwrap();
        let symbol = args.symbol.as_ref().unwrap();
        let decimals = args.decimals.unwrap();

        println!("Deploying ERC20 to RPC URL: {}", args.rpc_url);
        println!("\tName: {}", name);
        println!("\tSymbol: {}", symbol);
        println!("\tDecimals: {}", decimals);
        deploy_erc20(&args, name, symbol, decimals)?;
    }

    println!("\nDeployment completed successfully!");
    Ok(())
}

// Deploy a regular ERC20 token
fn deploy_erc20(args: &Args, name: &str, symbol: &str, decimals: u8) -> Result<()> {
    // Build the forge script command
    let mut cmd = Command::new("forge");
    cmd.arg("script")
        .arg("script/DeployDummyErc20.sol:DeployDummyERC20Script")
        .arg("--rpc-url")
        .arg(&args.rpc_url)
        .arg("--sig")
        .arg(RUN_ERC20_SIGNATURE)
        .arg(name)
        .arg(symbol)
        .arg(format!("{}", decimals))
        .arg("--broadcast")
        .arg("--private-key")
        .arg(&args.private_key)
        .arg(format!("-{}", args.verbosity));

    // Execute the command
    run_command(cmd)
}

// Deploy a WETH token
fn deploy_weth(args: &Args) -> Result<()> {
    // Build the forge script command
    let mut cmd = Command::new("forge");
    cmd.arg("script")
        .arg("script/DeployDummyErc20.sol:DeployWethMockScript")
        .arg("--rpc-url")
        .arg(&args.rpc_url)
        .arg("--sig")
        .arg(RUN_WETH_SIGNATURE)
        .arg("--broadcast")
        .arg("--private-key")
        .arg(&args.private_key)
        .arg(format!("-{}", args.verbosity));

    // Execute the command
    run_command(cmd)
}

// -----------
// | Helpers |
// -----------

/// Prompt for missing ERC20 token arguments
fn prompt_for_missing_erc20_args(args: &mut Args) -> Result<()> {
    if args.name.is_none() {
        let name = prompt_for_input("Enter ERC20 token name")?;
        args.name = Some(name);
    }

    if args.symbol.is_none() {
        let symbol = prompt_for_input("Enter ERC20 token symbol")?;
        args.symbol = Some(symbol);
    }

    if args.decimals.is_none() {
        let decimals = prompt_for_u8("Enter number of decimals", 18)?;
        args.decimals = Some(decimals);
    }

    Ok(())
}
