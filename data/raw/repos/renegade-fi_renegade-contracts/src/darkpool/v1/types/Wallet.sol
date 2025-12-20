// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

/* solhint-disable gas-increment-by-one */

import { BN254 } from "solidity-bn254/BN254.sol";
import { FixedPoint } from "renegade-lib/FixedPoint.sol";
import { PublicKeychain } from "darkpoolv1-types/Keychain.sol";
import { EncryptionKey } from "renegade-lib/Ciphertext.sol";

// This file contains types for operating on wallet shares

/// @dev The maximum number of orders in a wallet
uint256 constant MAX_ORDERS = 4;
/// @dev The maximum number of balances in a wallet
uint256 constant MAX_BALANCES = 10;
/// @dev The number of scalars in a serialized wallet share
uint256 constant NUM_WALLET_SCALARS = 70;

/// @title WalletShare
/// @notice A public secret share of a wallet
struct WalletShare {
    /// @dev The list of balances in the wallet
    BalanceShare[MAX_BALANCES] balances;
    /// @dev The list of orders in the wallet
    OrderShare[MAX_ORDERS] orders;
    /// @dev The keychain of the wallet
    PublicKeychain keychain;
    /// @dev The maximum match fee that the user is willing to pay for a match
    FixedPoint maxMatchFee;
    /// @dev The public key of the cluster that the wallet has authorized to collect match fees
    EncryptionKey managingCluster;
    /// @dev The public share of the wallet's blinder
    BN254.ScalarField blinder;
}

/// @title BalanceShare
/// @notice A balance in the wallet
/// @dev Note that the share type uses scalars for all entries, as this type represents a
/// @dev additive secret share of a balance over the BN254 scalar field
struct BalanceShare {
    /// @dev The address of the token
    BN254.ScalarField token;
    /// @dev The amount of the balance
    BN254.ScalarField amount;
    /// @dev The amount of the balance owed to the managing relayer cluster
    BN254.ScalarField relayerFeeBalance;
    /// @dev The amount of the balance owed to the protocol
    BN254.ScalarField protocolFeeBalance;
}

/// @title OrderShare
/// @notice An order in the wallet
/// @dev Note that the share type uses scalars for all entries, as this type represents a
/// @dev additive secret share of an order over the BN254 scalar field
struct OrderShare {
    /// @dev The address of the quote mint
    BN254.ScalarField quoteMint;
    /// @dev The address of the base mint
    BN254.ScalarField baseMint;
    /// @dev The direction of the order
    BN254.ScalarField side;
    /// @dev The amount of the order
    BN254.ScalarField amount;
    /// @dev The worst case price that the user is willing to accept on this order
    /// @dev If the order is a buy, this is the maximum price the user is willing to
    /// @dev pay. If the order is a sell, this is the minimum price the user is
    /// @dev willing to accept
    FixedPoint worstCasePrice;
}

/// @title WalletLib
/// @author Renegade Eng
/// @notice A library for operating on wallets
library WalletLib {
    /// @notice Serialize a wallet share into a list of scalars
    /// @param wallet The wallet to serialize
    /// @return scalars The serialized wallet as a list of scalar field elements
    function scalarSerialize(WalletShare memory wallet) internal pure returns (BN254.ScalarField[] memory scalars) {
        scalars = new BN254.ScalarField[](NUM_WALLET_SCALARS);

        // Serialize the balances
        uint256 offset = 0;
        for (uint256 i = 0; i < MAX_BALANCES; ++i) {
            scalars[offset++] = wallet.balances[i].token;
            scalars[offset++] = wallet.balances[i].amount;
            scalars[offset++] = wallet.balances[i].relayerFeeBalance;
            scalars[offset++] = wallet.balances[i].protocolFeeBalance;
        }

        // Serialize the orders
        for (uint256 i = 0; i < MAX_ORDERS; ++i) {
            scalars[offset++] = wallet.orders[i].quoteMint;
            scalars[offset++] = wallet.orders[i].baseMint;
            scalars[offset++] = wallet.orders[i].side;
            scalars[offset++] = wallet.orders[i].amount;
            scalars[offset++] = BN254.ScalarField.wrap(wallet.orders[i].worstCasePrice.repr);
        }

        // Serialize the keychain
        scalars[offset++] = wallet.keychain.pkRoot.x[0];
        scalars[offset++] = wallet.keychain.pkRoot.x[1];
        scalars[offset++] = wallet.keychain.pkRoot.y[0];
        scalars[offset++] = wallet.keychain.pkRoot.y[1];
        scalars[offset++] = wallet.keychain.pkMatch.key;
        scalars[offset++] = wallet.keychain.nonce;

        // Serialize the max match fee
        scalars[offset++] = BN254.ScalarField.wrap(wallet.maxMatchFee.repr);

        // Serialize the managing cluster
        scalars[offset++] = wallet.managingCluster.point.x;
        scalars[offset++] = wallet.managingCluster.point.y;

        // Serialize the blinder
        scalars[offset++] = wallet.blinder;
    }

    /// @notice Deserialize a wallet share from a list of scalars
    /// @param scalars The serialized wallet
    /// @return wallet The deserialized wallet
    function scalarDeserialize(BN254.ScalarField[] memory scalars) internal pure returns (WalletShare memory wallet) {
        uint256 offset = 0;

        // Deserialize the balances
        for (uint256 i = 0; i < MAX_BALANCES; ++i) {
            wallet.balances[i].token = scalars[offset++];
            wallet.balances[i].amount = scalars[offset++];
            wallet.balances[i].relayerFeeBalance = scalars[offset++];
            wallet.balances[i].protocolFeeBalance = scalars[offset++];
        }

        // Deserialize the orders
        for (uint256 i = 0; i < MAX_ORDERS; ++i) {
            wallet.orders[i].quoteMint = scalars[offset++];
            wallet.orders[i].baseMint = scalars[offset++];
            wallet.orders[i].side = scalars[offset++];
            wallet.orders[i].amount = scalars[offset++];
            wallet.orders[i].worstCasePrice = FixedPoint({ repr: BN254.ScalarField.unwrap(scalars[offset++]) });
        }

        // Deserialize the keychain
        wallet.keychain.pkRoot.x[0] = scalars[offset++];
        wallet.keychain.pkRoot.x[1] = scalars[offset++];
        wallet.keychain.pkRoot.y[0] = scalars[offset++];
        wallet.keychain.pkRoot.y[1] = scalars[offset++];
        wallet.keychain.pkMatch.key = scalars[offset++];
        wallet.keychain.nonce = scalars[offset++];

        // Deserialize the max match fee
        wallet.maxMatchFee = FixedPoint({ repr: BN254.ScalarField.unwrap(scalars[offset++]) });

        // Deserialize the managing cluster
        wallet.managingCluster.point.x = scalars[offset++];
        wallet.managingCluster.point.y = scalars[offset++];

        // Deserialize the blinder
        wallet.blinder = scalars[offset++];
    }
}
