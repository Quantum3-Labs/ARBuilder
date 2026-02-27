/**
 * Generate The Graph subgraph for Arbitrum contracts (M3 tool)
 */

export const TEMPLATE_DISCLAIMER =
  "This generated code is a starting entrypoint — a working foundation for you to build upon. " +
  "Review, customize, and extend it to match your specific requirements before deploying.";

type SubgraphType = "erc20" | "erc721" | "defi" | "custom";

interface GenerateIndexerArgs {
  contractAddress: string;
  subgraphType?: SubgraphType;
  abi?: string;
  events?: string[];
  network?: string;
}

interface GenerateIndexerResult {
  files: Record<string, string>;
  dependencies: Record<string, string>;
  commands: string[];
  setupInstructions: string[];
  disclaimer: string;
}

// ERC20 Subgraph Template
const ERC20_TEMPLATE = {
  schema: `"""
Token entity
"""
type Token @entity {
  id: Bytes! # Contract address
  name: String!
  symbol: String!
  decimals: Int!
  totalSupply: BigInt!
  holderCount: BigInt!
  transferCount: BigInt!
}

"""
Account entity
"""
type Account @entity {
  id: Bytes! # Address
  balance: BigInt!
  transfersFrom: [Transfer!]! @derivedFrom(field: "from")
  transfersTo: [Transfer!]! @derivedFrom(field: "to")
}

"""
Transfer event (immutable)
"""
type Transfer @entity(immutable: true) {
  id: Bytes! # tx hash + log index
  from: Account!
  to: Account!
  value: BigInt!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}

"""
Approval event (immutable)
"""
type Approval @entity(immutable: true) {
  id: Bytes!
  owner: Account!
  spender: Bytes!
  value: BigInt!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}
`,

  mapping: `import { BigInt, Bytes, Address } from "@graphprotocol/graph-ts";
import { Transfer as TransferEvent, Approval as ApprovalEvent } from "../generated/Token/Token";
import { Token, Account, Transfer, Approval } from "../generated/schema";

function getOrCreateAccount(address: Address): Account {
  let account = Account.load(address);
  if (account == null) {
    account = new Account(address);
    account.balance = BigInt.zero();
    account.save();
  }
  return account;
}

function getOrCreateToken(address: Address): Token {
  let token = Token.load(address);
  if (token == null) {
    token = new Token(address);
    token.name = "Unknown";
    token.symbol = "???";
    token.decimals = 18;
    token.totalSupply = BigInt.zero();
    token.holderCount = BigInt.zero();
    token.transferCount = BigInt.zero();
    token.save();
  }
  return token;
}

export function handleTransfer(event: TransferEvent): void {
  let id = event.transaction.hash.concatI32(event.logIndex.toI32());

  // Update accounts
  let from = getOrCreateAccount(event.params.from);
  let to = getOrCreateAccount(event.params.to);

  from.balance = from.balance.minus(event.params.value);
  from.save();

  to.balance = to.balance.plus(event.params.value);
  to.save();

  // Create transfer entity
  let transfer = new Transfer(id);
  transfer.from = from.id;
  transfer.to = to.id;
  transfer.value = event.params.value;
  transfer.blockNumber = event.block.number;
  transfer.blockTimestamp = event.block.timestamp;
  transfer.transactionHash = event.transaction.hash;
  transfer.save();

  // Update token stats
  let token = getOrCreateToken(event.address);
  token.transferCount = token.transferCount.plus(BigInt.fromI32(1));
  token.save();
}

export function handleApproval(event: ApprovalEvent): void {
  let id = event.transaction.hash.concatI32(event.logIndex.toI32());
  let owner = getOrCreateAccount(event.params.owner);

  let approval = new Approval(id);
  approval.owner = owner.id;
  approval.spender = event.params.spender;
  approval.value = event.params.value;
  approval.blockNumber = event.block.number;
  approval.blockTimestamp = event.block.timestamp;
  approval.transactionHash = event.transaction.hash;
  approval.save();
}
`,

  abi: [
    {
      anonymous: false,
      inputs: [
        { indexed: true, name: "from", type: "address" },
        { indexed: true, name: "to", type: "address" },
        { indexed: false, name: "value", type: "uint256" },
      ],
      name: "Transfer",
      type: "event",
    },
    {
      anonymous: false,
      inputs: [
        { indexed: true, name: "owner", type: "address" },
        { indexed: true, name: "spender", type: "address" },
        { indexed: false, name: "value", type: "uint256" },
      ],
      name: "Approval",
      type: "event",
    },
  ],
};

