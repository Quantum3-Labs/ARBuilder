"""
Indexer templates for The Graph subgraphs.
These templates provide scaffolding for indexing Arbitrum contracts.

Templates:
- ERC20 Subgraph: Token transfers, balances, and holders
- ERC721 Subgraph: NFT ownership, metadata, and transfers
- DeFi Subgraph: Swaps, liquidity, and pool data
- Custom Events Subgraph: Generic event indexing
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class IndexerTemplate:
    """A curated subgraph template."""

    name: str
    description: str
    template_type: str  # "erc20" | "erc721" | "defi" | "custom"
    features: List[str]
    files: Dict[str, str]  # path -> content
    dependencies: Dict[str, str]
    networks: List[str]  # supported networks


# ERC20 Subgraph Template
ERC20_SUBGRAPH_TEMPLATE = IndexerTemplate(
    name="ERC20 Subgraph",
    description="Index ERC20 token transfers, balances, and holder statistics",
    template_type="erc20",
    features=[
        "Transfer indexing",
        "Balance tracking",
        "Holder count",
        "Transaction history",
    ],
    files={
        "subgraph.yaml": '''specVersion: 1.0.0
indexerHints:
  prune: auto
schema:
  file: ./schema.graphql
dataSources:
  - kind: ethereum
    name: Token
    network: arbitrum-sepolia
    source:
      address: "0x0000000000000000000000000000000000000000"
      abi: ERC20
      startBlock: 0
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
        - Token
        - Account
        - Transfer
        - Approval
      abis:
        - name: ERC20
          file: ./abis/ERC20.json
      eventHandlers:
        - event: Transfer(indexed address,indexed address,uint256)
          handler: handleTransfer
        - event: Approval(indexed address,indexed address,uint256)
          handler: handleApproval
      file: ./src/mapping.ts
''',
        "schema.graphql": '''"""
