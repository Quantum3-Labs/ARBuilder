// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { PublicRootKey } from "darkpoolv1-types/Keychain.sol";
import { IHasher } from "renegade-lib/interfaces/IHasher.sol";
import { MerkleTreeLib } from "renegade-lib/merkle/MerkleTree.sol";
import { NullifierLib } from "renegade-lib/NullifierSet.sol";
import { WalletShare, WalletLib } from "darkpoolv1-types/Wallet.sol";
import { ExternalMatchResult, OrderSettlementIndices } from "darkpoolv1-types/Settlement.sol";
import { FeeTakeRate, FeeTake } from "darkpoolv1-types/Fees.sol";
import { BalanceShare } from "darkpoolv1-types/Wallet.sol";
import { TypesLib } from "darkpoolv1-types/TypesLib.sol";
import { IDarkpool } from "darkpoolv1-interfaces/IDarkpool.sol";
import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { ECDSALib } from "renegade-lib/ECDSA.sol";

// --- Helpers --- //

/// @notice Create a uint256 from a pair of BN254.ScalarField words, in little-endian order
/// @param low The low word
/// @param high The high word
/// @return The uint256 value
function scalarWordsToUint(BN254.ScalarField low, BN254.ScalarField high) pure returns (uint256) {
    return BN254.ScalarField.unwrap(low) + (BN254.ScalarField.unwrap(high) * BN254.R_MOD);
}

/// @notice Split a uint256 into a pair of BN254.ScalarField words, in little-endian order
/// @param value The uint256 value to split
/// @return low The low word
/// @return high The high word
function uintToScalarWords(uint256 value) pure returns (BN254.ScalarField low, BN254.ScalarField high) {
    low = BN254.ScalarField.wrap(value % BN254.R_MOD);
    high = BN254.ScalarField.wrap(value / BN254.R_MOD);
}

// --- Library --- //