// ERC721 Subgraph Template
const ERC721_TEMPLATE = {
  schema: `"""
NFT Collection
"""
type Collection @entity {
  id: Bytes! # Contract address
  name: String!
  symbol: String!
  totalMinted: BigInt!
  uniqueOwners: BigInt!
  tokens: [Token!]! @derivedFrom(field: "collection")
}

"""
Individual NFT Token
"""
type Token @entity {
  id: ID! # collection-tokenId
  tokenId: BigInt!
  collection: Collection!
  owner: Account!
  uri: String
  mintedAt: BigInt!
  transfers: [Transfer!]! @derivedFrom(field: "token")
}

"""
Account that owns NFTs
"""
type Account @entity {
  id: Bytes!
  tokens: [Token!]! @derivedFrom(field: "owner")
  transfersFrom: [Transfer!]! @derivedFrom(field: "from")
  transfersTo: [Transfer!]! @derivedFrom(field: "to")
}

"""
Transfer event (immutable)
"""
type Transfer @entity(immutable: true) {
  id: Bytes!
  token: Token!
  from: Account!
  to: Account!
  blockNumber: BigInt!
  blockTimestamp: BigInt!
  transactionHash: Bytes!
}
`,

  mapping: `import { BigInt, Bytes, Address } from "@graphprotocol/graph-ts";
import { Transfer as TransferEvent } from "../generated/NFT/NFT";
import { Collection, Token, Account, Transfer } from "../generated/schema";

const ZERO_ADDRESS = Address.fromString("0x0000000000000000000000000000000000000000");

function getOrCreateAccount(address: Address): Account {
  let account = Account.load(address);
  if (account == null) {
    account = new Account(address);
    account.save();
  }
  return account;
}

function getOrCreateCollection(address: Address): Collection {
  let collection = Collection.load(address);
  if (collection == null) {
    collection = new Collection(address);
    collection.name = "Unknown";
    collection.symbol = "???";
    collection.totalMinted = BigInt.zero();
    collection.uniqueOwners = BigInt.zero();
    collection.save();
  }
  return collection;
}

export function handleTransfer(event: TransferEvent): void {
  let collection = getOrCreateCollection(event.address);
  let from = getOrCreateAccount(event.params.from);
  let to = getOrCreateAccount(event.params.to);

  let tokenId = collection.id.toHexString() + "-" + event.params.tokenId.toString();
  let token = Token.load(tokenId);

  // Mint event
  if (event.params.from.equals(ZERO_ADDRESS)) {
    token = new Token(tokenId);
    token.tokenId = event.params.tokenId;
    token.collection = collection.id;
    token.owner = to.id;
    token.mintedAt = event.block.timestamp;
    token.save();

    collection.totalMinted = collection.totalMinted.plus(BigInt.fromI32(1));
    collection.save();
  } else if (token != null) {
    token.owner = to.id;
    token.save();
  }

  // Create transfer record
  let transferId = event.transaction.hash.concatI32(event.logIndex.toI32());
  let transfer = new Transfer(transferId);
  transfer.token = tokenId;
  transfer.from = from.id;
  transfer.to = to.id;
  transfer.blockNumber = event.block.number;
  transfer.blockTimestamp = event.block.timestamp;
  transfer.transactionHash = event.transaction.hash;
  transfer.save();
}
`,

  abi: [
    {
      anonymous: false,
      inputs: [
        { indexed: true, name: "from", type: "address" },
        { indexed: true, name: "to", type: "address" },
        { indexed: true, name: "tokenId", type: "uint256" },
      ],
      name: "Transfer",
      type: "event",
    },
  ],
};

/**
 * Map a Solidity type to the corresponding GraphQL type for subgraph schemas.
 */
