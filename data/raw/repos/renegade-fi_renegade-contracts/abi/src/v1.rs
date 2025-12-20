use alloy::{
    primitives::{Bytes, U256},
    sol,
};

// We use a combined ABI between the darkpool, gas sponsor, darkpool executor, and malleable match connector as the sol macro currently requires all
// types to be present in the same macro invocation.
sol! {
    #[allow(missing_docs, clippy::too_many_arguments)]
    #[sol(rpc)]
    IDarkpool,
    "ICombinedV1.json",
}

impl Default for IDarkpool::TransferAuthorization {
    fn default() -> Self {
        Self {
            permit2Nonce: U256::ZERO,
            permit2Deadline: U256::ZERO,
            permit2Signature: Bytes::new(),
            externalTransferSignature: Bytes::new(),
        }
    }
}

impl IDarkpool::TransferAuthorization {
    /// Create a withdrawal authorization
    pub fn withdrawal(sig_bytes: Vec<u8>) -> Self {
        Self {
            permit2Nonce: U256::ZERO,
            permit2Deadline: U256::ZERO,
            permit2Signature: Bytes::new(),
            externalTransferSignature: Bytes::from(sig_bytes),
        }
    }
}

#[cfg(feature = "v1-relayer-types")]
pub mod relayer_types {
    use std::borrow::Borrow;

    use alloy::primitives::Address;
    use alloy::primitives::Bytes;
    use alloy::primitives::U256;
    use ark_ec::AffineRepr;
    use ark_ff::{BigInteger, PrimeField};
    use jf_primitives::pcs::prelude::Commitment as JfCommitment;
    use num_bigint::BigUint;
    use renegade_circuit_types::keychain::PublicSigningKey;
    use renegade_circuit_types::r#match::OrderSettlementIndices as CircuitOrderSettlementIndices;
    use renegade_circuit_types::traits::BaseType;
    use renegade_circuit_types::transfers::ExternalTransfer as CircuitExternalTransfer;
    use renegade_circuit_types::transfers::ExternalTransferDirection;
    use renegade_circuit_types::PlonkLinkProof as CircuitPlonkLinkProof;
    use renegade_circuit_types::PlonkProof as CircuitPlonkProof;
    use renegade_circuits::zk_circuits::valid_commitments::ValidCommitmentsStatement as CircuitValidCommitmentsStatement;
    use renegade_circuits::zk_circuits::valid_match_settle::SizedValidMatchSettleStatement;
    use renegade_circuits::zk_circuits::valid_match_settle::SizedValidMatchSettleWithCommitmentsStatement;
    use renegade_circuits::zk_circuits::valid_match_settle_atomic::SizedValidMatchSettleAtomicStatement;
    use renegade_circuits::zk_circuits::valid_reblind::ValidReblindStatement as CircuitValidReblindStatement;
    use renegade_circuits::zk_circuits::valid_wallet_create::SizedValidWalletCreateStatement;
    use renegade_circuits::zk_circuits::valid_wallet_update::SizedValidWalletUpdateStatement;
    use renegade_common::types::transfer_auth::TransferAuth as CircuitTransferAuth;
    use renegade_constants::Scalar;

    use super::BN254::G1Point;

    use super::IDarkpool::*;

    /// Convert a relayer [`SizedValidWalletCreateStatement`] to a contract [`ValidWalletCreateStatement`]
    impl From<SizedValidWalletCreateStatement> for ValidWalletCreateStatement {
        fn from(statement: SizedValidWalletCreateStatement) -> Self {
            Self {
                walletShareCommitment: scalar_to_u256(statement.wallet_share_commitment),
                publicShares: statement
                    .public_wallet_shares
                    .to_scalars()
                    .into_iter()
                    .map(scalar_to_u256)
                    .collect(),
            }
        }
    }

