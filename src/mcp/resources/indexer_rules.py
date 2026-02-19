"""
Indexer Coding Rules Resource.

Provides coding guidelines and patterns for The Graph subgraph development
for indexing Arbitrum smart contracts.
"""

INDEXER_CODING_RULES = {
    "name": "Indexer Coding Rules",
    "version": "1.0.0",
    "description": "Guidelines for generating The Graph subgraphs",

    "overview": {
        "description": "The Graph is a decentralized protocol for indexing and querying blockchain data",
        "components": {
            "subgraph.yaml": "Manifest defining data sources and handlers",
            "schema.graphql": "GraphQL schema for indexed entities",
            "src/mapping.ts": "AssemblyScript handlers for events",
            "abis/": "Contract ABIs for event decoding",
        },
    },

    "graph_cli": {
        "version": "0.71.x",
        "commands": {
            "codegen": "graph codegen - Generate AssemblyScript types",
            "build": "graph build - Compile subgraph to WASM",
            "deploy": "graph deploy --studio <name> - Deploy to Subgraph Studio",
            "test": "graph test - Run matchstick tests",
        },
    },

    "subgraph_yaml": {
        "structure": '''specVersion: 1.0.0
indexerHints:
  prune: auto
schema:
  file: ./schema.graphql
dataSources:
  - kind: ethereum
    name: ContractName
    network: arbitrum-sepolia
    source:
      address: "0x..."
      abi: ContractName
      startBlock: 12345678
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
        - EntityName
      abis:
        - name: ContractName
          file: ./abis/Contract.json
      eventHandlers:
        - event: Transfer(indexed address,indexed address,uint256)
          handler: handleTransfer
      file: ./src/mapping.ts''',

        "networks": {
            "arbitrum-one": "Arbitrum One Mainnet",
            "arbitrum-sepolia": "Arbitrum Sepolia Testnet",
        },

        "tips": [
            "Set startBlock to deployment block to speed up indexing",
            "Use indexerHints.prune for efficient storage",
            "Match event signatures exactly with ABI",
        ],
    },

    "schema_patterns": {
        "basic_entity": '''"""
User account entity
"""
type Account @entity {
  id: Bytes!           # Address as bytes
  balance: BigInt!     # Token balance
  createdAt: BigInt!   # Creation timestamp
}''',

        "immutable_entity": '''"""
Transfer event (immutable - never updates)
"""
type Transfer @entity(immutable: true) {
  id: Bytes!                  # tx hash + log index
  from: Account!              # Sender
  to: Account!                # Recipient
  value: BigInt!              # Amount
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}''',

        "derived_fields": '''type Account @entity {
  id: Bytes!
  balance: BigInt!
  # Derived: all transfers from this account
  transfersFrom: [Transfer!]! @derivedFrom(field: "from")
  # Derived: all transfers to this account
  transfersTo: [Transfer!]! @derivedFrom(field: "to")
}''',

        "types": {
            "Bytes": "For addresses, hashes, raw bytes",
            "BigInt": "For uint256, int256, timestamps",
            "BigDecimal": "For decimal calculations",
            "String": "For text",
            "Boolean": "For booleans",
            "Int": "For small integers (i32)",
            "ID": "For unique identifiers (string)",
        },
    },

    "mapping_patterns": {
        "basic_handler": '''import { Transfer as TransferEvent } from "../generated/Token/Token";
import { Transfer, Account } from "../generated/schema";
import { BigInt, Bytes, Address } from "@graphprotocol/graph-ts";

export function handleTransfer(event: TransferEvent): void {
  // Create unique ID for transfer
  let id = event.transaction.hash.concatI32(event.logIndex.toI32());

  // Create Transfer entity
  let transfer = new Transfer(id);
  transfer.from = event.params.from;
  transfer.to = event.params.to;
  transfer.value = event.params.value;
  transfer.blockNumber = event.block.number;
  transfer.blockTimestamp = event.block.timestamp;
  transfer.transactionHash = event.transaction.hash;
  transfer.save();
}''',

        "get_or_create": '''function getOrCreateAccount(address: Address): Account {
  let account = Account.load(address);

  if (account == null) {
    account = new Account(address);
    account.balance = BigInt.zero();
    account.createdAt = BigInt.zero();
    account.save();
  }

  return account;
}''',

        "update_balance": '''export function handleTransfer(event: TransferEvent): void {
  let from = getOrCreateAccount(event.params.from);
  let to = getOrCreateAccount(event.params.to);

  // Update balances
  from.balance = from.balance.minus(event.params.value);
  from.save();

  to.balance = to.balance.plus(event.params.value);
  to.save();
}''',

        "contract_call": '''import { Token } from "../generated/Token/Token";

export function handleTransfer(event: TransferEvent): void {
  let contract = Token.bind(event.address);

  // try_ prefix for safe calls that may revert
  let nameResult = contract.try_name();
  let name = nameResult.reverted ? "Unknown" : nameResult.value;

  // Direct call (may fail if contract reverts)
  let totalSupply = contract.totalSupply();
}''',
    },

    "best_practices": [
        "Use immutable entities for events that never change",
        "Create unique IDs with txHash.concatI32(logIndex)",
        "Use try_ calls for contract reads that may revert",
        "Store addresses as Bytes, not String",
        "Use BigInt.zero() and BigDecimal.zero() for initialization",
        "Update derived fields automatically with @derivedFrom",
        "Batch save operations when possible",
        "Index only what you query - avoid storing unnecessary data",
    ],

    "common_patterns": {
        "erc20": {
            "entities": ["Token", "Account", "Transfer", "Approval"],
            "events": ["Transfer", "Approval"],
            "metrics": ["totalSupply", "holderCount", "transferCount"],
        },
        "erc721": {
            "entities": ["Collection", "Token", "Owner", "Transfer"],
            "events": ["Transfer", "Approval", "ApprovalForAll"],
            "metrics": ["totalMinted", "uniqueOwners"],
        },
        "defi": {
            "entities": ["Pool", "Swap", "LiquidityPosition", "User"],
            "events": ["Swap", "Mint", "Burn", "Sync"],
            "metrics": ["totalValueLocked", "volume24h", "feesCollected"],
        },
    },

    "deployment": {
        "studio": {
            "steps": [
                "Create subgraph on studio.thegraph.com",
                "Run: graph auth --studio",
                "Run: graph codegen && graph build",
                "Run: graph deploy --studio <subgraph-name>",
            ],
        },
        "hosted": {
            "note": "Hosted service is deprecated, use Subgraph Studio",
        },
    },

    "debugging": {
        "tips": [
            "Check startBlock matches contract deployment",
            "Verify event signatures match ABI exactly",
            "Use graph test with matchstick for unit testing",
            "Check indexing status in Studio dashboard",
            "Review failed transactions in error logs",
        ],
    },

    "dependencies": {
        "@graphprotocol/graph-cli": "0.71.0",
        "@graphprotocol/graph-ts": "0.32.0",
    },
}
