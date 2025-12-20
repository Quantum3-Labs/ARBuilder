// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable var-name-mixedcase */

import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";
import { PlonkProof } from "renegade-lib/verifier/Types.sol";
import { BN254 } from "solidity-bn254/BN254.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { IVerifier } from "darkpoolv1-interfaces/IVerifier.sol";
import { IWETH9 } from "renegade-lib/interfaces/IWETH9.sol";
import {
    ValidWalletCreateStatement,
    ValidWalletUpdateStatement,
    ValidMatchSettleStatement,
    ValidMatchSettleWithCommitmentsStatement,
    ValidMatchSettleAtomicStatement,
    ValidMatchSettleAtomicWithCommitmentsStatement,
    ValidMalleableMatchSettleAtomicStatement,
    ValidOfflineFeeSettlementStatement,
    ValidFeeRedemptionStatement
} from "darkpoolv1-lib/PublicInputs.sol";
import {
    PartyMatchPayload,
    MatchProofs,
    MatchLinkingProofs,
    MatchAtomicProofs,
    MatchAtomicLinkingProofs,
    MalleableMatchAtomicProofs
} from "darkpoolv1-types/Settlement.sol";
import { TransferAuthorization } from "darkpoolv1-types/Transfers.sol";
import { EncryptionKey } from "renegade-lib/Ciphertext.sol";

/// @title IDarkpool
/// @author Renegade Eng
/// @notice Interface for the Renegade darkpool contract for private trading
interface IDarkpool {
    // --- Errors --- //

    /// @notice Thrown when fee is set to zero
    error FeeCannotBeZero();
    /// @notice Thrown when an address parameter is zero
    error AddressCannotBeZero();
    /// @notice Thrown when proof verification fails
    error VerificationFailed();
    /// @notice Thrown when a signature is invalid
    error InvalidSignature();
    /// @notice Thrown when order settlement indices don't match
    error InvalidOrderSettlementIndices();
    /// @notice Thrown when protocol fee rate doesn't match expected
    error InvalidProtocolFeeRate();
    /// @notice Thrown when private share commitment doesn't match
    error InvalidPrivateShareCommitment();
    /// @notice Thrown when ETH value is invalid for the transaction
    error InvalidETHValue();
    /// @notice Thrown when protocol encryption key doesn't match
    error InvalidProtocolEncryptionKey();

    // --- Events --- //

    /// @notice Emitted when a wallet update is performed
    /// @param wallet_blinder_share The public blinder share of the wallet, used for indexing
    /// forge-lint: disable-next-line(mixed-case-variable)
    event WalletUpdated(uint256 indexed wallet_blinder_share);
    /// @notice Emitted when an internal Merkle node is updated
    /// @param depth The depth at which the node is updated
    /// @param index The index of the node in the Merkle tree
    /// @param new_value The new value of the node
    /// forge-lint: disable-next-line(mixed-case-variable)
    event MerkleOpeningNode(uint8 indexed depth, uint128 indexed index, uint256 new_value);
    /// @notice Emitted when a Merkle leaf is inserted into the tree
    /// @param index The leaf index
    /// @param value The value of the leaf
    /// forge-lint: disable-next-line(mixed-case-variable)
    event MerkleInsertion(uint128 indexed index, uint256 indexed value);
    /// @notice Emitted when a nullifier is spent
    /// @param nullifier The nullifier that was spent
    event NullifierSpent(BN254.ScalarField nullifier);
    /// @notice Emitted when an external transfer is executed
    /// @param account The account that the transfer is executed for
    /// @param mint The mint of the token that is transferred
    /// @param isWithdrawal Whether the transfer is a withdrawal
    /// @param amount The amount of the token that is transferred
    event ExternalTransfer(address indexed account, address indexed mint, bool indexed isWithdrawal, uint256 amount);
    /// @notice Emitted when a note commitment is inserted into the Merkle tree
    /// @param noteCommitment The commitment inserted
    event NotePosted(uint256 indexed noteCommitment);