    /// Convert a relayer [`SizedValidWalletUpdateStatement`] to a contract [`ValidWalletUpdateStatement`]
    impl From<SizedValidWalletUpdateStatement> for ValidWalletUpdateStatement {
        fn from(statement: SizedValidWalletUpdateStatement) -> Self {
            Self {
                previousNullifier: scalar_to_u256(statement.old_shares_nullifier),
                newWalletCommitment: scalar_to_u256(statement.new_wallet_commitment),
                newPublicShares: statement
                    .new_public_shares
                    .to_scalars()
                    .into_iter()
                    .map(scalar_to_u256)
                    .collect(),
                merkleRoot: scalar_to_u256(statement.merkle_root),
                externalTransfer: statement.external_transfer.into(),
                oldPkRoot: statement.old_pk_root.into(),
            }
        }
    }

    impl From<CircuitValidReblindStatement> for ValidReblindStatement {
        fn from(statement: CircuitValidReblindStatement) -> Self {
            Self {
                originalSharesNullifier: scalar_to_u256(statement.original_shares_nullifier),
                newPrivateShareCommitment: scalar_to_u256(
                    statement.reblinded_private_share_commitment,
                ),
                merkleRoot: scalar_to_u256(statement.merkle_root),
            }
        }
    }

    impl From<CircuitValidCommitmentsStatement> for ValidCommitmentsStatement {
        fn from(statement: CircuitValidCommitmentsStatement) -> Self {
            Self {
                indices: statement.indices.into(),
            }
        }
    }

    impl From<SizedValidMatchSettleStatement> for ValidMatchSettleStatement {
        fn from(statement: SizedValidMatchSettleStatement) -> Self {
            Self {
                firstPartyPublicShares: statement
                    .party0_modified_shares
                    .to_scalars()
                    .into_iter()
                    .map(scalar_to_u256)
                    .collect(),
                secondPartyPublicShares: statement
                    .party1_modified_shares
                    .to_scalars()
                    .into_iter()
                    .map(scalar_to_u256)
                    .collect(),
                firstPartySettlementIndices: statement.party0_indices.into(),
                secondPartySettlementIndices: statement.party1_indices.into(),
                protocolFeeRate: scalar_to_u256(statement.protocol_fee.repr),
            }
        }
    }

    impl From<SizedValidMatchSettleWithCommitmentsStatement>
        for ValidMatchSettleWithCommitmentsStatement
    {
        fn from(statement: SizedValidMatchSettleWithCommitmentsStatement) -> Self {
            Self {
                privateShareCommitment0: scalar_to_u256(statement.private_share_commitment0),
                privateShareCommitment1: scalar_to_u256(statement.private_share_commitment1),
                newShareCommitment0: scalar_to_u256(statement.new_share_commitment0),
                newShareCommitment1: scalar_to_u256(statement.new_share_commitment1),
                firstPartyPublicShares: statement
                    .party0_modified_shares
                    .to_scalars()
                    .into_iter()
                    .map(scalar_to_u256)
                    .collect(),
                secondPartyPublicShares: statement
                    .party1_modified_shares
                    .to_scalars()
                    .into_iter()
                    .map(scalar_to_u256)
                    .collect(),
                firstPartySettlementIndices: statement.party0_indices.into(),
                secondPartySettlementIndices: statement.party1_indices.into(),
                protocolFeeRate: scalar_to_u256(statement.protocol_fee.repr),
            }
        }
    }

    impl From<SizedValidMatchSettleAtomicStatement> for ValidMatchSettleAtomicStatement {
        fn from(statement: SizedValidMatchSettleAtomicStatement) -> Self {
            Self {
                matchResult: ExternalMatchResult {
                    quoteMint: biguint_to_address(statement.match_result.quote_mint),
                    baseMint: biguint_to_address(statement.match_result.base_mint),
                    quoteAmount: U256::from(statement.match_result.quote_amount),
                    baseAmount: U256::from(statement.match_result.base_amount),
                    direction: statement.match_result.direction as u8,
                },
                externalPartyFees: FeeTake {
                    relayerFee: U256::from(statement.external_party_fees.relayer_fee),
                    protocolFee: U256::from(statement.external_party_fees.protocol_fee),
                },
                internalPartyModifiedShares: statement
                    .internal_party_modified_shares
                    .to_scalars()
                    .into_iter()
                    .map(scalar_to_u256)
                    .collect(),
                internalPartySettlementIndices: statement.internal_party_indices.into(),
                protocolFeeRate: scalar_to_u256(statement.protocol_fee.repr),
                relayerFeeAddress: biguint_to_address(statement.relayer_fee_address),
            }
        }
    }