ERC20 Token entity
"""
type Token @entity {
  id: Bytes! # Token address
  name: String!
  symbol: String!
  decimals: Int!
  totalSupply: BigInt!
  holderCount: BigInt!
  transferCount: BigInt!
}

"""
Account holding tokens
"""
type Account @entity {
  id: Bytes! # Account address
  balance: BigInt!
  transfersFrom: [Transfer!]! @derivedFrom(field: "from")
  transfersTo: [Transfer!]! @derivedFrom(field: "to")
}

"""
Transfer event
"""
type Transfer @entity(immutable: true) {
  id: Bytes!
  from: Account!
  to: Account!
  value: BigInt!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}

"""
Approval event
"""
type Approval @entity {
  id: Bytes!
  owner: Account!
  spender: Account!
  value: BigInt!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}
''',
        "src/mapping.ts": '''import {
  Transfer as TransferEvent,
  Approval as ApprovalEvent,
  ERC20,
} from "../generated/Token/ERC20";
import { Token, Account, Transfer, Approval } from "../generated/schema";
import { BigInt, Bytes, Address } from "@graphprotocol/graph-ts";

const ZERO_ADDRESS = Address.fromString("0x0000000000000000000000000000000000000000");

function getOrCreateToken(address: Address): Token {
  let token = Token.load(address);
  if (token == null) {
    token = new Token(address);
    let contract = ERC20.bind(address);

    let nameResult = contract.try_name();
    token.name = nameResult.reverted ? "Unknown" : nameResult.value;

    let symbolResult = contract.try_symbol();
    token.symbol = symbolResult.reverted ? "???" : symbolResult.value;

    let decimalsResult = contract.try_decimals();
    token.decimals = decimalsResult.reverted ? 18 : decimalsResult.value;

    let totalSupplyResult = contract.try_totalSupply();
    token.totalSupply = totalSupplyResult.reverted ? BigInt.zero() : totalSupplyResult.value;

    token.holderCount = BigInt.zero();
    token.transferCount = BigInt.zero();
    token.save();
  }
  return token;
}

function getOrCreateAccount(address: Address): Account {
  let account = Account.load(address);
  if (account == null) {
    account = new Account(address);
    account.balance = BigInt.zero();
    account.save();
  }
  return account;
}

export function handleTransfer(event: TransferEvent): void {
  let token = getOrCreateToken(event.address);
  let from = getOrCreateAccount(event.params.from);
  let to = getOrCreateAccount(event.params.to);

  // Update balances
  if (event.params.from != ZERO_ADDRESS) {
    from.balance = from.balance.minus(event.params.value);
    if (from.balance.equals(BigInt.zero())) {
      token.holderCount = token.holderCount.minus(BigInt.fromI32(1));
    }
    from.save();
  }

  if (event.params.to != ZERO_ADDRESS) {
    let wasZero = to.balance.equals(BigInt.zero());
    to.balance = to.balance.plus(event.params.value);
    if (wasZero && to.balance.gt(BigInt.zero())) {
      token.holderCount = token.holderCount.plus(BigInt.fromI32(1));
    }
    to.save();
  }

  // Create transfer entity
  let transfer = new Transfer(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  );
  transfer.from = from.id;
  transfer.to = to.id;
  transfer.value = event.params.value;
  transfer.blockNumber = event.block.number;
  transfer.blockTimestamp = event.block.timestamp;
  transfer.transactionHash = event.transaction.hash;
  transfer.save();

  // Update token stats
  token.transferCount = token.transferCount.plus(BigInt.fromI32(1));
  token.save();
}

export function handleApproval(event: ApprovalEvent): void {
  let owner = getOrCreateAccount(event.params.owner);
  let spender = getOrCreateAccount(event.params.spender);

  let approval = new Approval(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  );
  approval.owner = owner.id;
  approval.spender = spender.id;
  approval.value = event.params.value;
  approval.blockNumber = event.block.number;
  approval.blockTimestamp = event.block.timestamp;
  approval.transactionHash = event.transaction.hash;
  approval.save();
}
''',
        "abis/ERC20.json": '''[
  {
    "anonymous": false,
    "inputs": [
      {"indexed": true, "name": "owner", "type": "address"},
      {"indexed": true, "name": "spender", "type": "address"},
      {"indexed": false, "name": "value", "type": "uint256"}
    ],
    "name": "Approval",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {"indexed": true, "name": "from", "type": "address"},
      {"indexed": true, "name": "to", "type": "address"},
      {"indexed": false, "name": "value", "type": "uint256"}
    ],
    "name": "Transfer",
    "type": "event"
  },
  {
    "inputs": [],
    "name": "name",
    "outputs": [{"name": "", "type": "string"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "symbol",
    "outputs": [{"name": "", "type": "string"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "decimals",
    "outputs": [{"name": "", "type": "uint8"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "totalSupply",
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{"name": "owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
  }
]
''',
        "package.json": '''{
  "name": "erc20-subgraph",
  "version": "0.1.0",
  "scripts": {
    "codegen": "graph codegen",
    "build": "graph build",
    "deploy": "graph deploy --node https://api.studio.thegraph.com/deploy/",
    "create-local": "graph create --node http://localhost:8020/ erc20-subgraph",
    "remove-local": "graph remove --node http://localhost:8020/ erc20-subgraph",
    "deploy-local": "graph deploy --node http://localhost:8020/ --ipfs http://localhost:5001 erc20-subgraph"
  },
  "dependencies": {
    "@graphprotocol/graph-cli": "0.71.0",
    "@graphprotocol/graph-ts": "0.32.0"
  }
}
''',
    },
    dependencies={
        "@graphprotocol/graph-cli": "0.71.0",
        "@graphprotocol/graph-ts": "0.32.0",
    },
    networks=["arbitrum-one", "arbitrum-sepolia"],
)


# ERC721 Subgraph Template
ERC721_SUBGRAPH_TEMPLATE = IndexerTemplate(
    name="ERC721 Subgraph",
    description="Index NFT ownership, metadata, and transfer history",
    template_type="erc721",
    features=[
        "NFT ownership tracking",
        "Metadata indexing",
        "Transfer history",
        "Collection stats",
    ],
    files={
        "subgraph.yaml": '''specVersion: 1.0.0
indexerHints:
  prune: auto
schema:
  file: ./schema.graphql
dataSources:
  - kind: ethereum
    name: NFT
    network: arbitrum-sepolia
    source:
      address: "0x0000000000000000000000000000000000000000"
      abi: ERC721
      startBlock: 0
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
        - Collection
        - Token
        - Owner
        - Transfer
      abis:
        - name: ERC721
          file: ./abis/ERC721.json
      eventHandlers:
        - event: Transfer(indexed address,indexed address,indexed uint256)
          handler: handleTransfer
      file: ./src/mapping.ts
''',
        "schema.graphql": '''"""
