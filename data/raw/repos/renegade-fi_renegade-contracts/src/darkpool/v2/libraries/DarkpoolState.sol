// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { MerkleMountainLib } from "renegade-lib/merkle/MerkleMountain.sol";
import { NullifierLib } from "renegade-lib/NullifierSet.sol";
import { FixedPoint } from "renegade-lib/FixedPoint.sol";
import { FeeRate } from "darkpoolv2-types/Fee.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { EncryptionKey } from "renegade-lib/Ciphertext.sol";

/// @title Darkpool State
/// @notice Storage struct bundling core darkpool state
/// @dev Used to pass storage references as a single parameter
struct DarkpoolState {
    /// @notice The mapping of open public intents
    /// @dev This maps the intent hash to the amount remaining.
    /// @dev An intent hash is a hash of the tuple (executor, intent),
    /// where executor is the address of the party allowed to fill the intent.
    mapping(bytes32 => uint256) openPublicIntents;
    /// @notice A store of spent signature nonces for user updates
    /// @dev This is used to prevent a relayer from submitting the same update twice
    mapping(uint256 => bool) spentNonces;
    /// @notice The default protocol fee rate for the darkpool
    FixedPoint defaultProtocolFeeRate;
    /// @notice The address at which external parties pay protocol fees
    /// @dev This is only used for external parties in atomic matches
    address protocolFeeRecipient;
    /// @notice The public encryption key for the protocol's fees
    EncryptionKey protocolFeeKey;
    /// @notice A per-pair fee override for the darkpool
    /// @dev This is used to set the protocol fee rate for atomic matches on a per-pair basis
    /// @dev Only external match fees are overridden, internal match fees are always the protocol fee rate
    /// @dev Key is keccak256(abi.encodePacked(token0, token1)) where token0 < token1
    mapping(bytes32 => FixedPoint) perPairFeeOverrides;
    /// @notice The Merkle mountain range for state element commitments
    MerkleMountainLib.MerkleMountainRange merkleMountainRange;
    /// @notice The nullifier set for the darkpool
    /// @dev Each time a state element is updated a nullifier is spent.
    /// @dev The nullifier set ensures that a pre-update state element cannot create two separate post-update state
    /// elements in the Merkle state
    /// @dev The nullifier is computed deterministically from the shares of the pre-update state element
    NullifierLib.NullifierSet nullifierSet;
}