    // ---------------------
    // | Application Types |
    // ---------------------

    /// Convert a relayer [`ExternalTransfer`] to a contract [`ExternalTransferStruct`]
    impl From<CircuitExternalTransfer> for ExternalTransferStruct {
        fn from(transfer: CircuitExternalTransfer) -> Self {
            let transfer_type = match transfer.direction {
                ExternalTransferDirection::Deposit => 0,
                ExternalTransferDirection::Withdrawal => 1,
            };

            ExternalTransferStruct {
                account: biguint_to_address(transfer.account_addr),
                mint: biguint_to_address(transfer.mint),
                amount: U256::from(transfer.amount),
                transferType: transfer_type,
            }
        }
    }

    impl From<CircuitTransferAuth> for TransferAuthorization {
        fn from(auth: CircuitTransferAuth) -> Self {
            match auth {
                CircuitTransferAuth::Deposit(deposit_auth) => {
                    let permit_sig = Bytes::from(deposit_auth.permit_signature);
                    let permit_deadline = biguint_to_u256(deposit_auth.permit_deadline);
                    let permit_nonce = biguint_to_u256(deposit_auth.permit_nonce);

                    TransferAuthorization {
                        permit2Nonce: permit_nonce,
                        permit2Deadline: permit_deadline,
                        permit2Signature: permit_sig,
                        externalTransferSignature: Bytes::default(),
                    }
                }
                CircuitTransferAuth::Withdrawal(withdrawal_auth) => TransferAuthorization {
                    permit2Nonce: U256::ZERO,
                    permit2Deadline: U256::ZERO,
                    permit2Signature: Bytes::default(),
                    externalTransferSignature: Bytes::from(
                        withdrawal_auth.external_transfer_signature,
                    ),
                },
            }
        }
    }

    /// Convert a relayer [`PublicSigningKey`] to a contract [`PublicRootKey`]
    impl From<PublicSigningKey> for PublicRootKey {
        fn from(key: PublicSigningKey) -> Self {
            let x_words = &key.x.scalar_words;
            let y_words = &key.y.scalar_words;
            let x = [scalar_to_u256(x_words[0]), scalar_to_u256(x_words[1])];
            let y = [scalar_to_u256(y_words[0]), scalar_to_u256(y_words[1])];

            PublicRootKey { x, y }
        }
    }

    /// Convert a relayer [`OrderSettlementIndices`] to a contract [`OrderSettlementIndices`]
    impl From<CircuitOrderSettlementIndices> for OrderSettlementIndices {
        fn from(indices: CircuitOrderSettlementIndices) -> Self {
            Self {
                balanceSend: U256::from(indices.balance_send),
                balanceReceive: U256::from(indices.balance_receive),
                order: U256::from(indices.order),
            }
        }
    }
    // ----------------------
    // | Proof System Types |
    // ----------------------

    /// Convert from a relayer's `PlonkProof` to a contract's `Proof`
    impl From<CircuitPlonkProof> for PlonkProof {
        fn from(proof: CircuitPlonkProof) -> Self {
            let evals = proof.poly_evals;
            Self {
                wireComms: size_vec(
                    proof
                        .wires_poly_comms
                        .into_iter()
                        .map(convert_jf_commitment)
                        .collect(),
                ),
                zComm: convert_jf_commitment(proof.prod_perm_poly_comm),
                quotientComms: size_vec(
                    proof
                        .split_quot_poly_comms
                        .into_iter()
                        .map(convert_jf_commitment)
                        .collect(),
                ),
                wZeta: convert_jf_commitment(proof.opening_proof),
                wZetaOmega: convert_jf_commitment(proof.shifted_opening_proof),
                wireEvals: size_vec(evals.wires_evals.into_iter().map(fr_to_u256).collect()),
                sigmaEvals: size_vec(evals.wire_sigma_evals.into_iter().map(fr_to_u256).collect()),
                zBar: fr_to_u256(evals.perm_next_eval),
            }
        }
    }