NFT Collection entity
"""
type Collection @entity {
  id: Bytes! # Contract address
  name: String!
  symbol: String!
  totalSupply: BigInt!
  tokens: [Token!]! @derivedFrom(field: "collection")
}

"""
Individual NFT token
"""
type Token @entity {
  id: ID! # collection-tokenId
  collection: Collection!
  tokenId: BigInt!
  owner: Owner!
  tokenURI: String
  transfers: [Transfer!]! @derivedFrom(field: "token")
  mintedAt: BigInt!
  mintTransaction: Bytes!
}

"""
NFT Owner
"""
type Owner @entity {
  id: Bytes! # Address
  tokens: [Token!]! @derivedFrom(field: "owner")
  tokenCount: BigInt!
}

"""
Transfer event
"""
type Transfer @entity(immutable: true) {
  id: Bytes!
  token: Token!
  from: Owner!
  to: Owner!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}
''',
        "src/mapping.ts": '''import {
  Transfer as TransferEvent,
  ERC721,
} from "../generated/NFT/ERC721";
import { Collection, Token, Owner, Transfer } from "../generated/schema";
import { BigInt, Bytes, Address } from "@graphprotocol/graph-ts";

const ZERO_ADDRESS = Address.fromString("0x0000000000000000000000000000000000000000");

function getOrCreateCollection(address: Address): Collection {
  let collection = Collection.load(address);
  if (collection == null) {
    collection = new Collection(address);
    let contract = ERC721.bind(address);

    let nameResult = contract.try_name();
    collection.name = nameResult.reverted ? "Unknown" : nameResult.value;

    let symbolResult = contract.try_symbol();
    collection.symbol = symbolResult.reverted ? "???" : symbolResult.value;

    collection.totalSupply = BigInt.zero();
    collection.save();
  }
  return collection;
}

function getOrCreateOwner(address: Address): Owner {
  let owner = Owner.load(address);
  if (owner == null) {
    owner = new Owner(address);
    owner.tokenCount = BigInt.zero();
    owner.save();
  }
  return owner;
}

function getTokenId(collection: Address, tokenId: BigInt): string {
  return collection.toHexString() + "-" + tokenId.toString();
}

export function handleTransfer(event: TransferEvent): void {
  let collection = getOrCreateCollection(event.address);
  let from = getOrCreateOwner(event.params.from);
  let to = getOrCreateOwner(event.params.to);

  let tokenEntityId = getTokenId(event.address, event.params.tokenId);
  let token = Token.load(tokenEntityId);

  // Mint event
  if (event.params.from == ZERO_ADDRESS) {
    token = new Token(tokenEntityId);
    token.collection = collection.id;
    token.tokenId = event.params.tokenId;
    token.owner = to.id;
    token.mintedAt = event.block.timestamp;
    token.mintTransaction = event.transaction.hash;

    // Try to get tokenURI
    let contract = ERC721.bind(event.address);
    let uriResult = contract.try_tokenURI(event.params.tokenId);
    token.tokenURI = uriResult.reverted ? null : uriResult.value;

    collection.totalSupply = collection.totalSupply.plus(BigInt.fromI32(1));
    collection.save();
  }

  if (token != null) {
    // Update ownership
    if (event.params.from != ZERO_ADDRESS) {
      from.tokenCount = from.tokenCount.minus(BigInt.fromI32(1));
      from.save();
    }

    if (event.params.to != ZERO_ADDRESS) {
      to.tokenCount = to.tokenCount.plus(BigInt.fromI32(1));
      to.save();
    }

    token.owner = to.id;
    token.save();

    // Create transfer record
    let transfer = new Transfer(
      event.transaction.hash.concatI32(event.logIndex.toI32())
    );
    transfer.token = token.id;
    transfer.from = from.id;
    transfer.to = to.id;
    transfer.blockNumber = event.block.number;
    transfer.blockTimestamp = event.block.timestamp;
    transfer.transactionHash = event.transaction.hash;
    transfer.save();
  }
}
''',
        "abis/ERC721.json": '''[
  {
    "anonymous": false,
    "inputs": [
      {"indexed": true, "name": "from", "type": "address"},
      {"indexed": true, "name": "to", "type": "address"},
      {"indexed": true, "name": "tokenId", "type": "uint256"}
    ],
    "name": "Transfer",
    "type": "event"
  },
  {
    "inputs": [],
    "name": "name",
    "outputs": [{"name": "", "type": "string"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "symbol",
    "outputs": [{"name": "", "type": "string"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{"name": "tokenId", "type": "uint256"}],
    "name": "tokenURI",
    "outputs": [{"name": "", "type": "string"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{"name": "tokenId", "type": "uint256"}],
    "name": "ownerOf",
    "outputs": [{"name": "", "type": "address"}],
    "stateMutability": "view",
    "type": "function"
  }
]
''',
        "package.json": '''{
  "name": "erc721-subgraph",
  "version": "0.1.0",
  "scripts": {
    "codegen": "graph codegen",
    "build": "graph build",
    "deploy": "graph deploy --node https://api.studio.thegraph.com/deploy/"
  },
  "dependencies": {
    "@graphprotocol/graph-cli": "0.71.0",
    "@graphprotocol/graph-ts": "0.32.0"
  }
}
''',
    },
    dependencies={
        "@graphprotocol/graph-cli": "0.71.0",
        "@graphprotocol/graph-ts": "0.32.0",
    },
    networks=["arbitrum-one", "arbitrum-sepolia"],
)


# DeFi Subgraph Template
DEFI_SUBGRAPH_TEMPLATE = IndexerTemplate(
    name="DeFi Subgraph",
    description="Index DEX swaps, liquidity pools, and trading activity",
    template_type="defi",
    features=[
        "Swap indexing",
        "Pool tracking",
        "Volume metrics",
        "Liquidity history",
    ],
    files={
        "subgraph.yaml": '''specVersion: 1.0.0
indexerHints:
  prune: auto
schema:
  file: ./schema.graphql
dataSources:
  - kind: ethereum
    name: Pool
    network: arbitrum-sepolia
    source:
      address: "0x0000000000000000000000000000000000000000"
      abi: Pool
      startBlock: 0
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
        - Pool
        - Swap
        - LiquidityEvent
      abis:
        - name: Pool
          file: ./abis/Pool.json
      eventHandlers:
        - event: Swap(indexed address,indexed address,int256,int256,uint160,uint128,int24)
          handler: handleSwap
        - event: Mint(address,indexed address,indexed int24,indexed int24,uint128,uint256,uint256)
          handler: handleMint
        - event: Burn(indexed address,indexed int24,indexed int24,uint128,uint256,uint256)
          handler: handleBurn
      file: ./src/mapping.ts
''',
        "schema.graphql": '''"""