function solidityToGraphqlType(solType: string): string {
  const t = solType.trim();

  if (t === "address") return "Bytes!";
  if (t === "bool") return "Boolean!";
  if (t === "string") return "String!";
  if (/^u?int\d*$/.test(t)) return "BigInt!";
  if (/^bytes\d*$/.test(t)) return "Bytes!";

  // Default fallback for unknown types
  return "Bytes!";
}

interface AbiEventInput {
  name: string;
  type: string;
  indexed: boolean;
}

interface AbiEvent {
  name: string;
  inputs: AbiEventInput[];
}

/**
 * Generate dynamic schema.graphql and mapping.ts from parsed ABI events.
 * One entity per event, one handler per event.
 */
function generateCustomSubgraph(
  events: AbiEvent[],
  eventSignatures: string[]
): { schema: string; mapping: string } {
  // --- schema.graphql ---
  const entityBlocks = events.map((ev) => {
    const fields = [
      "  id: Bytes!",
      ...ev.inputs.map(
        (inp) => `  ${inp.name}: ${solidityToGraphqlType(inp.type)}`
      ),
      "  blockNumber: BigInt!",
      "  blockTimestamp: BigInt!",
      "  transactionHash: Bytes!",
    ];
    return `type ${ev.name} @entity(immutable: true) {\n${fields.join("\n")}\n}`;
  });
  const schema = entityBlocks.join("\n\n") + "\n";

  // --- mapping.ts ---
  const eventImports = events
    .map((ev) => `${ev.name} as ${ev.name}Event`)
    .join(", ");
  const entityImports = events.map((ev) => ev.name).join(", ");

  const handlers = events.map((ev) => {
    const paramAssignments = ev.inputs
      .map((inp) => `  entity.${inp.name} = event.params.${inp.name};`)
      .join("\n");

    return `export function handle${ev.name}(event: ${ev.name}Event): void {
  let entity = new ${ev.name}(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  );

${paramAssignments}
  entity.blockNumber = event.block.number;
  entity.blockTimestamp = event.block.timestamp;
  entity.transactionHash = event.transaction.hash;
  entity.save();
}`;
  });

  const mapping = `import { BigInt, Bytes, Address } from "@graphprotocol/graph-ts";
import { ${eventImports} } from "../generated/Contract/Contract";
import { ${entityImports} } from "../generated/schema";

${handlers.join("\n\n")}
`;

  return { schema, mapping };
}

function generateSubgraphYaml(
  contractAddress: string,
  network: string,
  events: string[],
  abiName: string,
  entities?: string[]
): string {
  const eventHandlers = events
    .map((event) => {
      const name = event.split("(")[0];
      return `        - event: ${event}
          handler: handle${name}`;
    })
    .join("\n");

  const entityList = entities ?? ["Token", "Account", "Transfer", "Approval"];
  const entityLines = entityList
    .map((e) => `        - ${e}`)
    .join("\n");

  return `specVersion: 1.0.0
indexerHints:
  prune: auto
schema:
  file: ./schema.graphql
dataSources:
  - kind: ethereum
    name: ${abiName}
    network: ${network}
    source:
      address: "${contractAddress}"
      abi: ${abiName}
      startBlock: 0  # Update to contract deployment block
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
${entityLines}
      abis:
        - name: ${abiName}
          file: ./abis/${abiName}.json
      eventHandlers:
${eventHandlers}
      file: ./src/mapping.ts
`;
}

