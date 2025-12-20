// SPDX-License-Identifier: Apache
pragma solidity ^0.8.24;

import { PlonkProof, LinkingProof, VerificationKey } from "renegade-lib/verifier/Types.sol";
import {
    OutputBalanceValidityStatement,
    NewOutputBalanceValidityStatement
} from "darkpoolv2-lib/public_inputs/ValidityProofs.sol";
import { IDarkpoolV2 } from "darkpoolv2-interfaces/IDarkpoolV2.sol";
import { IVkeys } from "darkpoolv2-interfaces/IVkeys.sol";
import { BN254 } from "solidity-bn254/BN254.sol";

// ------------------------
// | Output Balance Types |
// ------------------------

/// @notice The output balance bundle for a user
/// @dev This type encapsulates the authorization data for use of a balance as the output of a trade.
struct OutputBalanceBundle {
    /// @dev The Merkle depth at which to update the balance
    uint256 merkleDepth;
    /// @dev The type of output balance bundle
    OutputBalanceBundleType bundleType;
    /// @dev The data validating the output balance bundle
    bytes data;
    /// @dev The plonk proof of output balance validity
    PlonkProof proof;
    /// @dev The proof linking argument between the output balance validity proof and the settlement proof
    LinkingProof settlementLinkingProof;
}

/// @notice The type of output balance bundle
/// @dev There are two types of output balance bundles:
/// 1. EXISTING_BALANCE: A bundle representing a balance that already exists in the Merkle tree.
/// 2. NEW_BALANCE: A bundle representing a new balance that is created as part of the settlement.
enum OutputBalanceBundleType {
    EXISTING_BALANCE,
    NEW_BALANCE
}

/// @notice The verification data for an existing balance bundle
struct ExistingBalanceBundle {
    /// @dev The statement for the balance validity proof
    OutputBalanceValidityStatement statement;
}

/// @notice The verification data for a new balance bundle
struct NewBalanceBundle {
    /// @dev The statement for the balance creation proof
    NewOutputBalanceValidityStatement statement;
}

/// @title Output Balance Bundle Library
/// @author Renegade Eng
/// @notice Library for decoding output balance bundle data
library OutputBalanceBundleLib {
    /// @notice Decode an existing balance bundle
    /// @param bundle The output balance bundle to decode
    /// @return bundleData The decoded bundle data
    function decodeExistingBalanceBundle(OutputBalanceBundle memory bundle)
        internal
        pure
        returns (ExistingBalanceBundle memory bundleData)
    {
        bool validType = bundle.bundleType == OutputBalanceBundleType.EXISTING_BALANCE;
        require(validType, IDarkpoolV2.InvalidOutputBalanceBundleType());
        bundleData = abi.decode(bundle.data, (ExistingBalanceBundle));
    }

    /// @notice Decode a new balance bundle
    /// @param bundle The output balance bundle to decode
    /// @return bundleData The decoded bundle data
    function decodeNewBalanceBundle(OutputBalanceBundle memory bundle)
        internal
        pure
        returns (NewBalanceBundle memory bundleData)
    {
        bool validType = bundle.bundleType == OutputBalanceBundleType.NEW_BALANCE;
        require(validType, IDarkpoolV2.InvalidOutputBalanceBundleType());
        bundleData = abi.decode(bundle.data, (NewBalanceBundle));
    }
}
