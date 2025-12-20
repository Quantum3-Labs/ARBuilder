// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/* solhint-disable func-named-parameters */
/* solhint-disable use-natspec */

import { SettlementBundle, SettlementBundleType, PartyId } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import { PublicIntentPublicBalanceBundle } from "darkpoolv2-types/settlement/SettlementBundle.sol";
import {
    RenegadeSettledPrivateFirstFillBundle,
    RenegadeSettledPrivateFillBundle
} from "darkpoolv2-lib/settlement/bundles/RenegadeSettledPrivateFillLib.sol";
import {
    PrivateIntentPublicBalanceFirstFillBundle,
    PrivateIntentPublicBalanceBundle
} from "darkpoolv2-lib/settlement/bundles/PrivateIntentPublicBalanceBundleLib.sol";
import {
    RenegadeSettledIntentFirstFillBundle,
    RenegadeSettledIntentBundle
} from "darkpoolv2-lib/settlement/bundles/PrivateIntentPrivateBalanceBundleLib.sol";
import {
    PublicIntentAuthBundle,
    PublicIntentPermit,
    PrivateIntentAuthBundleFirstFill,
    PrivateIntentAuthBundle,
    RenegadeSettledIntentAuthBundleFirstFill,
    RenegadeSettledIntentAuthBundle,
    SignatureWithNonce
} from "darkpoolv2-types/settlement/IntentBundle.sol";
import {
    ObligationBundle, ObligationType, PrivateObligationBundle
} from "darkpoolv2-types/settlement/ObligationBundle.sol";
import {
    OutputBalanceBundle,
    OutputBalanceBundleType,
    ExistingBalanceBundle,
    NewBalanceBundle
} from "darkpoolv2-types/settlement/OutputBalanceBundle.sol";
import { SettlementContext } from "darkpoolv2-types/settlement/SettlementContext.sol";

/// @title ISettlementTypes
/// @author Renegade Eng
/// @notice Interface exposing all settlement types for ABI generation
/// @dev This interface is used solely for generating ABIs for Rust bindings.
///      All functions are intentionally empty/unimplemented.
interface ISettlementTypes {
    // SettlementBundle types
    function exposeSettlementBundle(SettlementBundle calldata) external pure returns (SettlementBundle memory);
    function exposeSettlementBundleType(SettlementBundleType) external pure returns (SettlementBundleType);
    function exposePartyId(PartyId) external pure returns (PartyId);

    // Settlement bundle data types
    function exposePublicIntentPublicBalanceBundle(PublicIntentPublicBalanceBundle calldata)
        external
        pure
        returns (PublicIntentPublicBalanceBundle memory);
    function exposePrivateIntentPublicBalanceFirstFillBundle(PrivateIntentPublicBalanceFirstFillBundle calldata)
        external
        pure
        returns (PrivateIntentPublicBalanceFirstFillBundle memory);
    function exposePrivateIntentPublicBalanceBundle(PrivateIntentPublicBalanceBundle calldata)
        external
        pure
        returns (PrivateIntentPublicBalanceBundle memory);
    function exposeRenegadeSettledIntentFirstFillBundle(RenegadeSettledIntentFirstFillBundle calldata)
        external
        pure
        returns (RenegadeSettledIntentFirstFillBundle memory);
    function exposeRenegadeSettledIntentBundle(RenegadeSettledIntentBundle calldata)
        external
        pure
        returns (RenegadeSettledIntentBundle memory);
    function exposeRenegadeSettledPrivateFirstFillBundle(RenegadeSettledPrivateFirstFillBundle calldata)
        external
        pure
        returns (RenegadeSettledPrivateFirstFillBundle memory);
    function exposeRenegadeSettledPrivateFillBundle(RenegadeSettledPrivateFillBundle calldata)
        external
        pure
        returns (RenegadeSettledPrivateFillBundle memory);

    // Intent bundle types
    function exposePublicIntentAuthBundle(PublicIntentAuthBundle calldata)
        external
        pure
        returns (PublicIntentAuthBundle memory);
    function exposePublicIntentPermit(PublicIntentPermit calldata) external pure returns (PublicIntentPermit memory);
    function exposePrivateIntentAuthBundleFirstFill(PrivateIntentAuthBundleFirstFill calldata)
        external
        pure
        returns (PrivateIntentAuthBundleFirstFill memory);
    function exposePrivateIntentAuthBundle(PrivateIntentAuthBundle calldata)
        external
        pure
        returns (PrivateIntentAuthBundle memory);
    function exposeRenegadeSettledIntentAuthBundleFirstFill(RenegadeSettledIntentAuthBundleFirstFill calldata)
        external
        pure
        returns (RenegadeSettledIntentAuthBundleFirstFill memory);
    function exposeRenegadeSettledIntentAuthBundle(RenegadeSettledIntentAuthBundle calldata)
        external
        pure
        returns (RenegadeSettledIntentAuthBundle memory);
    function exposeSignatureWithNonce(SignatureWithNonce calldata) external pure returns (SignatureWithNonce memory);

    // Obligation bundle types
    function exposeObligationBundle(ObligationBundle calldata) external pure returns (ObligationBundle memory);
    function exposeObligationType(ObligationType) external pure returns (ObligationType);
    function exposePrivateObligationBundle(PrivateObligationBundle calldata)
        external
        pure
        returns (PrivateObligationBundle memory);

    // Output balance bundle types
    function exposeOutputBalanceBundle(OutputBalanceBundle calldata)
        external
        pure
        returns (OutputBalanceBundle memory);
    function exposeOutputBalanceBundleType(OutputBalanceBundleType) external pure returns (OutputBalanceBundleType);
    function exposeExistingBalanceBundle(ExistingBalanceBundle calldata)
        external
        pure
        returns (ExistingBalanceBundle memory);
    function exposeNewBalanceBundle(NewBalanceBundle calldata) external pure returns (NewBalanceBundle memory);

    // Settlement context types
    function exposeSettlementContext(SettlementContext calldata) external pure returns (SettlementContext memory);
}