Liquidity Pool
"""
type Pool @entity {
  id: Bytes! # Pool address
  token0: Bytes!
  token1: Bytes!
  fee: Int!
  liquidity: BigInt!
  sqrtPrice: BigInt!
  tick: Int!
  totalValueLockedToken0: BigDecimal!
  totalValueLockedToken1: BigDecimal!
  volumeToken0: BigDecimal!
  volumeToken1: BigDecimal!
  swapCount: BigInt!
  swaps: [Swap!]! @derivedFrom(field: "pool")
  liquidityEvents: [LiquidityEvent!]! @derivedFrom(field: "pool")
}

"""
Swap event
"""
type Swap @entity(immutable: true) {
  id: Bytes!
  pool: Pool!
  sender: Bytes!
  recipient: Bytes!
  amount0: BigInt!
  amount1: BigInt!
  sqrtPriceX96: BigInt!
  liquidity: BigInt!
  tick: Int!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}

"""
Liquidity add/remove event
"""
type LiquidityEvent @entity(immutable: true) {
  id: Bytes!
  pool: Pool!
  type: String! # "mint" or "burn"
  owner: Bytes!
  tickLower: Int!
  tickUpper: Int!
  amount: BigInt!
  amount0: BigInt!
  amount1: BigInt!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}

"""
Daily pool stats
"""
type PoolDayData @entity {
  id: ID! # pool-timestamp
  pool: Pool!
  date: Int!
  volumeToken0: BigDecimal!
  volumeToken1: BigDecimal!
  tvlToken0: BigDecimal!
  tvlToken1: BigDecimal!
  swapCount: BigInt!
}
''',
        "src/mapping.ts": '''import {
  Swap as SwapEvent,
  Mint as MintEvent,
  Burn as BurnEvent,
} from "../generated/Pool/Pool";
import { Pool, Swap, LiquidityEvent, PoolDayData } from "../generated/schema";
import { BigInt, BigDecimal, Bytes } from "@graphprotocol/graph-ts";

function getOrCreatePool(address: Bytes): Pool {
  let pool = Pool.load(address);
  if (pool == null) {
    pool = new Pool(address);
    pool.token0 = Bytes.empty();
    pool.token1 = Bytes.empty();
    pool.fee = 0;
    pool.liquidity = BigInt.zero();
    pool.sqrtPrice = BigInt.zero();
    pool.tick = 0;
    pool.totalValueLockedToken0 = BigDecimal.zero();
    pool.totalValueLockedToken1 = BigDecimal.zero();
    pool.volumeToken0 = BigDecimal.zero();
    pool.volumeToken1 = BigDecimal.zero();
    pool.swapCount = BigInt.zero();
    pool.save();
  }
  return pool;
}

export function handleSwap(event: SwapEvent): void {
  let pool = getOrCreatePool(event.address);

  let swap = new Swap(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  );
  swap.pool = pool.id;
  swap.sender = event.params.sender;
  swap.recipient = event.params.recipient;
  swap.amount0 = event.params.amount0;
  swap.amount1 = event.params.amount1;
  swap.sqrtPriceX96 = event.params.sqrtPriceX96;
  swap.liquidity = event.params.liquidity;
  swap.tick = event.params.tick;
  swap.blockNumber = event.block.number;
  swap.blockTimestamp = event.block.timestamp;
  swap.transactionHash = event.transaction.hash;
  swap.save();

  // Update pool stats
  pool.sqrtPrice = event.params.sqrtPriceX96;
  pool.liquidity = event.params.liquidity;
  pool.tick = event.params.tick;
  pool.swapCount = pool.swapCount.plus(BigInt.fromI32(1));

  // Update volume (absolute values)
  let volume0 = event.params.amount0.abs().toBigDecimal();
  let volume1 = event.params.amount1.abs().toBigDecimal();
  pool.volumeToken0 = pool.volumeToken0.plus(volume0);
  pool.volumeToken1 = pool.volumeToken1.plus(volume1);

  pool.save();
}

export function handleMint(event: MintEvent): void {
  let pool = getOrCreatePool(event.address);

  let mint = new LiquidityEvent(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  );
  mint.pool = pool.id;
  mint.type = "mint";
  mint.owner = event.params.owner;
  mint.tickLower = event.params.tickLower;
  mint.tickUpper = event.params.tickUpper;
  mint.amount = event.params.amount;
  mint.amount0 = event.params.amount0;
  mint.amount1 = event.params.amount1;
  mint.blockNumber = event.block.number;
  mint.blockTimestamp = event.block.timestamp;
  mint.transactionHash = event.transaction.hash;
  mint.save();

  // Update TVL
  pool.totalValueLockedToken0 = pool.totalValueLockedToken0.plus(
    event.params.amount0.toBigDecimal()
  );
  pool.totalValueLockedToken1 = pool.totalValueLockedToken1.plus(
    event.params.amount1.toBigDecimal()
  );
  pool.save();
}

export function handleBurn(event: BurnEvent): void {
  let pool = getOrCreatePool(event.address);

  let burn = new LiquidityEvent(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  );
  burn.pool = pool.id;
  burn.type = "burn";
  burn.owner = event.params.owner;
  burn.tickLower = event.params.tickLower;
  burn.tickUpper = event.params.tickUpper;
  burn.amount = event.params.amount;
  burn.amount0 = event.params.amount0;
  burn.amount1 = event.params.amount1;
  burn.blockNumber = event.block.number;
  burn.blockTimestamp = event.block.timestamp;
  burn.transactionHash = event.transaction.hash;
  burn.save();

  // Update TVL
  pool.totalValueLockedToken0 = pool.totalValueLockedToken0.minus(
    event.params.amount0.toBigDecimal()
  );
  pool.totalValueLockedToken1 = pool.totalValueLockedToken1.minus(
    event.params.amount1.toBigDecimal()
  );
  pool.save();
}
''',
        "abis/Pool.json": '''[
  {
    "anonymous": false,
    "inputs": [
      {"indexed": true, "name": "sender", "type": "address"},
      {"indexed": true, "name": "recipient", "type": "address"},
      {"indexed": false, "name": "amount0", "type": "int256"},
      {"indexed": false, "name": "amount1", "type": "int256"},
      {"indexed": false, "name": "sqrtPriceX96", "type": "uint160"},
      {"indexed": false, "name": "liquidity", "type": "uint128"},
      {"indexed": false, "name": "tick", "type": "int24"}
    ],
    "name": "Swap",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {"indexed": false, "name": "sender", "type": "address"},
      {"indexed": true, "name": "owner", "type": "address"},
      {"indexed": true, "name": "tickLower", "type": "int24"},
      {"indexed": true, "name": "tickUpper", "type": "int24"},
      {"indexed": false, "name": "amount", "type": "uint128"},
      {"indexed": false, "name": "amount0", "type": "uint256"},
      {"indexed": false, "name": "amount1", "type": "uint256"}
    ],
    "name": "Mint",
    "type": "event"
  },
  {
    "anonymous": false,
    "inputs": [
      {"indexed": true, "name": "owner", "type": "address"},
      {"indexed": true, "name": "tickLower", "type": "int24"},
      {"indexed": true, "name": "tickUpper", "type": "int24"},
      {"indexed": false, "name": "amount", "type": "uint128"},
      {"indexed": false, "name": "amount0", "type": "uint256"},
      {"indexed": false, "name": "amount1", "type": "uint256"}
    ],
    "name": "Burn",
    "type": "event"
  }
]
''',
        "package.json": '''{
  "name": "defi-subgraph",
  "version": "0.1.0",
  "scripts": {
    "codegen": "graph codegen",
    "build": "graph build",
    "deploy": "graph deploy --node https://api.studio.thegraph.com/deploy/"
  },
  "dependencies": {
    "@graphprotocol/graph-cli": "0.71.0",
    "@graphprotocol/graph-ts": "0.32.0"
  }
}
''',
    },
    dependencies={
        "@graphprotocol/graph-cli": "0.71.0",
        "@graphprotocol/graph-ts": "0.32.0",
    },
    networks=["arbitrum-one", "arbitrum-sepolia"],
)


# Custom Events Subgraph Template
CUSTOM_EVENTS_SUBGRAPH_TEMPLATE = IndexerTemplate(
    name="Custom Events Subgraph",
    description="Generic template for indexing custom contract events",
    template_type="custom",
    features=[
        "Configurable events",
        "Generic entity mapping",
        "Transaction tracking",
        "Block data",
    ],
    files={
        "subgraph.yaml": '''specVersion: 1.0.0
indexerHints:
  prune: auto
schema:
  file: ./schema.graphql
dataSources:
  - kind: ethereum
    name: Contract
    network: arbitrum-sepolia
    source:
      address: "0x0000000000000000000000000000000000000000"
      abi: Contract
      startBlock: 0
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
        - Event
        - Transaction
      abis:
        - name: Contract
          file: ./abis/Contract.json
      eventHandlers:
        # Add your custom events here
        - event: ValueChanged(indexed address,uint256,uint256)
          handler: handleValueChanged
      file: ./src/mapping.ts
''',
        "schema.graphql": '''"""
