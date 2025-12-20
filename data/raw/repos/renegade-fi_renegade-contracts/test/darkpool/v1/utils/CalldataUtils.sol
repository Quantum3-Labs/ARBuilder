// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import { BN254 } from "solidity-bn254/BN254.sol";
import { Vm } from "forge-std/Vm.sol";
import { IPermit2 } from "permit2-lib/interfaces/IPermit2.sol";
import { ISignatureTransfer } from "permit2-lib/interfaces/ISignatureTransfer.sol";
import { IERC20 } from "oz-contracts/token/ERC20/IERC20.sol";
import { TestUtils } from "test-utils/TestUtils.sol";
import { PlonkProof, LinkingProof } from "renegade-lib/verifier/Types.sol";
import { FixedPoint } from "renegade-lib/FixedPoint.sol";
import { TypesLib } from "darkpoolv1-types/TypesLib.sol";
import { ExternalTransfer, TransferType, TransferAuthorization, DepositWitness } from "darkpoolv1-types/Transfers.sol";
import { PublicRootKey, publicKeyToUints } from "darkpoolv1-types/Keychain.sol";
import {
    MatchProofs,
    MatchLinkingProofs,
    MatchAtomicProofs,
    MatchAtomicLinkingProofs,
    MalleableMatchAtomicProofs,
    PartyMatchPayload,
    ExternalMatchResult,
    ExternalMatchDirection,
    BoundedMatchResult,
    OrderSettlementIndices
} from "darkpoolv1-types/Settlement.sol";
import { FeeTake, FeeTakeRate } from "darkpoolv1-types/Fees.sol";
import { EncryptionKey, ElGamalCiphertext, BabyJubJubPoint } from "renegade-lib/Ciphertext.sol";
import { DarkpoolConstants } from "darkpoolv1-lib/Constants.sol";
import { uintToScalarWords, WalletOperations } from "darkpoolv1-lib/WalletOperations.sol";
import {
    ValidWalletCreateStatement,
    ValidWalletUpdateStatement,
    ValidCommitmentsStatement,
    ValidReblindStatement,
    ValidMatchSettleStatement,
    ValidMatchSettleWithCommitmentsStatement,
    ValidMatchSettleAtomicStatement,
    ValidMatchSettleAtomicWithCommitmentsStatement,
    ValidMalleableMatchSettleAtomicStatement,
    ValidOfflineFeeSettlementStatement,
    ValidFeeRedemptionStatement
} from "darkpoolv1-lib/PublicInputs.sol";

/// @dev The typehash for the PermitWitnessTransferFrom parameters
bytes32 constant PERMIT_TRANSFER_FROM_TYPEHASH = keccak256(
    "PermitWitnessTransferFrom(TokenPermissions permitted,address spender,uint256 nonce,uint256 deadline,DepositWitness witness)DepositWitness(uint256[4] pkRoot)TokenPermissions(address token,uint256 amount)"
);