export function generateIndexer(args: GenerateIndexerArgs): GenerateIndexerResult {
  const {
    contractAddress,
    subgraphType = "erc20",
    abi,
    events,
    network = "arbitrum-sepolia",
  } = args;

  const files: Record<string, string> = {};

  // Select template based on type
  let template = ERC20_TEMPLATE;
  let abiName = "Token";
  let eventSignatures = [
    "Transfer(indexed address,indexed address,uint256)",
    "Approval(indexed address,indexed address,uint256)",
  ];

  if (subgraphType === "erc721") {
    template = ERC721_TEMPLATE;
    abiName = "NFT";
    eventSignatures = ["Transfer(indexed address,indexed address,indexed uint256)"];
  } else if (subgraphType === "custom" && abi) {
    // Parse ABI to extract event items for custom subgraphs
    let parsedAbi: Array<Record<string, unknown>> = [];
    try {
      parsedAbi = JSON.parse(abi);
    } catch {
      // Invalid ABI — fall through to default ERC20 template
    }

    if (parsedAbi.length > 0) {
      // Extract all event items from the ABI
      let abiEvents: AbiEvent[] = parsedAbi
        .filter((item) => item.type === "event")
        .map((item) => ({
          name: item.name as string,
          inputs: (item.inputs as Array<Record<string, unknown>>).map((inp) => ({
            name: inp.name as string,
            type: inp.type as string,
            indexed: inp.indexed as boolean,
          })),
        }));

      // If specific event names were provided, filter to only those
      if (events && events.length > 0) {
        abiEvents = abiEvents.filter((ev) => events.includes(ev.name));
      }

      if (abiEvents.length > 0) {
        // Build event signatures from parsed ABI events
        eventSignatures = abiEvents.map((ev) => {
          const params = ev.inputs
            .map((inp) => (inp.indexed ? `indexed ${inp.type}` : inp.type))
            .join(",");
          return `${ev.name}(${params})`;
        });

        abiName = "Contract";
        const customEntityNames = abiEvents.map((ev) => ev.name);
        const { schema, mapping } = generateCustomSubgraph(
          abiEvents,
          eventSignatures
        );

        files["schema.graphql"] = schema;
        files["src/mapping.ts"] = mapping;
        files[`abis/${abiName}.json`] = JSON.stringify(parsedAbi, null, 2);
        files["subgraph.yaml"] = generateSubgraphYaml(
          contractAddress,
          network,
          eventSignatures,
          abiName,
          customEntityNames
        );
      }
    }
  } else if (subgraphType === "custom" && events) {
    // Custom with raw event signatures but no ABI — keep ERC20 template schema/mapping
    eventSignatures = events;
  }

  // Use provided ABI or template ABI (only if files weren't already set by custom branch)
  if (!files["schema.graphql"]) {
    let contractAbi: unknown = template.abi;
    if (abi) {
      try {
        contractAbi = JSON.parse(abi);
      } catch {
        // Invalid ABI, use template
      }
    }

    files["schema.graphql"] = template.schema;
    files["src/mapping.ts"] = template.mapping;
    files[`abis/${abiName}.json`] = JSON.stringify(contractAbi, null, 2);
    files["subgraph.yaml"] = generateSubgraphYaml(
      contractAddress,
      network,
      eventSignatures,
      abiName
    );
  }

  // Package.json
  files["package.json"] = JSON.stringify(
    {
      name: "arbbuilder-subgraph",
      version: "1.0.0",
      scripts: {
        codegen: "graph codegen",
        build: "graph build",
        deploy: "graph deploy --studio arbbuilder-subgraph",
        test: "graph test",
      },
      dependencies: {
        "@graphprotocol/graph-cli": "0.71.0",
        "@graphprotocol/graph-ts": "0.32.0",
      },
      devDependencies: {
        "matchstick-as": "0.6.0",
      },
    },
    null,
    2
  );

  // tsconfig for AssemblyScript
  files["tsconfig.json"] = JSON.stringify(
    {
      extends: "@graphprotocol/graph-ts/tsconfig.json",
      compilerOptions: {
        outDir: "build",
      },
      include: ["src/**/*.ts"],
    },
    null,
    2
  );

  return {
    files,
    dependencies: {
      "@graphprotocol/graph-cli": "0.71.0",
      "@graphprotocol/graph-ts": "0.32.0",
    },
    commands: [
      "npm install",
      "npm run codegen",
      "npm run build",
      "graph auth --studio YOUR_DEPLOY_KEY",
      "npm run deploy",
    ],
    setupInstructions: [
      "1. Install dependencies: npm install",
      "2. Update startBlock in subgraph.yaml to contract deployment block",
      "3. Run codegen: npm run codegen",
      "4. Build: npm run build",
      "5. Create subgraph at studio.thegraph.com",
      "6. Authenticate: graph auth --studio YOUR_DEPLOY_KEY",
      "7. Deploy: npm run deploy",
    ],
    disclaimer: TEMPLATE_DISCLAIMER,
  };
}
