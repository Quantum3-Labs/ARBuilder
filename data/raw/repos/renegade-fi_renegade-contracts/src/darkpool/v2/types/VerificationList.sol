// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { BN254 } from "solidity-bn254/BN254.sol";
import { PlonkProof, VerificationKey, ProofLinkingInstance } from "renegade-lib/verifier/Types.sol";

/// @title Verification List
/// @author Renegade Eng
/// @notice A list of verifications to perform on a settlement bundle
struct VerificationList {
    /// @dev The cursor indicating the next index to push to
    uint256 nextIndex;
    /// @dev The list of verifications
    PlonkProof[] proofs;
    /// @dev The list of public inputs to the proof
    BN254.ScalarField[][] publicInputs;
    /// @dev The list of verification keys to use
    VerificationKey[] vks;
}

/// @title Verification List Library
/// @author Renegade Eng
/// @notice A library for managing verification lists
library VerificationListLib {
    // --- Errors --- //

    /// @notice Thrown when attempting to push to a list that has reached its capacity
    error ProofListCapacityExceeded();

    // --- Interface --- //

    /// @notice Create a new verification list
    /// @param capacity The initial capacity of the list
    /// @return The new verification list
    function newList(uint256 capacity) internal pure returns (VerificationList memory) {
        return VerificationList({
            nextIndex: 0,
            proofs: new PlonkProof[](capacity),
            publicInputs: new BN254.ScalarField[][](capacity),
            vks: new VerificationKey[](capacity)
        });
    }

    /// @notice Get the length of the list
    /// @param list The list to get the length of
    /// @return The length of the list
    function length(VerificationList memory list) internal pure returns (uint256) {
        return list.nextIndex;
    }

    /// @notice Push a proof to the list
    /// @param list The list to push to
    /// @param publicInputs The public inputs to the proof
    /// @param proof The proof to push
    /// @param vk The verification key to use
    function push(
        VerificationList memory list,
        BN254.ScalarField[] memory publicInputs,
        PlonkProof memory proof,
        VerificationKey memory vk
    )
        internal
        pure
    {
        if (list.nextIndex > list.proofs.length - 1) {
            revert ProofListCapacityExceeded();
        }
        list.proofs[list.nextIndex] = proof;
        list.publicInputs[list.nextIndex] = publicInputs;
        list.vks[list.nextIndex] = vk;
        ++list.nextIndex;
    }
}

/// @title Proof Linking List
/// @author Renegade Eng
/// @notice A list of proof linking instances to verify
struct ProofLinkingList {
    /// @dev The cursor indicating the next index to push to
    uint256 nextIndex;
    /// @dev The list of proof linking instances
    ProofLinkingInstance[] instances;
}

/// @title Proof Linking List Library
/// @author Renegade Eng
/// @notice A library for managing proof linking lists
library ProofLinkingListLib {
    // --- Errors --- //

    /// @notice Thrown when attempting to push to a list that has reached its capacity
    error ProofLinkingListCapacityExceeded();

    // --- Interface --- //

    /// @notice Create a new proof linking list
    /// @param capacity The initial capacity of the list
    /// @return The new proof linking list
    function newList(uint256 capacity) internal pure returns (ProofLinkingList memory) {
        return ProofLinkingList({ nextIndex: 0, instances: new ProofLinkingInstance[](capacity) });
    }

    /// @notice Get the length of the list
    /// @param list The list to get the length of
    /// @return The length of the list
    function length(ProofLinkingList memory list) internal pure returns (uint256) {
        return list.nextIndex;
    }

    /// @notice Push a proof linking instance to the list
    /// @param list The list to push to
    /// @param instance The proof linking instance to push
    function push(ProofLinkingList memory list, ProofLinkingInstance memory instance) internal pure {
        if (list.nextIndex > list.instances.length - 1) {
            revert ProofLinkingListCapacityExceeded();
        }
        list.instances[list.nextIndex] = instance;
        ++list.nextIndex;
    }
}