/// @title Calldata Utils
/// @notice Utilities for generating darkpool calldata
contract CalldataUtils is TestUtils {
    using TypesLib for DepositWitness;

    /// @notice The floating point precision used in the fixed point representation
    uint256 public constant FIXED_POINT_PRECISION = 2 ** 63;
    /// @notice The protocol fee rate used for testing
    /// @dev This is the fixed point representation of 0.0001 (1bp)
    /// @dev computed as `floor(0.0001 * 2 ** 63)`
    uint256 public constant TEST_PROTOCOL_FEE = 922_337_203_685_477;
    /// @notice The relayer fee rate used for testing
    /// @dev This is the fixed point representation of 0.0002 (2bp)
    /// @dev computed as `floor(0.0002 * 2 ** 63)`
    uint256 public constant TEST_RELAYER_FEE = 1_844_674_407_370_955;

    /// @dev The typehash for the TokenPermissions parameters
    bytes32 public constant _TOKEN_PERMISSIONS_TYPEHASH = keccak256("TokenPermissions(address token,uint256 amount)");

    /// @dev The number of scalars in a note ciphertext
    uint256 public constant NOTE_CIPHERTEXT_SCALARS = 3;

    // ---------------------
    // | Darkpool Calldata |
    // ---------------------

    /// --- Create Wallet --- ///

    /// @notice Generate calldata for creating a wallet
    function createWalletCalldata()
        internal
        returns (ValidWalletCreateStatement memory statement, PlonkProof memory proof)
    {
        statement = ValidWalletCreateStatement({
            walletShareCommitment: BN254.ScalarField.wrap(randomFelt()),
            publicShares: randomWalletShares()
        });
        proof = dummyPlonkProof();
    }

    /// --- Update Wallet --- ///

    /// @notice Generate calldata for updating a wallet
    function updateWalletCalldata()
        internal
        returns (
            bytes memory newSharesCommitmentSig,
            ValidWalletUpdateStatement memory statement,
            PlonkProof memory proof
        )
    {
        ExternalTransfer memory transfer = emptyExternalTransfer();
        return updateWalletWithExternalTransferCalldata(transfer);
    }

    /// @notice Generate calldata for a wallet update with a given external transfer
    function updateWalletWithExternalTransferCalldata(ExternalTransfer memory transfer)
        internal
        returns (
            bytes memory newSharesCommitmentSig,
            ValidWalletUpdateStatement memory statement,
            PlonkProof memory proof
        )
    {
        Vm.Wallet memory rootKeyWallet = randomEthereumWallet();
        return generateUpdateWalletCalldata(transfer, rootKeyWallet);
    }

    /// @notice Generate update wallet calldata for a given transfer using a given root key wallet
    function generateUpdateWalletCalldata(
        ExternalTransfer memory transfer,
        Vm.Wallet memory rootKeyWallet
    )
        internal
        returns (
            bytes memory newSharesCommitmentSig,
            ValidWalletUpdateStatement memory statement,
            PlonkProof memory proof
        )
    {
        statement = ValidWalletUpdateStatement({
            previousNullifier: randomScalar(),
            newWalletCommitment: randomScalar(),
            newPublicShares: randomWalletShares(),
            merkleRoot: randomScalar(),
            externalTransfer: transfer,
            oldPkRoot: forgeWalletToRootKey(rootKeyWallet)
        });
        proof = dummyPlonkProof();

        // Sign the new shares commitment
        bytes32 digest = WalletOperations.walletCommitmentDigest(statement.newWalletCommitment);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(rootKeyWallet.privateKey, digest);
        newSharesCommitmentSig = abi.encodePacked(r, s, v);
    }

    /// --- Settle Match --- ///

    /// @notice Generate calldata for settling a match
    function settleMatchCalldata(BN254.ScalarField merkleRoot)
        internal
        returns (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        )
    {
        party0Payload = generatePartyMatchPayload(merkleRoot);
        party1Payload = generatePartyMatchPayload(merkleRoot);

        OrderSettlementIndices memory indices0 = party0Payload.validCommitmentsStatement.indices;
        OrderSettlementIndices memory indices1 = party1Payload.validCommitmentsStatement.indices;
        statement = ValidMatchSettleStatement({
            firstPartyPublicShares: randomWalletShares(),
            secondPartyPublicShares: randomWalletShares(),
            firstPartySettlementIndices: indices0,
            secondPartySettlementIndices: indices1,
            protocolFeeRate: TEST_PROTOCOL_FEE
        });
        proofs = MatchProofs({
            validCommitments0: dummyPlonkProof(),
            validReblind0: dummyPlonkProof(),
            validCommitments1: dummyPlonkProof(),
            validReblind1: dummyPlonkProof(),
            validMatchSettle: dummyPlonkProof()
        });
        linkingProofs = MatchLinkingProofs({
            validReblindCommitments0: dummyLinkingProof(),
            validCommitmentsMatchSettle0: dummyLinkingProof(),
            validReblindCommitments1: dummyLinkingProof(),
            validCommitmentsMatchSettle1: dummyLinkingProof()
        });
    }

    /// --- Settle Match With Commitments --- ///

    /// @notice Generate calldata for settling a match with commitments
    function settleMatchWithCommitmentsCalldata(BN254.ScalarField merkleRoot)
        internal
        returns (
            PartyMatchPayload memory party0Payload,
            PartyMatchPayload memory party1Payload,
            ValidMatchSettleWithCommitmentsStatement memory statement,
            MatchProofs memory proofs,
            MatchLinkingProofs memory linkingProofs
        )
    {
        // Generate base calldata
        ValidMatchSettleStatement memory baseStatement;
        (party0Payload, party1Payload, baseStatement, proofs, linkingProofs) = settleMatchCalldata(merkleRoot);

        // Create a `VALID MATCH SETTLE WITH COMMITMENTS` statement
        BN254.ScalarField privateShareCommitment0 = party0Payload.validReblindStatement.newPrivateShareCommitment;
        BN254.ScalarField privateShareCommitment1 = party1Payload.validReblindStatement.newPrivateShareCommitment;
        BN254.ScalarField newShareCommitment0 = randomScalar();
        BN254.ScalarField newShareCommitment1 = randomScalar();
        statement = ValidMatchSettleWithCommitmentsStatement({
            privateShareCommitment0: privateShareCommitment0,
            privateShareCommitment1: privateShareCommitment1,
            newShareCommitment0: newShareCommitment0,
            newShareCommitment1: newShareCommitment1,
            firstPartyPublicShares: baseStatement.firstPartyPublicShares,
            secondPartyPublicShares: baseStatement.secondPartyPublicShares,
            firstPartySettlementIndices: baseStatement.firstPartySettlementIndices,
            secondPartySettlementIndices: baseStatement.secondPartySettlementIndices,
            protocolFeeRate: baseStatement.protocolFeeRate
        });
    }

    /// --- Settle Atomic Match --- ///

    /// @notice Generate calldata for settling an atomic match
    function settleAtomicMatchCalldata(BN254.ScalarField merkleRoot)
        internal
        returns (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        )
    {
        ExternalMatchResult memory matchResult = randomExternalMatchResult();
        return settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);
    }

    /// @notice Generate calldata for settling an atomic match with a given match result
    function settleAtomicMatchCalldataWithMatchResult(
        BN254.ScalarField merkleRoot,
        ExternalMatchResult memory matchResult
    )
        internal
        returns (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        )
    {
        internalPartyPayload = generatePartyMatchPayload(merkleRoot);
        statement = ValidMatchSettleAtomicStatement({
            matchResult: matchResult,
            externalPartyFees: computeExternalPartyFees(matchResult),
            internalPartyModifiedShares: randomWalletShares(),
            internalPartySettlementIndices: internalPartyPayload.validCommitmentsStatement.indices,
            protocolFeeRate: TEST_PROTOCOL_FEE,
            relayerFeeAddress: vm.randomAddress()
        });

        proofs = MatchAtomicProofs({
            validCommitments: dummyPlonkProof(),
            validReblind: dummyPlonkProof(),
            validMatchSettleAtomic: dummyPlonkProof()
        });
        linkingProofs = MatchAtomicLinkingProofs({
            validReblindCommitments: dummyLinkingProof(),
            validCommitmentsMatchSettleAtomic: dummyLinkingProof()
        });
    }

    /// --- Settle Atomic Match With Commitments --- ///

    /// @notice Generate calldata for settling an atomic match with commitments
    function settleAtomicMatchWithCommitmentsCalldata(
        BN254.ScalarField merkleRoot,
        ExternalMatchResult memory matchResult
    )
        internal
        returns (
            PartyMatchPayload memory internalPartyPayload,
            ValidMatchSettleAtomicWithCommitmentsStatement memory statement,
            MatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        )
    {
        // Generate base calldata
        ValidMatchSettleAtomicStatement memory baseStatement;
        (internalPartyPayload, baseStatement, proofs, linkingProofs) =
            settleAtomicMatchCalldataWithMatchResult(merkleRoot, matchResult);

        // Create a `VALID MATCH SETTLE ATOMIC WITH COMMITMENTS` statement
        BN254.ScalarField privateShareCommitment = internalPartyPayload.validReblindStatement.newPrivateShareCommitment;
        BN254.ScalarField newShareCommitment = randomScalar();
        statement = ValidMatchSettleAtomicWithCommitmentsStatement({
            privateShareCommitment: privateShareCommitment,
            newShareCommitment: newShareCommitment,
            matchResult: baseStatement.matchResult,
            externalPartyFees: baseStatement.externalPartyFees,
            internalPartyModifiedShares: baseStatement.internalPartyModifiedShares,
            internalPartySettlementIndices: baseStatement.internalPartySettlementIndices,
            protocolFeeRate: baseStatement.protocolFeeRate,
            relayerFeeAddress: baseStatement.relayerFeeAddress
        });
    }

    /// --- Settle Malleable Atomic Match --- ///

    /// @notice Generate calldata for settling a malleable atomic match
    /// @dev This is a helper function that generates calldata for a malleable atomic match, with a match direction
    function settleMalleableAtomicMatchCalldata(BN254.ScalarField merkleRoot)
        internal
        returns (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        )
    {
        ExternalMatchDirection direction;
        if (vm.randomBool()) {
            direction = ExternalMatchDirection.InternalPartyBuy;
        } else {
            direction = ExternalMatchDirection.InternalPartySell;
        }

        return settleMalleableAtomicMatchCalldata(direction, merkleRoot);
    }

    /// @notice Generate calldata for settling a malleable atomic match, with a match direction
    /// @param merkleRoot The merkle root of the wallet
    /// @param direction The direction of the match
    /// @return internalPartyPayload The payload for the internal party
    /// @return statement The statement for the malleable atomic match
    /// @return proofs The proofs for the malleable atomic match
    /// @return linkingProofs The linking proofs for the malleable atomic match
    function settleMalleableAtomicMatchCalldata(
        ExternalMatchDirection direction,
        BN254.ScalarField merkleRoot
    )
        internal
        returns (
            PartyMatchPayload memory internalPartyPayload,
            ValidMalleableMatchSettleAtomicStatement memory statement,
            MalleableMatchAtomicProofs memory proofs,
            MatchAtomicLinkingProofs memory linkingProofs
        )
    {
        internalPartyPayload = generatePartyMatchPayload(merkleRoot);
        statement = ValidMalleableMatchSettleAtomicStatement({
            matchResult: randomBoundedMatchResult(direction),
            externalFeeRates: randomFeeTakeRate(),
            internalFeeRates: randomFeeTakeRate(),
            internalPartyPublicShares: randomWalletShares(),
            relayerFeeAddress: vm.randomAddress()
        });
        proofs = MalleableMatchAtomicProofs({
            validCommitments: dummyPlonkProof(),
            validReblind: dummyPlonkProof(),
            validMalleableMatchSettleAtomic: dummyPlonkProof()
        });
        linkingProofs = MatchAtomicLinkingProofs({
            validReblindCommitments: dummyLinkingProof(),
            validCommitmentsMatchSettleAtomic: dummyLinkingProof()
        });
    }

    /// --- Settle Offline Fee --- ///

    /// @notice Generate calldata for settling an offline fee
    function settleOfflineFeeCalldata(
        BN254.ScalarField merkleRoot,
        EncryptionKey memory protocolKey
    )
        internal
        returns (ValidOfflineFeeSettlementStatement memory statement, PlonkProof memory proof)
    {
        statement = ValidOfflineFeeSettlementStatement({
            merkleRoot: merkleRoot,
            walletNullifier: randomScalar(),
            newWalletCommitment: randomScalar(),
            updatedWalletPublicShares: randomWalletShares(),
            noteCiphertext: randomElGamalCiphertext(NOTE_CIPHERTEXT_SCALARS),
            noteCommitment: randomScalar(),
            protocolKey: protocolKey,
            isProtocolFee: vm.randomBool()
        });
        proof = dummyPlonkProof();
    }

    /// --- Redeem Fee --- ///

    /// @notice Generate calldata for redeeming a fee
    function redeemFeeCalldata(
        BN254.ScalarField merkleRoot,
        Vm.Wallet memory receiverWallet
    )
        internal
        returns (
            bytes memory newSharesCommitmentSig,
            ValidFeeRedemptionStatement memory statement,
            PlonkProof memory proof
        )
    {
        statement = ValidFeeRedemptionStatement({
            walletRoot: merkleRoot,
            noteRoot: merkleRoot,
            walletNullifier: randomScalar(),
            noteNullifier: randomScalar(),
            newSharesCommitment: randomScalar(),
            newWalletPublicShares: randomWalletShares(),
            walletRootKey: forgeWalletToRootKey(receiverWallet)
        });
        proof = dummyPlonkProof();

        // Sign the new shares commitment
        bytes32 digest = WalletOperations.walletCommitmentDigest(statement.newSharesCommitment);
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(receiverWallet.privateKey, digest);
        newSharesCommitmentSig = abi.encodePacked(r, s, v);
    }

    // --------------------
    // | Calldata Helpers |
    // --------------------

    /// --- Match Bundles --- ///

    /// @notice Generate a match payload for a single party in a match
    function generatePartyMatchPayload(BN254.ScalarField merkleRoot)
        internal
        returns (PartyMatchPayload memory payload)
    {
        payload = PartyMatchPayload({
            validCommitmentsStatement: ValidCommitmentsStatement({ indices: randomOrderSettlementIndices() }),
            validReblindStatement: ValidReblindStatement({
                originalSharesNullifier: randomScalar(),
                newPrivateShareCommitment: randomScalar(),
                merkleRoot: merkleRoot
            })
        });
    }

    /// @notice Generate a random external match result
    function randomExternalMatchResult() internal returns (ExternalMatchResult memory matchResult) {
        ExternalMatchDirection direction;
        if (vm.randomBool()) {
            direction = ExternalMatchDirection.InternalPartyBuy;
        } else {
            direction = ExternalMatchDirection.InternalPartySell;
        }

        matchResult = randomExternalMatchResult(direction);
    }

    /// @dev Generate a random external match result
    function randomExternalMatchResult(ExternalMatchDirection direction)
        internal
        returns (ExternalMatchResult memory matchResult)
    {
        matchResult = ExternalMatchResult({
            baseMint: vm.randomAddress(),
            quoteMint: vm.randomAddress(),
            baseAmount: randomAmount(),
            quoteAmount: randomAmount(),
            direction: direction
        });
    }

    /// @dev Generate a random bounded match result
    function randomBoundedMatchResult(ExternalMatchDirection direction)
        internal
        returns (BoundedMatchResult memory matchResult)
    {
        uint256 minAmt = randomAmount();
        uint256 maxAmt = randomUint(minAmt, minAmt * 2);
        matchResult = BoundedMatchResult({
            quoteMint: vm.randomAddress(),
            baseMint: vm.randomAddress(),
            price: randomPrice(),
            minBaseAmount: minAmt,
            maxBaseAmount: maxAmt,
            direction: direction
        });
    }

    /// @dev Generate a random price
    /// @dev We generate a random price between 0.01 and 1000 by generating a
    /// @dev random fixed-point representation between 92233720368547760 (0.01) and
    /// @dev 9223372036854775808000 (1000)
    function randomPrice() internal returns (FixedPoint memory price) {
        uint256 minPriceRepr = 92_233_720_368_547_760;
        uint256 maxPriceRepr = 9_223_372_036_854_775_808_000;
        price = FixedPoint({ repr: randomUint(minPriceRepr, maxPriceRepr) });
    }

    /// @dev Generate a random set of order settlement indices
    function randomOrderSettlementIndices() internal returns (OrderSettlementIndices memory indices) {
        uint256 bal1 = randomUint(DarkpoolConstants.MAX_BALANCES);
        uint256 bal2 = randomUint(DarkpoolConstants.MAX_BALANCES);
        while (bal2 == bal1) {
            bal2 = randomUint(DarkpoolConstants.MAX_BALANCES);
        }
        uint256 order = randomUint(DarkpoolConstants.MAX_ORDERS);

        indices = OrderSettlementIndices({ balanceSend: bal1, balanceReceive: bal2, order: order });
    }

    /// @dev Generate a random fee take rate
    function randomFeeTakeRate() internal returns (FeeTakeRate memory feeRates) {
        FixedPoint memory protocolFee = FixedPoint({ repr: TEST_PROTOCOL_FEE });
        feeRates = FeeTakeRate({ relayerFeeRate: randomTakeRate(), protocolFeeRate: protocolFee });
    }

    /// @dev Generate a random take rate
    function randomTakeRate() internal returns (FixedPoint memory feeRate) {
        // Generate a random fee between 1bp and 10bps
        // We use a fixed point representation of `x * 2^63` as is used throughout the system
        // and generate a random integer representation between our bounds
        uint256 oneBpFp = 922_337_203_685_477;
        uint256 tenBpsFp = oneBpFp * 10;
        uint256 randRepr = randomUint(oneBpFp, tenBpsFp);
        feeRate = FixedPoint({ repr: randRepr });
    }

    /// --- Fees --- ///

    /// @notice Compute the fee due by an external party for the given external match result
    function computeExternalPartyFees(ExternalMatchResult memory matchResult)
        internal
        pure
        returns (FeeTake memory fees)
    {
        if (matchResult.direction == ExternalMatchDirection.InternalPartyBuy) {
            fees = computeFees(matchResult.quoteAmount);
        } else {
            fees = computeFees(matchResult.baseAmount);
        }
    }

    /// @notice Compute the fee for a given receive amount using the `TEST_RELAYER_FEE`
    /// @notice and the `TEST_PROTOCOL_FEE` for the relayer and protocol fees respectively
    function computeFees(uint256 receiveAmount) internal pure returns (FeeTake memory fees) {
        fees = computeFeesWithRates(receiveAmount, TEST_RELAYER_FEE, TEST_PROTOCOL_FEE);
    }

    /// @notice Compute the fee for a given receive amount using the given relayer and protocol fees
    function computeFeesWithRates(
        uint256 receiveAmount,
        uint256 relayerFee,
        uint256 protocolFee
    )
        internal
        pure
        returns (FeeTake memory fees)
    {
        fees = FeeTake({
            relayerFee: (receiveAmount * relayerFee) / FIXED_POINT_PRECISION,
            protocolFee: (receiveAmount * protocolFee) / FIXED_POINT_PRECISION
        });
    }

    /// --- External Transfers --- ///

    /// @notice Generate an empty external transfer
    function emptyExternalTransfer() internal pure returns (ExternalTransfer memory transfer) {
        transfer =
            ExternalTransfer({ account: address(0), mint: address(0), amount: 0, transferType: TransferType.Deposit });
    }

    /// @notice Generate empty transfer authorization
    function emptyTransferAuthorization() internal pure returns (TransferAuthorization memory authorization) {
        authorization = TransferAuthorization({
            permit2Nonce: 0,
            permit2Deadline: 0,
            permit2Signature: bytes(""),
            externalTransferSignature: bytes("")
        });
    }

    /// @notice Authorize a deposit
    function authorizeDeposit(
        ExternalTransfer memory transfer,
        PublicRootKey memory oldPkRoot,
        address darkpoolAddress,
        IPermit2 permit2,
        Vm.Wallet memory wallet
    )
        internal
        returns (TransferAuthorization memory authorization)
    {
        // Default to empty transfer auth, we only fill in the deposit info
        authorization = emptyTransferAuthorization();

        // 1. Approve the permit2 contract
        IERC20 token = IERC20(transfer.mint);
        vm.startBroadcast(wallet.addr);
        token.approve(address(permit2), transfer.amount);
        vm.stopBroadcast();

        // 2. Generate a permit2 signature
        uint256 nonce = randomUint();
        uint256 deadline = block.timestamp + 1 days;
        ISignatureTransfer.TokenPermissions memory tokenPermissions =
            ISignatureTransfer.TokenPermissions({ token: transfer.mint, amount: transfer.amount });
        ISignatureTransfer.PermitTransferFrom memory permit =
            ISignatureTransfer.PermitTransferFrom({ permitted: tokenPermissions, nonce: nonce, deadline: deadline });
        DepositWitness memory depositWitness = DepositWitness({ pkRoot: publicKeyToUints(oldPkRoot) });
        bytes32 depositWitnessHash = depositWitness.hashWitness();

        bytes memory sig = getPermitWitnessTransferSignature(
            permit,
            darkpoolAddress,
            wallet.privateKey,
            PERMIT_TRANSFER_FROM_TYPEHASH,
            depositWitnessHash,
            permit2.DOMAIN_SEPARATOR()
        );

        authorization.permit2Nonce = nonce;
        authorization.permit2Deadline = deadline;
        authorization.permit2Signature = sig;
    }

    /// @notice Generate a permit2 signature for a witness transfer
    /// @dev Borrowed from `permit2-lib/test/utils/PermitSignature.sol`, solc cannot infer types correctly
    /// @dev if the import is directly from `permit2-lib/test/utils/PermitSignature.sol`
    function getPermitWitnessTransferSignature(
        ISignatureTransfer.PermitTransferFrom memory permit,
        address receiver,
        uint256 privateKey,
        bytes32 typehash,
        bytes32 witness,
        bytes32 domainSeparator
    )
        internal
        pure
        returns (bytes memory sig)
    {
        bytes32 tokenPermissions = keccak256(abi.encode(_TOKEN_PERMISSIONS_TYPEHASH, permit.permitted));

        bytes32 msgHash = keccak256(
            abi.encodePacked(
                "\x19\x01",
                domainSeparator,
                keccak256(abi.encode(typehash, tokenPermissions, receiver, permit.nonce, permit.deadline, witness))
            )
        );

        (uint8 v, bytes32 r, bytes32 s) = vm.sign(privateKey, msgHash);
        return bytes.concat(r, s, bytes1(v));
    }

    /// @notice Authorize a withdrawal
    function authorizeWithdrawal(
        ExternalTransfer memory transfer,
        Vm.Wallet memory wallet
    )
        internal
        pure
        returns (TransferAuthorization memory authorization)
    {
        // Default to empty transfer auth, we only fill in the withdrawal signature
        authorization = emptyTransferAuthorization();

        // Sign the transfer, this is sufficient for a withdrawal
        bytes32 digest = keccak256(abi.encode(transfer));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(wallet.privateKey, digest);
        authorization.externalTransferSignature = abi.encodePacked(r, s, v);
    }

    /// --- Wallets --- ///

    /// @notice Generate a random root key
    function randomRootKey() internal returns (PublicRootKey memory rootKey) {
        Vm.Wallet memory wallet = randomEthereumWallet();
        rootKey = forgeWalletToRootKey(wallet);
    }

    /// @notice Convert a forge wallet to a public root key
    function forgeWalletToRootKey(Vm.Wallet memory wallet) internal pure returns (PublicRootKey memory rootKey) {
        (BN254.ScalarField xLow, BN254.ScalarField xHigh) = uintToScalarWords(wallet.publicKeyX);
        (BN254.ScalarField yLow, BN254.ScalarField yHigh) = uintToScalarWords(wallet.publicKeyY);
        rootKey = PublicRootKey({ x: [xLow, xHigh], y: [yLow, yHigh] });
    }

    /// --- Encryption --- ///

    /// @notice Generate a random encryption key
    /// @dev For our purposes, this key does not need to be on the curve,
    /// @dev no curve arithmetic is performed on it
    function randomEncryptionKey() internal returns (EncryptionKey memory key) {
        key = EncryptionKey({ point: BabyJubJubPoint({ x: randomScalar(), y: randomScalar() }) });
    }

    /// @notice Generate a random ElGamal ciphertext
    function randomElGamalCiphertext(uint256 numScalars) internal returns (ElGamalCiphertext memory ciphertext) {
        // Generate the stream ciphered scalars
        BN254.ScalarField[] memory scalars = new BN254.ScalarField[](numScalars);
        for (uint256 i = 0; i < numScalars; i++) {
            scalars[i] = randomScalar();
        }

        // Generate the ephemeral key
        EncryptionKey memory ephemeralKey = randomEncryptionKey();
        ciphertext = ElGamalCiphertext({ ephemeralKey: ephemeralKey.point, ciphertext: scalars });
    }

    /// --- Plonk Proofs --- ///

    /// @notice Generates a dummy PlonK proof
    function dummyPlonkProof() internal pure returns (PlonkProof memory proof) {
        BN254.ScalarField dummyScalar = BN254.ScalarField.wrap(1);
        BN254.G1Point memory dummyPoint = BN254.P1();
        BN254.ScalarField[] memory publicInputs = new BN254.ScalarField[](1);
        publicInputs[0] = dummyScalar;

        proof = PlonkProof({
            wireComms: [dummyPoint, dummyPoint, dummyPoint, dummyPoint, dummyPoint],
            zComm: dummyPoint,
            quotientComms: [dummyPoint, dummyPoint, dummyPoint, dummyPoint, dummyPoint],
            wZeta: dummyPoint,
            wZetaOmega: dummyPoint,
            wireEvals: [dummyScalar, dummyScalar, dummyScalar, dummyScalar, dummyScalar],
            sigmaEvals: [dummyScalar, dummyScalar, dummyScalar, dummyScalar],
            zBar: dummyScalar
        });
    }

    /// @notice Generates a dummy linking proof
    function dummyLinkingProof() internal pure returns (LinkingProof memory proof) {
        BN254.G1Point memory dummyPoint = BN254.P1();
        proof = LinkingProof({ linkingQuotientPolyComm: dummyPoint, linkingPolyOpening: dummyPoint });
    }
}
