pub mod merkle_hash;
pub mod merkle_insert;
pub mod sponge_hash;
pub mod util;

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Hash through a Merkle tree
    MerkleHash(MerkleHashArgs),

    /// Hash inputs using a Poseidon sponge
    SpongeHash(SpongeHashArgs),

    /// Compute the root after inserting elements into a Merkle tree sequentially
    InsertAndGetRoot(InsertAndGetRootArgs),
}

#[derive(Parser)]
struct MerkleHashArgs {
    /// The depth of the Merkle tree
    depth: u64,
    /// Index in the Merkle tree
    idx: u64,
    /// Input value
    input: String,
    /// Sister leaves
    sister_leaves: Vec<String>,
}

#[derive(Parser)]
struct SpongeHashArgs {
    /// Input values to hash
    #[arg(required = true)]
    inputs: Vec<String>,
}

#[derive(Parser)]
struct InsertAndGetRootArgs {
    /// The depth of the Merkle tree
    depth: u64,
    /// Input values to insert sequentially (starting from index 0)
    #[arg(required = true)]
    inputs: Vec<String>,
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::MerkleHash(args) => merkle_hash::handle_merkle_hash(args),
        Commands::SpongeHash(args) => sponge_hash::handle_sponge_hash(args),
        Commands::InsertAndGetRoot(args) => merkle_insert::handle_insert_get_root(args),
    }
}
