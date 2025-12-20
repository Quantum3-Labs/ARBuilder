/// SPDX-License-Identifier: Apache
// solhint-disable one-contract-per-file
pragma solidity ^0.8.24;

import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";
import { SignatureWithNonce } from "darkpoolv2-types/settlement/SignatureWithNonce.sol";
import { BoundedMatchResult } from "darkpoolv2-types/BoundedMatchResult.sol";

// --------------------------------------------
// | Bounded Match Result Authorization Types |
// --------------------------------------------

/// @notice Bounded match result authorization payload with signature attached
struct BoundedMatchResultBundle {
    /// @dev The bounded match result authorization permit
    BoundedMatchResultPermit permit;
    /// @dev The signature of the bounded match result by the authorized executor
    SignatureWithNonce executorSignature;
}

/// @notice Bounded match result authorization data
struct BoundedMatchResultPermit {
    /// @dev The bounded match result
    BoundedMatchResult matchResult;
}

/// @title Bounded Match Result Permit Library
/// @author Renegade Eng
/// @notice Library for bounded match result permit operations
library BoundedMatchResultPermitLib {
    /// @notice Compute the hash of a `BoundedMatchResultPermit`
    /// @param permit The `BoundedMatchResultPermit` to compute the hash of
    /// @return The hash of the `BoundedMatchResultPermit`
    function computeHash(BoundedMatchResultPermit memory permit) internal pure returns (bytes32) {
        return EfficientHashLib.hash(abi.encode(permit));
    }
}