    /// @notice Initialize the darkpool
    /// @param initialOwner The initial owner of the contract
    /// @param protocolFeeRate_ The protocol fee rate
    /// @param protocolFeeRecipient_ The recipient for protocol fees
    /// @param protocolFeeKey_ The encryption key for protocol fees
    /// @param weth_ The WETH contract
    /// @param hasher_ The Poseidon hasher contract
    /// @param verifier_ The verifier contract
    /// @param permit2_ The Permit2 contract
    /// @param transferExecutor_ The transfer executor contract
    function initialize(
        address initialOwner,
        uint256 protocolFeeRate_,
        address protocolFeeRecipient_,
        EncryptionKey memory protocolFeeKey_,
        IWETH9 weth_,
        IHasher hasher_,
        IVerifier verifier_,
        IPermit2 permit2_,
        address transferExecutor_
    )
        external;

    // --- Admin Interface --- //

    /// @notice Returns the current owner of the contract
    /// @return The address of the current owner
    function owner() external view returns (address);

    /// @notice Returns true if the contract is paused, and false otherwise
    /// @return True if paused, false otherwise
    function paused() external view returns (bool);

    /// @notice Pauses the contract
    function pause() external;

    /// @notice Unpauses the contract
    function unpause() external;

    // --- State Getters --- //

    /// @notice Get the current Merkle root
    /// @return The current Merkle root
    function getMerkleRoot() external view returns (BN254.ScalarField);

    /// @notice Check whether a root is in the Merkle root history
    /// @param root The root to check
    /// @return Whether the root is in the history
    function rootInHistory(BN254.ScalarField root) external view returns (bool);

    /// @notice Check whether a nullifier has been spent
    /// @param nullifier The nullifier to check
    /// @return Whether the nullifier has been spent
    function nullifierSpent(BN254.ScalarField nullifier) external view returns (bool);

    /// @notice Check whether a public blinder has been used
    /// @param publicBlinder The public blinder to check
    /// @return Whether the public blinder has been used
    function publicBlinderUsed(BN254.ScalarField publicBlinder) external view returns (bool);

    /// @notice Get the protocol fee rate
    /// @return The protocol fee rate
    function getProtocolFee() external view returns (uint256);

    /// @notice Get the public encryption key for the protocol's fees
    /// @return The public encryption key for the protocol's fees
    function getProtocolFeeKey() external view returns (EncryptionKey memory);

    /// @notice Get the protocol fee rate for a given asset
    /// @dev This fee only applies to external matches
    /// @param asset The asset to get the protocol fee rate for
    /// @return The protocol fee rate for the asset
    function getTokenExternalMatchFeeRate(address asset) external view returns (uint256);

    // --- State Variables --- //

    /// @notice The protocol fee rate for the darkpool
    /// @return The protocol fee rate as a fixed-point number
    function protocolFeeRate() external view returns (uint256);

    /// @notice The address at which external parties pay protocol fees
    /// @return The protocol fee recipient address
    function protocolFeeRecipient() external view returns (address);

    /// @notice The public encryption key for the protocol's fees
    /// @return The protocol fee encryption key
    function protocolFeeKey() external view returns (EncryptionKey memory);

    /// @notice A per-asset fee override for the darkpool
    /// @param asset The token address to query
    /// @return The fee override for the given asset
    function perTokenFeeOverrides(address asset) external view returns (uint256);

    /// @notice The hasher for the darkpool
    /// @return The hasher contract instance
    function hasher() external view returns (IHasher);

    /// @notice The verifier for the darkpool
    /// @return The verifier contract instance
    function verifier() external view returns (IVerifier);

    /// @notice The Permit2 contract instance for handling deposits
    /// @return The Permit2 contract instance
    function permit2() external view returns (IPermit2);

    /// @notice The WETH9 contract instance used for depositing/withdrawing native tokens
    /// @return The WETH9 contract instance
    function weth() external view returns (IWETH9);

    // --- State Setters --- //