/// @title DarkpoolState
/// @author Renegade Eng
/// @notice Library for the darkpool state
library DarkpoolStateLib {
    using MerkleMountainLib for MerkleMountainLib.MerkleMountainRange;
    using NullifierLib for NullifierLib.NullifierSet;

    // --- Errors --- //

    /// @notice Error thrown when a signature nonce has already been spent
    error NonceAlreadySpent();

    // --- Helpers --- //

    /// @notice Compute a consistent key for a trading pair
    /// @param asset0 The first asset in the pair
    /// @param asset1 The second asset in the pair
    /// @return The keccak256 hash of the ordered pair
    /// @dev Ensures consistent ordering so getPair(A, B) == getPair(B, A)
    function _getPairKey(address asset0, address asset1) internal pure returns (bytes32) {
        (address token0, address token1) = asset0 < asset1 ? (asset0, asset1) : (asset1, asset0);
        return keccak256(abi.encodePacked(token0, token1));
    }

    // --- Getters --- //

    /// @notice Get the amount remaining for an open public intent
    /// @param state The darkpool state
    /// @param intentHash The hash of the intent
    /// @return The amount remaining for the intent
    function getOpenIntentAmountRemaining(
        DarkpoolState storage state,
        bytes32 intentHash
    )
        internal
        view
        returns (uint256)
    {
        return state.openPublicIntents[intentHash];
    }

    /// @notice Check if a nullifier has been spent
    /// @param state The darkpool state
    /// @param nullifier The nullifier to check
    /// @return Whether the nullifier has been spent
    function nullifierSpent(DarkpoolState storage state, BN254.ScalarField nullifier) internal view returns (bool) {
        return state.nullifierSet.isSpent(nullifier);
    }

    /// @notice Get the current Merkle root
    /// @param state The darkpool state
    /// @param depth The depth of the Merkle tree to get the root of
    /// @return The current Merkle root
    function getMerkleRoot(DarkpoolState storage state, uint256 depth) internal view returns (BN254.ScalarField) {
        return state.merkleMountainRange.getRoot(depth);
    }

    /// @notice Check if a root is in the Merkle mountain range history
    /// @param state The darkpool state
    /// @param root The root to check
    /// @return Whether the root is in the history
    function rootInHistory(DarkpoolState storage state, BN254.ScalarField root) internal view returns (bool) {
        return state.merkleMountainRange.rootInHistory(root);
    }

    /// @notice Assert that a root is in the Merkle mountain range history
    /// @param state The darkpool state
    /// @param root The root to check
    function assertRootInHistory(DarkpoolState storage state, BN254.ScalarField root) internal view {
        if (!rootInHistory(state, root)) revert IDarkpoolV2.InvalidMerkleRoot();
    }

    /// @notice Get the default protocol fee rate
    /// @param state The darkpool state
    /// @return The default protocol fee rate
    function getDefaultProtocolFeeRate(DarkpoolState storage state) internal view returns (FixedPoint memory) {
        return state.defaultProtocolFeeRate;
    }

    /// @notice Get the protocol fee recipient address
    /// @param state The darkpool state
    /// @return The protocol fee recipient address
    function getProtocolFeeRecipient(DarkpoolState storage state) internal view returns (address) {
        return state.protocolFeeRecipient;
    }

    /// @notice Get the protocol fee encryption key
    /// @param state The darkpool state
    /// @return The protocol fee encryption key
    function getProtocolFeeKey(DarkpoolState storage state) internal view returns (EncryptionKey memory) {
        return state.protocolFeeKey;
    }

    /// @notice Get the protocol fee rate for a trading pair
    /// @param state The darkpool state
    /// @param asset0 The first asset in the trading pair
    /// @param asset1 The second asset in the trading pair
    /// @return The protocol fee rate for the pair, including recipient address
    function getProtocolFeeRate(
        DarkpoolState storage state,
        address asset0,
        address asset1
    )
        internal
        view
        returns (FeeRate memory)
    {
        bytes32 pairKey = _getPairKey(asset0, asset1);
        FixedPoint memory overrideFee = state.perPairFeeOverrides[pairKey];

        // Use per-pair override if set, otherwise use default
        FixedPoint memory rate = overrideFee.repr != 0 ? overrideFee : state.defaultProtocolFeeRate;
        return FeeRate({ rate: rate, recipient: state.protocolFeeRecipient });
    }

    // --- Setters --- //

    /// @notice Set the amount remaining for an open public intent
    /// @param state The darkpool state
    /// @param intentHash The hash of the intent
    /// @param amount The amount remaining for the intent
    function setOpenIntentAmountRemaining(DarkpoolState storage state, bytes32 intentHash, uint256 amount) internal {
        state.openPublicIntents[intentHash] = amount;
    }

    /// @notice Decrement the amount remaining for an open public intent
    /// @param state The darkpool state
    /// @param intentHash The hash of the intent
    /// @param amount The amount to decrement the amount remaining by
    function decrementOpenIntentAmountRemaining(
        DarkpoolState storage state,
        bytes32 intentHash,
        uint256 amount
    )
        internal
    {
        state.openPublicIntents[intentHash] -= amount;
    }

    /// @notice Spend a signature nonce
    /// @param state The darkpool state
    /// @param nonce The nonce to spend
    function spendNonce(DarkpoolState storage state, uint256 nonce) internal {
        if (state.spentNonces[nonce]) revert NonceAlreadySpent();
        state.spentNonces[nonce] = true;
    }

    /// @notice Set the per-pair fee override for a trading pair
    /// @param state The darkpool state
    /// @param asset0 The first asset in the trading pair
    /// @param asset1 The second asset in the trading pair
    /// @param feeRate The fee rate to set for the pair
    function setPerPairFeeOverride(
        DarkpoolState storage state,
        address asset0,
        address asset1,
        FixedPoint memory feeRate
    )
        internal
    {
        bytes32 pairKey = _getPairKey(asset0, asset1);
        state.perPairFeeOverrides[pairKey] = feeRate;
    }

    /// @notice Spend a nullifier
    /// @param state The darkpool state
    /// @param nullifier The nullifier to spend
    function spendNullifier(DarkpoolState storage state, BN254.ScalarField nullifier) internal {
        state.nullifierSet.spend(nullifier);
    }

    /// @notice Insert a leaf into the Merkle mountain range at the given depth
    /// @param state The darkpool state
    /// @param depth The depth at which to insert the leaf
    /// @param leaf The leaf to insert
    /// @param hasher The hasher to use for hashing
    function insertMerkleLeaf(
        DarkpoolState storage state,
        uint256 depth,
        BN254.ScalarField leaf,
        IHasher hasher
    )
        internal
    {
        // TODO: Allow for dynamic Merkle depth
        if (depth != DarkpoolConstants.DEFAULT_MERKLE_DEPTH) {
            revert IDarkpoolV2.InvalidMerkleDepthRequested();
        }
        state.merkleMountainRange.insertLeaf(depth, leaf, hasher);
    }
}