/// @title WalletOperations
/// @author Renegade Eng
/// @notice Library for wallet operations including rotation, nullifier spending, and signature verification
library WalletOperations {
    /// @notice Error thrown when Merkle root is not in history
    error MerkleRootNotInHistory();
    /// @notice Error thrown when note is not in Merkle history
    error NoteNotInMerkleHistory();
    /// @notice Error thrown when signature length is invalid
    error InvalidSignatureLength();
    /// @notice Error thrown when signature is invalid
    error InvalidSignature();

    using NullifierLib for NullifierLib.NullifierSet;
    using MerkleTreeLib for MerkleTreeLib.MerkleTree;
    using WalletLib for WalletShare;
    using TypesLib for FeeTakeRate;
    using TypesLib for FeeTake;
    using TypesLib for ExternalMatchResult;
    using BN254 for BN254.ScalarField;

    /// @notice Rotate a wallet's shares, nullifying the previous shares and inserting the new shares
    /// @param nullifier The nullifier of the previous wallet's shares
    /// @param historicalMerkleRoot The merkle root to which the previous wallet's share are committed
    /// @param newPrivateShareCommitment The commitment to the new private shares
    /// @param newPublicShares The new shares of the wallet to commit to
    /// @param nullifierSet The set of nullifiers for the darkpool
    /// @param publicBlinderSet The set of public blinders for the darkpool
    /// @param merkleTree The merkle tree for the darkpool
    /// @param hasher The hasher for the darkpool
    /// @return newCommitment The commitment to the new wallet shares
    function rotateWallet(
        BN254.ScalarField nullifier,
        BN254.ScalarField historicalMerkleRoot,
        BN254.ScalarField newPrivateShareCommitment,
        BN254.ScalarField[] memory newPublicShares,
        NullifierLib.NullifierSet storage nullifierSet,
        NullifierLib.NullifierSet storage publicBlinderSet,
        MerkleTreeLib.MerkleTree storage merkleTree,
        IHasher hasher
    )
        internal
        returns (BN254.ScalarField newCommitment)
    {
        // Compute the wallet commitment from the shares
        newCommitment = computeWalletCommitment(newPrivateShareCommitment, newPublicShares, hasher);
        rotateWalletWithCommitment(
            nullifier,
            historicalMerkleRoot,
            newCommitment,
            newPublicShares,
            nullifierSet,
            publicBlinderSet,
            merkleTree,
            hasher
        );
    }

    /// @notice Rotate a wallet given a commitment to the new shares directly
    /// @dev Using this method, the contract does not need to hash the public shares to generate
    /// a wallet commitment
    /// @param nullifier The nullifier of the previous wallet's shares
    /// @param historicalMerkleRoot The merkle root to which the previous wallet's share are committed
    /// @param newSharesCommitment The commitment to the new shares
    /// @param newPublicShares The new public shares
    /// @param nullifierSet The set of nullifiers for the darkpool
    /// @param publicBlinderSet The set of public blinders for the darkpool
    /// @param merkleTree The merkle tree for the darkpool
    /// @param hasher The hasher for the darkpool
    function rotateWalletWithCommitment(
        BN254.ScalarField nullifier,
        BN254.ScalarField historicalMerkleRoot,
        BN254.ScalarField newSharesCommitment,
        BN254.ScalarField[] memory newPublicShares,
        NullifierLib.NullifierSet storage nullifierSet,
        NullifierLib.NullifierSet storage publicBlinderSet,
        MerkleTreeLib.MerkleTree storage merkleTree,
        IHasher hasher
    )
        internal
    {
        // 1. Nullify the previous wallet's shares
        spendNullifier(nullifier, nullifierSet);

        // 2. Mark the public blinder share as spent
        BN254.ScalarField publicBlinder = newPublicShares[newPublicShares.length - 1];
        markPublicBlinderAsUsed(publicBlinder, publicBlinderSet);

        // 3. Check that the Merkle root is in the historical Merkle roots
        if (!merkleTree.rootInHistory(historicalMerkleRoot)) revert MerkleRootNotInHistory();

        // 4. Insert the new shares into the Merkle tree
        merkleTree.insertLeaf(newSharesCommitment, hasher);
    }

    /// @notice Mark a public blinder as used
    /// @param publicBlinder The public blinder to mark as used
    /// @param publicBlinderSet The set of public blinders for the darkpool
    function markPublicBlinderAsUsed(
        BN254.ScalarField publicBlinder,
        NullifierLib.NullifierSet storage publicBlinderSet
    )
        internal
    {
        publicBlinderSet.spend(publicBlinder);
        emit IDarkpool.WalletUpdated(BN254.ScalarField.unwrap(publicBlinder));
    }

    /// @notice Spend a nullifier
    /// @param nullifier The nullifier to spend
    /// @param nullifierSet The set of nullifiers for the darkpool
    function spendNullifier(BN254.ScalarField nullifier, NullifierLib.NullifierSet storage nullifierSet) internal {
        nullifierSet.spend(nullifier);
        emit IDarkpool.NullifierSpent(nullifier);
    }

    /// @notice Compute a commitment to a wallet's shares
    /// @param privateShareCommitment The commitment to the private shares
    /// @param publicShares The public shares of the wallet
    /// @param hasher The hasher for the darkpool
    /// @return The commitment to the wallet's shares
    function computeWalletCommitment(
        BN254.ScalarField privateShareCommitment,
        BN254.ScalarField[] memory publicShares,
        IHasher hasher
    )
        internal
        view
        returns (BN254.ScalarField)
    {
        uint256[] memory hashInputs = new uint256[](publicShares.length + 1);
        hashInputs[0] = BN254.ScalarField.unwrap(privateShareCommitment);
        for (uint256 i = 1; i < publicShares.length + 1; ++i) {
            hashInputs[i] = BN254.ScalarField.unwrap(publicShares[i - 1]);
        }

        uint256 walletCommitment = hasher.spongeHash(hashInputs);
        return BN254.ScalarField.wrap(walletCommitment);
    }

    /// @notice Spend a note
    /// @dev This involves both checking the note's inclusion root and spending its nullifier
    /// @param noteNullifier The nullifier of the note
    /// @param noteRoot The root of the note
    /// @param nullifierSet The set of nullifiers for the darkpool
    /// @param merkleTree The merkle tree for the darkpool
    function spendNote(
        BN254.ScalarField noteNullifier,
        BN254.ScalarField noteRoot,
        NullifierLib.NullifierSet storage nullifierSet,
        MerkleTreeLib.MerkleTree storage merkleTree
    )
        internal
    {
        // 1. Check that the note is in the Merkle tree
        if (!merkleTree.rootInHistory(noteRoot)) revert NoteNotInMerkleHistory();

        // 2. Spend the note
        spendNullifier(noteNullifier, nullifierSet);
    }

    /// @notice Verify a wallet update signature
    /// @dev The signature is expected in the following format:
    /// @dev r || s || v, for a total of 65 bytes where:
    /// @dev bytes [0:32] = r
    /// @dev bytes [32:64] = s
    /// @dev bytes [64] = v
    /// @param walletCommitment The commitment to the new wallet shares
    /// @param newSharesCommitmentSig The signature of the wallet commitment
    /// @param oldRootKey The public root key used to sign the commitment
    /// @return Whether the signature is valid
    function verifyWalletUpdateSignature(
        BN254.ScalarField walletCommitment,
        bytes calldata newSharesCommitmentSig,
        PublicRootKey memory oldRootKey
    )
        internal
        pure
        returns (bool)
    {
        // 1. Hash the wallet commitment
        bytes32 commitmentHash = walletCommitmentDigest(walletCommitment);

        // 2. Verify the signature
        return verifyRootKeySignature(commitmentHash, newSharesCommitmentSig, oldRootKey);
    }

    /// @notice Verify the root key signature of a digest
    /// @param digest The digest to verify
    /// @param signature The signature to verify
    /// @param rootKey The public root key to verify against
    /// @return Whether the signature is valid
    function verifyRootKeySignature(
        bytes32 digest,
        bytes calldata signature,
        PublicRootKey memory rootKey
    )
        internal
        pure
        returns (bool)
    {
        address rootKeyAddress = addressFromRootKey(rootKey);
        return ECDSALib.verify(digest, signature, rootKeyAddress);
    }

    /// @notice Get the digest of a wallet commitment
    /// @param walletCommitment The wallet commitment to hash
    /// @return The digest of the wallet commitment
    function walletCommitmentDigest(BN254.ScalarField walletCommitment) internal pure returns (bytes32) {
        bytes32 walletCommitmentBytes = bytes32(BN254.ScalarField.unwrap(walletCommitment));
        return EfficientHashLib.hash(abi.encode(walletCommitmentBytes));
    }

    /// @notice Get an ethereum address from a public root key
    /// @param rootKey The public root key to convert
    /// @return The ethereum address derived from the root key
    function addressFromRootKey(PublicRootKey memory rootKey) internal pure returns (address) {
        uint256 x = scalarWordsToUint(rootKey.x[0], rootKey.x[1]);
        uint256 y = scalarWordsToUint(rootKey.y[0], rootKey.y[1]);
        // Pack x and y into 64 bytes
        bytes memory packed = abi.encodePacked(x, y);

        // Hash and convert last 20 bytes to address
        bytes32 hash = EfficientHashLib.hash(packed);
        return address(uint160(uint256(hash)));
    }

    /// @notice Apply an external match to a wallet's public shares
    /// @dev Arithmetic here is safe because the amounts are constrained in-circuit
    /// @param shares The wallet's shares
    /// @param internalPartyFeeRate The fees due on the match
    /// @param matchResult The result of the match
    /// @param indices The order settlement indices to apply the match into
    /// @return The updated wallet shares after applying the match
    function applyExternalMatchToShares(
        BN254.ScalarField[] memory shares,
        FeeTakeRate memory internalPartyFeeRate,
        ExternalMatchResult memory matchResult,
        OrderSettlementIndices memory indices
    )
        internal
        pure
        returns (BN254.ScalarField[] memory)
    {
        // Deserialize the shares into a wallet share type
        WalletShare memory walletShare = WalletLib.scalarDeserialize(shares);

        // Deduct the matched amount from the order's volume
        walletShare.orders[indices.order].amount = walletShare.orders[indices.order].amount.sub(matchResult.baseAmount);

        // Compute the fees owed by the internal party
        (, uint256 recvAmount) = matchResult.externalPartySellMintAmount();
        (, uint256 sendAmount) = matchResult.externalPartyBuyMintAmount();
        FeeTake memory internalPartyFees = internalPartyFeeRate.computeFeeTake(recvAmount);

        // Add the receive amount to the wallet's balances
        uint256 netReceiveAmount = recvAmount - internalPartyFees.total();
        BalanceShare memory recvBal = walletShare.balances[indices.balanceReceive];
        BalanceShare memory sendBal = walletShare.balances[indices.balanceSend];

        recvBal.amount = recvBal.amount.add(netReceiveAmount);
        recvBal.relayerFeeBalance = recvBal.relayerFeeBalance.add(internalPartyFees.relayerFee);
        recvBal.protocolFeeBalance = recvBal.protocolFeeBalance.add(internalPartyFees.protocolFee);

        // Deduct the send amount from the wallet's balances
        sendBal.amount = sendBal.amount.sub(sendAmount);

        // Serialize the updated shares
        return walletShare.scalarSerialize();
    }
}