    impl From<CircuitPlonkLinkProof> for LinkingProof {
        fn from(proof: CircuitPlonkLinkProof) -> Self {
            Self {
                linkingQuotientPolyComm: convert_jf_commitment(proof.quotient_commitment),
                linkingPolyOpening: convert_g1_point(proof.opening_proof.proof),
            }
        }
    }

    // -----------
    // | Helpers |
    // -----------

    /// Size a vector of values to be a known fixed size
    pub fn size_vec<const N: usize, T>(vec: Vec<T>) -> [T; N] {
        let size = vec.len();
        if size != N {
            panic!("vector is not the correct size: expected {N}, got {size}");
        }
        vec.try_into().map_err(|_| ()).unwrap()
    }

    // --- Alloy Types --- //

    /// Convert a `BigUint` to a `Address`
    pub fn biguint_to_address<B: Borrow<BigUint>>(biguint: B) -> Address {
        let bytes = biguint.borrow().to_bytes_be();
        let padded = pad_bytes::<20>(&bytes);
        Address::from_slice(&padded)
    }

    /// Convert a `BigUint` to a `U256`
    pub fn biguint_to_u256<B: Borrow<BigUint>>(biguint: B) -> U256 {
        let bytes = biguint.borrow().to_bytes_be();
        U256::from_be_slice(&bytes)
    }

    /// Convert an `Address` to a `BigUint`
    pub fn address_to_biguint(address: Address) -> BigUint {
        let bytes = address.0.to_vec();
        BigUint::from_bytes_be(&bytes)
    }

    // --- Scalars --- //

    /// Convert a Scalar to a Uint256
    pub fn scalar_to_u256(scalar: Scalar) -> U256 {
        let bytes = scalar.to_bytes_be();
        bytes_to_u256(&bytes)
    }

    /// Convert a Uint256 to a Scalar
    pub fn u256_to_scalar(u256: U256) -> Scalar {
        let bytes: [u8; 32] = u256.to_be_bytes();
        Scalar::from_be_bytes_mod_order(&bytes)
    }

    /// Convert a `Fr` to a `U256`
    ///
    /// This is the same field as `Scalar`, but must first be wrapped
    fn fr_to_u256(fr: ark_bn254::Fr) -> U256 {
        scalar_to_u256(Scalar::new(fr))
    }

    /// Convert a point in the BN254 base field to a Uint256
    fn base_field_to_u256(fq: ark_bn254::Fq) -> U256 {
        let bytes = fq.into_bigint().to_bytes_be();
        bytes_to_u256(&bytes)
    }

    /// Convert a set of big endian bytes to a Uint256
    ///
    /// Handles padding as necessary
    fn bytes_to_u256(bytes: &[u8]) -> U256 {
        let mut buf = [0u8; 32];
        buf[..bytes.len()].copy_from_slice(bytes);
        U256::from_be_bytes(buf)
    }

    /// Pad big endian bytes to a fixed size
    fn pad_bytes<const N: usize>(bytes: &[u8]) -> [u8; N] {
        assert!(bytes.len() <= N, "bytes are too long for padding");

        let mut padded = [0u8; N];
        padded[N - bytes.len()..].copy_from_slice(bytes);
        padded
    }

    // --- Curve Points --- //

    /// Convert a point on the BN254 curve to a `G1Point` in the contract's format
    fn convert_g1_point(point: ark_bn254::G1Affine) -> G1Point {
        let x = point.x().expect("x is zero");
        let y = point.y().expect("y is zero");

        G1Point {
            x: base_field_to_u256(*x),
            y: base_field_to_u256(*y),
        }
    }

    /// Convert a `JfCommitment` to a `G1Point`
    fn convert_jf_commitment(commitment: JfCommitment<ark_bn254::Bn254>) -> G1Point {
        convert_g1_point(commitment.0)
    }
}