Generic event entity - customize for your needs
"""
type Event @entity(immutable: true) {
  id: Bytes!
  eventName: String!
  sender: Bytes!
  data: String!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}

"""
Transaction tracking
"""
type Transaction @entity {
  id: Bytes!
  from: Bytes!
  to: Bytes
  value: BigInt!
  gasPrice: BigInt!
  gasUsed: BigInt
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  events: [Event!]!
}

"""
Contract state snapshot
"""
type StateSnapshot @entity {
  id: ID! # contract-block
  contract: Bytes!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  data: String!
}
''',
        "src/mapping.ts": '''import { ValueChanged as ValueChangedEvent } from "../generated/Contract/Contract";
import { Event, Transaction } from "../generated/schema";
import { BigInt, Bytes, json } from "@graphprotocol/graph-ts";

export function handleValueChanged(event: ValueChangedEvent): void {
  // Create event entity
  let eventEntity = new Event(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  );
  eventEntity.eventName = "ValueChanged";
  eventEntity.sender = event.params.sender;
  eventEntity.data = JSON.stringify({
    oldValue: event.params.oldValue.toString(),
    newValue: event.params.newValue.toString(),
  });
  eventEntity.blockNumber = event.block.number;
  eventEntity.blockTimestamp = event.block.timestamp;
  eventEntity.transactionHash = event.transaction.hash;
  eventEntity.save();

  // Track transaction
  let tx = Transaction.load(event.transaction.hash);
  if (tx == null) {
    tx = new Transaction(event.transaction.hash);
    tx.from = event.transaction.from;
    tx.to = event.transaction.to;
    tx.value = event.transaction.value;
    tx.gasPrice = event.transaction.gasPrice;
    tx.gasUsed = null;
    tx.blockNumber = event.block.number;
    tx.blockTimestamp = event.block.timestamp;
    tx.events = [];
    tx.save();
  }

  // Add event to transaction
  let events = tx.events;
  events.push(eventEntity.id);
  tx.events = events;
  tx.save();
}

// Helper to stringify objects
function JSON_stringify(obj: Map<string, string>): string {
  let result = "{";
  let keys = obj.keys();
  for (let i = 0; i < keys.length; i++) {
    if (i > 0) result += ",";
    result += '"' + keys[i] + '":"' + obj.get(keys[i]) + '"';
  }
  return result + "}";
}
''',
        "abis/Contract.json": '''[
  {
    "anonymous": false,
    "inputs": [
      {"indexed": true, "name": "sender", "type": "address"},
      {"indexed": false, "name": "oldValue", "type": "uint256"},
      {"indexed": false, "name": "newValue", "type": "uint256"}
    ],
    "name": "ValueChanged",
    "type": "event"
  }
]
''',
        "package.json": '''{
  "name": "custom-subgraph",
  "version": "0.1.0",
  "scripts": {
    "codegen": "graph codegen",
    "build": "graph build",
    "deploy": "graph deploy --node https://api.studio.thegraph.com/deploy/"
  },
  "dependencies": {
    "@graphprotocol/graph-cli": "0.71.0",
    "@graphprotocol/graph-ts": "0.32.0"
  }
}
''',
    },
    dependencies={
        "@graphprotocol/graph-cli": "0.71.0",
        "@graphprotocol/graph-ts": "0.32.0",
    },
    networks=["arbitrum-one", "arbitrum-sepolia"],
)


# All templates indexed by type
INDEXER_TEMPLATES = {
    "erc20": ERC20_SUBGRAPH_TEMPLATE,
    "erc721": ERC721_SUBGRAPH_TEMPLATE,
    "defi": DEFI_SUBGRAPH_TEMPLATE,
    "custom": CUSTOM_EVENTS_SUBGRAPH_TEMPLATE,
}


def select_indexer_template(prompt: str) -> IndexerTemplate:
    """Select the best indexer template based on prompt keywords."""
    lower_prompt = prompt.lower()

    if any(kw in lower_prompt for kw in ["erc20", "token", "transfer", "balance"]):
        return ERC20_SUBGRAPH_TEMPLATE

    if any(kw in lower_prompt for kw in ["nft", "erc721", "721", "collectible", "ownership"]):
        return ERC721_SUBGRAPH_TEMPLATE

    if any(kw in lower_prompt for kw in ["swap", "dex", "liquidity", "pool", "defi"]):
        return DEFI_SUBGRAPH_TEMPLATE

    return CUSTOM_EVENTS_SUBGRAPH_TEMPLATE


def get_indexer_template(template_type: str) -> Optional[IndexerTemplate]:
    """Get a specific indexer template by type."""
    return INDEXER_TEMPLATES.get(template_type)


def list_indexer_templates() -> List[IndexerTemplate]:
    """List all available indexer templates."""
    return [
        ERC20_SUBGRAPH_TEMPLATE,
        ERC721_SUBGRAPH_TEMPLATE,
        DEFI_SUBGRAPH_TEMPLATE,
        CUSTOM_EVENTS_SUBGRAPH_TEMPLATE,
    ]
