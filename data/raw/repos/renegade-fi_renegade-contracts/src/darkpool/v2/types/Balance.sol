// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";

/// @title Pre-match balance share
/// @notice A pre-match balance share is a share of the balance without the `amount` or fees fields.
/// @dev We use this type to represent balances whose `amount` or fees fields are determined in a later circuit
/// within a proof-linked chain of circuits. For example, we may leak a `PreMatchBalanceShare` in a validity circuit
/// and separately leak the `amount` or fees fields thereafter.
struct PreMatchBalanceShare {
    /// @dev The mint of the token in the balance
    BN254.ScalarField mint;
    /// @dev The owner of the balance
    BN254.ScalarField owner;
    /// @dev The relayer fee recipient of the balance
    BN254.ScalarField relayerFeeRecipient;
    /// @dev The one-time authority of the balance
    BN254.ScalarField oneTimeAuthority;
}

/// @title Post-match balance share
/// @notice A post-match balance share is a share of the balance containing only the fields which change in a match.
/// @dev That is, the fee and amount fields.
struct PostMatchBalanceShare {
    /// @dev The relayer fee balance of the balance
    BN254.ScalarField relayerFeeBalance;
    /// @dev The protocol fee balance of the balance
    BN254.ScalarField protocolFeeBalance;
    /// @dev The amount of the token in the balance
    BN254.ScalarField amount;
}

/// @title Post-match balance share library
/// @notice Library for post-match balance shares
library PostMatchBalanceShareLib {
    /// @notice Serialize a post-match balance share to scalars
    /// @param share The post-match balance share to serialize
    /// @return scalars The serialized post-match balance share as an array of scalars
    function scalarSerialize(PostMatchBalanceShare memory share) internal pure returns (uint256[] memory scalars) {
        scalars = new uint256[](3);
        scalars[0] = BN254.ScalarField.unwrap(share.relayerFeeBalance);
        scalars[1] = BN254.ScalarField.unwrap(share.protocolFeeBalance);
        scalars[2] = BN254.ScalarField.unwrap(share.amount);
    }
}