    /// @notice Set the protocol fee rate
    /// @param newFee The new protocol fee rate to set
    function setProtocolFeeRate(uint256 newFee) external;

    /// @notice Set the protocol fee rate for a given asset
    /// @param asset The asset to set the protocol fee rate for
    /// @param fee The protocol fee rate to set. This is a fixed point representation
    /// @dev of a real number between 0 and 1. To convert to its floating point representation,
    /// @dev divide by the fixed point precision, i.e. `fee = assetFeeRate / FIXED_POINT_PRECISION`.
    function setTokenExternalMatchFeeRate(address asset, uint256 fee) external;

    /// @notice Remove the fee override for an asset
    /// @param asset The asset to remove the fee override for
    function removeTokenExternalMatchFeeRate(address asset) external;

    /// @notice Set the protocol public encryption key
    /// @param newPubkeyX The new X coordinate of the public key
    /// @param newPubkeyY The new Y coordinate of the public key
    function setProtocolFeeKey(uint256 newPubkeyX, uint256 newPubkeyY) external;

    /// @notice Set the protocol external fee collection address
    /// @param newAddress The new address to collect external fees
    function setProtocolFeeRecipient(address newAddress) external;

    /// @notice Get the protocol fee recipient address
    /// @notice This is the address to which external match fees are sent for the protocol
    /// @return The protocol fee recipient address
    function getProtocolFeeRecipient() external view returns (address);

    // --- Core Wallet Methods --- //

    /// @notice Create a wallet in the darkpool
    /// @param statement The statement to verify
    /// @param proof The proof of `VALID WALLET CREATE`
    function createWallet(ValidWalletCreateStatement calldata statement, PlonkProof calldata proof) external;

    /// @notice Update a wallet in the darkpool
    /// @param newSharesCommitmentSig The signature of the new wallet shares commitment by the
    /// old wallet's root key
    /// @param transferAuthorization The authorization for any external transfer in the update
    /// @param statement The statement to verify
    /// @param proof The proof of `VALID WALLET UPDATE`
    function updateWallet(
        bytes calldata newSharesCommitmentSig,
        TransferAuthorization calldata transferAuthorization,
        ValidWalletUpdateStatement calldata statement,
        PlonkProof calldata proof
    )
        external;

    /// @notice Settle a match in the darkpool
    /// @param party0MatchPayload The validity proofs payload for the first party
    /// @param party1MatchPayload The validity proofs payload for the second party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE`
    /// @param proofs The proofs for the match, including two sets of validity proofs and a settlement proof
    /// @param linkingProofs The proof-linking arguments for the match
    function processMatchSettle(
        PartyMatchPayload calldata party0MatchPayload,
        PartyMatchPayload calldata party1MatchPayload,
        ValidMatchSettleStatement calldata matchSettleStatement,
        MatchProofs calldata proofs,
        MatchLinkingProofs calldata linkingProofs
    )
        external;

