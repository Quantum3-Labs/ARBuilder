// SPDX-License-Identifier: Apache
// solhint-disable one-contract-per-file
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { FixedPoint } from "renegade-lib/FixedPoint.sol";
import { DarkpoolConstants } from "darkpoolv2-lib/Constants.sol";

/// @title Intent
/// @notice Intent is a struct that represents an intent to buy or sell a token
struct Intent {
    /// @dev The token to buy
    address inToken;
    /// @dev The token to sell
    address outToken;
    /// @dev The owner of the intent, an EOA
    address owner;
    /// @dev The minimum price at which a party may settle a partial fill
    /// @dev This is in units of `outToken/inToken`
    FixedPoint minPrice;
    /// @dev The amount of the input token to trade
    uint256 amountIn;
}

/// @title IntentLib
/// @author Renegade Eng
/// @notice Library for operating on intents
library IntentLib {
    /// @notice Validate an intent's internal fields
    /// @param intent The intent to validate
    /// @dev The only fields that need to be validated are the amount and price
    /// All other fields may be set arbitrarily by the owner and are validated only in relation to a settlement
    /// obligation.
    function validate(Intent memory intent) internal pure {
        DarkpoolConstants.validateAmount(intent.amountIn);
        DarkpoolConstants.validatePrice(intent.minPrice);
    }
}

/// @notice A secret share of an intent
/// @dev All fields here are scalars over the BN254 scalar field
struct IntentPublicShare {
    /// @dev The token to buy
    BN254.ScalarField inToken;
    /// @dev The token to sell
    BN254.ScalarField outToken;
    /// @dev The owner of the intent
    BN254.ScalarField owner;
    /// @dev The minimum price at which a party may settle a partial fill
    /// @dev This is in units of `outToken/inToken`
    BN254.ScalarField minPrice;
    /// @dev The amount of the input token to trade
    BN254.ScalarField amountIn;
}

/// @title IntentPublicShareLib
/// @author Renegade Eng
/// @notice Library for operating on intent public shares
library IntentPublicShareLib {
    /// @notice Serialize an intent public share to scalars for the prefix of a match
    /// @dev The prefix here is the fields which don't change in a match.
    /// @param share The intent public share to serialize
    /// @return scalars The serialized intent public share as an array of scalars
    function scalarSerializeMatchPrefix(IntentPublicShare memory share)
        internal
        pure
        returns (uint256[] memory scalars)
    {
        scalars = new uint256[](4);
        scalars[0] = BN254.ScalarField.unwrap(share.inToken);
        scalars[1] = BN254.ScalarField.unwrap(share.outToken);
        scalars[2] = BN254.ScalarField.unwrap(share.owner);
        scalars[3] = BN254.ScalarField.unwrap(share.minPrice);
    }

    /// @notice Serialize an intent public share to scalars
    /// @dev Serializes all fields of the intent public share
    /// @param share The intent public share to serialize
    /// @return scalars The serialized intent public share as an array of scalars
    function scalarSerialize(IntentPublicShare memory share) internal pure returns (uint256[] memory scalars) {
        scalars = new uint256[](5);
        scalars[0] = BN254.ScalarField.unwrap(share.inToken);
        scalars[1] = BN254.ScalarField.unwrap(share.outToken);
        scalars[2] = BN254.ScalarField.unwrap(share.owner);
        scalars[3] = BN254.ScalarField.unwrap(share.minPrice);
        scalars[4] = BN254.ScalarField.unwrap(share.amountIn);
    }
}

/// @notice A pre-match share of an intent
/// @dev This is a secret share of all fields in an intent which don't change in a match
/// @dev That is, all but the `amountIn` field.
struct IntentPreMatchShare {
    /// @dev The token to buy
    BN254.ScalarField inToken;
    /// @dev The token to sell
    BN254.ScalarField outToken;
    /// @dev The owner of the intent
    BN254.ScalarField owner;
    /// @dev The minimum price at which a party may settle a partial fill
    /// @dev This is in units of `outToken/inToken`
    BN254.ScalarField minPrice;
}

/// @title IntentPreMatchShareLib
/// @author Renegade Eng
/// @notice Library for operating on pre-match intent shares
library IntentPreMatchShareLib {
    /// @notice Create an intent public share from a pre-match share and an `amountIn` share
    /// @param preMatchShare The pre-match share to create the intent public share from
    /// @param amountInShare The `amountIn` share to create the intent public share from
    /// @return intentPublicShare The intent public share
    function toFullPublicShare(
        IntentPreMatchShare memory preMatchShare,
        BN254.ScalarField amountInShare
    )
        internal
        pure
        returns (IntentPublicShare memory intentPublicShare)
    {
        intentPublicShare = IntentPublicShare({
            inToken: preMatchShare.inToken,
            outToken: preMatchShare.outToken,
            owner: preMatchShare.owner,
            minPrice: preMatchShare.minPrice,
            amountIn: amountInShare
        });
    }
}
