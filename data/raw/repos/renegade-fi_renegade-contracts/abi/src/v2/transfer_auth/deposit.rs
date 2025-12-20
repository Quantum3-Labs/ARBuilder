//! Permit2 helpers for depositing using the ISignatureTransfer interface

use alloy::{
    primitives::{Address, U256},
    signers::{local::PrivateKeySigner, Error as SignerError, Signature, SignerSync},
    sol,
    sol_types::{eip712_domain, SolStruct},
};

use crate::v2::IDarkpoolV2::Deposit;

// ---------------
// | Permit2 ABI |
// ---------------

/// The name of the domain separator for Permit2 typed data
pub(crate) const PERMIT2_EIP712_DOMAIN_NAME: &str = "Permit2";

// Types & methods from the Permit2 `ISignatureTransfer` interface, taken from https://github.com/Uniswap/permit2/blob/main/src/interfaces/ISignatureTransfer.sol
sol! {
    /// The token and amount details for a transfer signed in the permit transfer signature
    struct TokenPermissions {
        /// ERC20 token address
        address token;
        /// the maximum amount that can be spent
        uint256 amount;
    }

    /// The Permit2 witness type used in a deposit
    struct DepositWitness {
        /// The commitment to the new balance after deposit
        uint256 newBalanceCommitment;
    }

    /// The signed permit message for a single token transfer
    struct PermitWitnessTransferFrom {
        /// The token permissions for the transfer
        TokenPermissions permitted;
        /// The address to which the transfer is made
        address spender;
        /// a unique value for every token owner's signature to prevent signature replays
        uint256 nonce;
        /// deadline on the permit signature
        uint256 deadline;
        /// The witness for the transfer
        DepositWitness witness;
    }
}

// -------------------
// | Permit2 Helpers |
// -------------------

/// Create a permit for a signature deposit into the darkpool
pub fn create_deposit_permit(
    commitment: U256,
    deposit: Deposit,
    chain_id: u64,
    darkpool: Address,
    permit2: Address,
    signer: &PrivateKeySigner,
) -> Result<(PermitWitnessTransferFrom, Signature), SignerError> {
    let nonce = U256::random();
    let deadline = U256::MAX;
    let witness = DepositWitness {
        newBalanceCommitment: commitment,
    };

    // Build the permit
    let signable_permit = PermitWitnessTransferFrom {
        permitted: TokenPermissions {
            token: deposit.token,
            amount: deposit.amount,
        },
        spender: darkpool,
        nonce,
        deadline,
        witness,
    };

    let signature = sign_permit(chain_id, permit2, &signable_permit, signer)?;
    Ok((signable_permit, signature))
}

/// Sign a permit
pub fn sign_permit(
    chain_id: u64,
    permit2: Address,
    permit: &PermitWitnessTransferFrom,
    signer: &PrivateKeySigner,
) -> Result<Signature, SignerError> {
    // Construct the EIP712 domain
    let permit_domain = eip712_domain!(
        name: PERMIT2_EIP712_DOMAIN_NAME,
        chain_id: chain_id,
        verifying_contract: permit2,
    );

    let msg_hash = permit.eip712_signing_hash(&permit_domain);
    let signature = signer.sign_hash_sync(&msg_hash)?;
    Ok(signature)
}