    /// @notice Process an atomic match with a non-sender receiver specified
    /// @dev The receiver will receive the buy side token amount implied by the match
    /// @dev net of fees by the relayer and protocol
    /// @param receiver The address that will receive the buy side token amount implied by the match
    /// @param internalPartyPayload The validity proofs for the internal party
    /// @param matchSettleStatement The statement (public inputs) of `VALID MATCH SETTLE`
    /// @param proofs The proofs for the match
    /// @param linkingProofs The proof-linking arguments for the match
    /// @return The amount of the buy token that the external party receives
    function processAtomicMatchSettle(
        address receiver,
        PartyMatchPayload calldata internalPartyPayload,
        ValidMatchSettleAtomicStatement calldata matchSettleStatement,
        MatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        payable
        returns (uint256);

    /// @notice Process a malleable match settlement between two parties
    /// @dev This is a variant of `processAtomicMatchSettle` that allows the match amount to be determined
    /// @dev after the proof is generated. This is done by the prover constraining a valid range for the match
    /// @dev amount, allowing the tx sender to choose any value in this range.
    /// @dev The darkpool then uses the price specified in the statement to determine the quote amount and fees
    /// @dev for the match, then settles the obligations to both the internal and external parties
    /// @param quoteAmount The quote amount of the match, resolving in between the bounds
    /// @param baseAmount The base amount of the match, resolving in between the bounds
    /// @param receiver The address that will receive the buy side token amount for the external party
    /// @param internalPartyPayload The validity proofs for the internal party
    /// @param matchSettleStatement The statement (public inputs) of `VALID MATCH SETTLE`
    /// @param proofs The proofs for the match
    /// @param linkingProofs The proof-linking arguments for the match
    /// @return The amount of the buy token that the external party receives
    function processMalleableAtomicMatchSettle(
        uint256 quoteAmount,
        uint256 baseAmount,
        address receiver,
        PartyMatchPayload calldata internalPartyPayload,
        ValidMalleableMatchSettleAtomicStatement calldata matchSettleStatement,
        MalleableMatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        payable
        returns (uint256);

    /// @notice Process a match settlement between two parties with commitments
    /// @notice This method is currently disabled on the darkpool, but left in the ABI so that tests compile
    /// @param party0MatchPayload The validity proofs payload for the first party
    /// @param party1MatchPayload The validity proofs payload for the second party
    /// @param matchSettleStatement The statement of `VALID MATCH SETTLE WITH COMMITMENTS`
    /// @param proofs The proofs for the match
    /// @param linkingProofs The proof-linking arguments for the match
    function processMatchSettleWithCommitments(
        PartyMatchPayload calldata party0MatchPayload,
        PartyMatchPayload calldata party1MatchPayload,
        ValidMatchSettleWithCommitmentsStatement calldata matchSettleStatement,
        MatchProofs calldata proofs,
        MatchLinkingProofs calldata linkingProofs
    )
        external;

    /// @notice Process an atomic match settlement between two parties with commitments; one internal and one external
    /// @notice This method is currently disabled on the darkpool, but left in the ABI so that tests compile
    /// @dev An internal party is one with state committed into the darkpool, while
    /// @dev an external party provides liquidity to the pool during the
    /// @dev transaction in which this method is called
    /// @dev The receiver of the match settlement is the sender of the transaction
    /// @dev This variant allows the receiver to be specified as a parameter
    /// @param receiver The address that will receive the buy side token amount for the external party
    /// @param internalPartyPayload The validity proofs for the internal party
    /// @param matchSettleStatement The statement (public inputs) of `VALID MATCH SETTLE WITH COMMITMENTS`
    /// @param proofs The proofs for the match
    /// @param linkingProofs The proof-linking arguments for the match
    function processAtomicMatchSettleWithCommitments(
        address receiver,
        PartyMatchPayload calldata internalPartyPayload,
        ValidMatchSettleAtomicWithCommitmentsStatement calldata matchSettleStatement,
        MatchAtomicProofs calldata proofs,
        MatchAtomicLinkingProofs calldata linkingProofs
    )
        external
        payable;

    /// @notice Settle a fee due to the protocol or a relayer offline, i.e. without updating the recipient's wallet
    /// @dev Instead of updating the recipient's wallet, a `Note` is created that the recipient may later redeem
    /// @param statement The statement of `VALID OFFLINE FEE SETTLEMENT`
    /// @param proof The proof of `VALID OFFLINE FEE SETTLEMENT`
    function settleOfflineFee(
        ValidOfflineFeeSettlementStatement calldata statement,
        PlonkProof calldata proof
    )
        external
        payable;

    /// @notice Redeem a fee that has been paid offline into a wallet
    /// @param recipientCommitmentSig The signature of the recipient's wallet commitment
    /// @param statement The statement of `VALID FEE REDEMPTION`
    /// @param proof The proof of `VALID FEE REDEMPTION`
    function redeemFee(
        bytes calldata recipientCommitmentSig,
        ValidFeeRedemptionStatement calldata statement,
        PlonkProof calldata proof
    )
        external;
}
