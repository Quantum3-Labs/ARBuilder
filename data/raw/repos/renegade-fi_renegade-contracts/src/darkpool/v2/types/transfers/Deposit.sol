// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { EfficientHashLib } from "solady/utils/EfficientHashLib.sol";

/// @dev The type hash for the DepositWitness struct
// solhint-disable-next-line gas-small-strings
bytes32 constant DEPOSIT_WITNESS_TYPEHASH = keccak256("DepositWitness(uint256 newBalanceCommitment)");
/// @dev The type string for the DepositWitness struct
/// @dev We must include the `TokenPermission` type encoding as well as this is concatenated with
/// @dev the `PermitWitnessTransferFrom` type encoding stub of the form:
/// @dev `PermitWitnessTransferFrom(TokenPermissions permitted,address spender,uint256 nonce,uint256 deadline,`
/// @dev So we must prepare our type string to concatenate to the entire type encoding
/// @dev See:
/// https://github.com/Uniswap/permit2/blob/cc56ad0f3439c502c246fc5cfcc3db92bb8b7219/src/libraries/PermitHash.sol#L31-L32
// solhint-disable-next-line gas-small-strings
string constant DEPOSIT_WITNESS_TYPE_STRING =
    "DepositWitness witness)DepositWitness(uint256 newBalanceCommitment)TokenPermissions(address token,uint256 amount)";

/// @notice A deposit into a balance in the darkpool
/// @dev A deposit transfer directly into a user's Merklized balance
/// @dev As opposed to a simple transfer, this transfer type requires a user to sign a Permit2 witness transfer permit
/// in order to authorize its execution.
struct Deposit {
    /// @dev The address from which to deposit
    address from;
    /// @dev The token to deposit
    address token;
    /// @dev The amount to deposit
    uint256 amount;
}

/// @notice The authorization for a deposit
/// @dev This authorizes a Permit2 witness transfer [see
/// here](https://github.com/Uniswap/permit2/blob/main/src/SignatureTransfer.sol#L32)
/// @dev The witness is the commitment to the updated balance element after the deposit is executed.
struct DepositAuth {
    /// @dev The nonce of the permit
    uint256 permit2Nonce;
    /// @dev The deadline of the permit
    uint256 permit2Deadline;
    /// @dev The signature of the permit
    bytes permit2Signature;
}

/// @notice The witness for a deposit
/// @dev The witness is the commitment to the updated balance element after the deposit is executed.
struct DepositWitness {
    /// @dev The commitment to the updated balance element after the deposit is executed
    uint256 newBalanceCommitment;
}

/// @title DepositLib
/// @author Renegade Eng
/// @notice Library for deposit-related operations
library DepositLib {
    /// @notice Hash a deposit witness for permit2 signature transfer
    /// @param witness The deposit witness to hash
    /// @return The hash of the deposit witness
    function hashWitness(DepositWitness memory witness) internal pure returns (bytes32) {
        return EfficientHashLib.hash(DEPOSIT_WITNESS_TYPEHASH, bytes32(witness.newBalanceCommitment));
    }
}
