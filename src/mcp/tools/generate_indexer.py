"""
generate_indexer MCP Tool.

Generates The Graph subgraph code for indexing Arbitrum smart contract events.
"""

import re
from typing import Optional

from .base import BaseTool
from .get_stylus_context import GetStylusContextTool


SYSTEM_PROMPT = """You are an expert in The Graph protocol and subgraph development for Arbitrum.

Key patterns to follow:

## Subgraph Structure:
1. subgraph.yaml - Manifest file defining data sources
2. schema.graphql - Entity definitions
3. src/mapping.ts - Event handlers in AssemblyScript

## Schema Design:
1. Use @entity directive for storable types
2. Use ID type for entity identifiers
3. Use BigInt for large numbers, Bytes for addresses/hashes
4. Define relationships with @derivedFrom
5. Add indexes for frequently queried fields

## Mapping Handlers:
1. Import entities from generated schema
2. Use event.params to access event data
3. Use event.block and event.transaction for metadata
4. Load or create entities with Entity.load() and new Entity()
5. Always save entities with entity.save()

## Best Practices:
1. Use meaningful entity IDs (e.g., txHash-logIndex)
2. Track cumulative metrics with aggregation entities
3. Handle entity relationships properly
4. Use helper functions for common operations
5. Follow AssemblyScript limitations

## Arbitrum Specific:
1. Use correct network names: arbitrum-one, arbitrum-sepolia
2. Set appropriate startBlock for efficiency
3. Handle Arbitrum-specific features if needed

When generating code:
- Generate complete subgraph configuration
- Include all necessary entity definitions
- Write proper event handlers
- Add package.json with graph-cli
"""

SUBGRAPH_YAML_TEMPLATE = '''specVersion: 1.0.0
schema:
  file: ./schema.graphql
dataSources:
  - kind: ethereum
    name: {contractName}
    network: {network}
    source:
      address: "{contractAddress}"
      abi: {contractName}
      startBlock: {startBlock}
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
{entities}
      abis:
        - name: {contractName}
          file: ./abis/{contractName}.json
      eventHandlers:
{eventHandlers}
      file: ./src/mapping.ts
'''

SCHEMA_TEMPLATE = '''"""
{entityName} entity
"""
type {entityName} @entity {{
  id: ID!
  # Add fields here
  createdAt: BigInt!
  createdAtBlock: BigInt!
  transactionHash: Bytes!
}}
'''

MAPPING_TEMPLATE = '''import {{ BigInt, Bytes }} from "@graphprotocol/graph-ts";
import {{
  {eventNames}
}} from "../generated/{contractName}/{contractName}";
import {{
  {entityNames}
}} from "../generated/schema";

// Helper function to generate unique IDs
function createId(txHash: Bytes, logIndex: BigInt): string {{
  return txHash.toHexString() + "-" + logIndex.toString();
}}

// Event handlers will be generated based on the ABI
'''


class GenerateIndexerTool(BaseTool):
    """
    Generates The Graph subgraph code for indexing contract events.

    Uses RAG context to inform code generation with relevant examples.
    """

    def __init__(
        self,
        context_tool: Optional[GetStylusContextTool] = None,
        **kwargs,
    ):
        """
        Initialize the tool.

        Args:
            context_tool: GetStylusContextTool for retrieving examples.
        """
        super().__init__(**kwargs)
        self.context_tool = context_tool or GetStylusContextTool(**kwargs)

    def execute(
        self,
        prompt: str,
        contract_address: str = "0x0000000000000000000000000000000000000000",
        contract_abi: Optional[str] = None,
        contract_name: str = "Contract",
        network: str = "arbitrum-one",
        entities: Optional[list[str]] = None,
        start_block: int = 0,
        temperature: float = 0.2,
        **kwargs,
    ) -> dict:
        """
        Generate subgraph code.

        Args:
            prompt: Description of what to index.
            contract_address: Deployed contract address.
            contract_abi: Contract ABI with events.
            contract_name: Name of the contract.
            network: Network to deploy to (arbitrum-one, arbitrum-sepolia).
            entities: Entity names to track.
            start_block: Block number to start indexing from.
            temperature: Generation temperature (0-1).

        Returns:
            Dict with files, package_json, explanation, warnings, context_used.
        """
        if not prompt or not prompt.strip():
            return {"error": "Prompt is required and cannot be empty"}

        prompt = prompt.strip()
        entities = entities or []
        warnings = []

        if network not in ["arbitrum-one", "arbitrum-sepolia"]:
            warnings.append(f"Unknown network '{network}', defaulting to arbitrum-one")
            network = "arbitrum-one"

        try:
            # Retrieve relevant context
            context_used = []
            context_text = ""

            context_result = self.context_tool.execute(
                query=f"subgraph graphql event handler mapping entity arbitrum {prompt}",
                n_results=5,
                content_type="code",
                rerank=True,
            )

            if "contexts" in context_result:
                for ctx in context_result["contexts"]:
                    context_used.append({
                        "source": ctx["source"],
                        "relevance": ctx["relevance_score"],
                    })
                    context_text += f"\n--- Example from {ctx['source']} ---\n{ctx['content'][:1500]}\n"

            # Parse events from ABI if provided
            parsed_events = []
            if contract_abi:
                parsed_events = self._parse_events_from_abi(contract_abi)

            # Build generation prompt
            user_prompt = self._build_prompt(
                prompt=prompt,
                contract_address=contract_address,
                contract_name=contract_name,
                network=network,
                entities=entities,
                parsed_events=parsed_events,
                start_block=start_block,
                context_text=context_text,
            )

            # Generate code
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            response = self._call_llm(
                messages=messages,
                temperature=temperature,
                max_tokens=8192,
            )

            # Parse response
            files = self._parse_files(response)
            explanation = self._extract_explanation(response)

            # Generate package.json
            package_json = self._generate_package_json()

            # Add base files if missing
            files = self._add_base_files(
                files,
                contract_name,
                contract_address,
                network,
                entities,
                parsed_events,
                start_block,
                prompt,
            )

            return {
                "files": files,
                "package_json": package_json,
                "explanation": explanation,
                "warnings": warnings if warnings else [],
                "context_used": context_used,
                "network": network,
                "events_found": [e["name"] for e in parsed_events],
                "prerequisites": {
                    "required": ["node >= 18", "npm >= 9", "graph-cli"],
                    "install": {
                        "macos": "brew install node && npm install -g @graphprotocol/graph-cli",
                        "linux": "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs && npm install -g @graphprotocol/graph-cli",
                        "windows": "Download Node.js from https://nodejs.org/ then run: npm install -g @graphprotocol/graph-cli",
                    },
                    "verify": "node --version && npm --version && graph --version",
                },
            }

        except Exception as e:
            return {"error": f"Indexer generation failed: {str(e)}"}

    def _parse_events_from_abi(self, abi_string: str) -> list[dict]:
        """Parse event definitions from ABI."""
        import json

        try:
            abi = json.loads(abi_string)
        except json.JSONDecodeError:
            return []

        events = []
        for item in abi:
            if item.get("type") == "event":
                events.append({
                    "name": item.get("name", ""),
                    "inputs": item.get("inputs", []),
                })

        return events

    def _build_prompt(
        self,
        prompt: str,
        contract_address: str,
        contract_name: str,
        network: str,
        entities: list[str],
        parsed_events: list[dict],
        start_block: int,
        context_text: str,
    ) -> str:
        """Build the generation prompt."""
        parts = []

        parts.append("Generate a complete subgraph for The Graph protocol with:")
        parts.append(f"- Contract name: {contract_name}")
        parts.append(f"- Contract address: {contract_address}")
        parts.append(f"- Network: {network}")
        parts.append(f"- Start block: {start_block}")
        parts.append("")

        # Add entity hints
        if entities:
            parts.append(f"Required entities: {', '.join(entities)}")

        # Add parsed events
        if parsed_events:
            parts.append("\nEvents to handle from ABI:")
            for event in parsed_events:
                inputs_str = ", ".join([
                    f"{inp.get('name', 'arg')}: {inp.get('type', 'unknown')}"
                    for inp in event.get("inputs", [])
                ])
                parts.append(f"  - {event['name']}({inputs_str})")
        else:
            # Infer events from prompt keywords
            inferred_events = self._infer_events_from_prompt(prompt)
            if inferred_events:
                parts.append("\nInferred events to handle (based on requirements):")
                for event in inferred_events:
                    parts.append(f"  - {event}")

        # Add context if available
        if context_text:
            parts.append("\nHere are some relevant subgraph examples for reference:")
            parts.append(context_text)

        # Add main request
        parts.append(f"\nGenerate subgraph code for the following requirement:")
        parts.append(f"\n{prompt}\n")

        parts.append("\nProvide the following files with EXACT format:")
        parts.append("1. subgraph.yaml - Manifest configuration with proper eventHandlers")
        parts.append("2. schema.graphql - Entity definitions with proper types and relationships")
        parts.append("3. src/mapping.ts - Event handlers in AssemblyScript with full implementation")
        parts.append("")
        parts.append("IMPORTANT: Include complete event handler implementations, not placeholders.")
        parts.append("Format each file with: // path/to/file.ext followed by a code block.")

        return "\n".join(parts)

    def _infer_events_from_prompt(self, prompt: str) -> list[str]:
        """Infer common events from prompt keywords."""
        prompt_lower = prompt.lower()
        events = []

        # ERC20 events
        if "transfer" in prompt_lower or "erc20" in prompt_lower or "token" in prompt_lower:
            events.append("Transfer(address indexed from, address indexed to, uint256 value)")
        if "approval" in prompt_lower or "approve" in prompt_lower:
            events.append("Approval(address indexed owner, address indexed spender, uint256 value)")

        # ERC721/NFT events
        if "nft" in prompt_lower or "erc721" in prompt_lower:
            events.append("Transfer(address indexed from, address indexed to, uint256 indexed tokenId)")
            if "approval" in prompt_lower:
                events.append("Approval(address indexed owner, address indexed approved, uint256 indexed tokenId)")

        # DEX/AMM events
        if "swap" in prompt_lower or "dex" in prompt_lower or "amm" in prompt_lower:
            events.append("Swap(address indexed sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, address indexed to)")
        if "liquidity" in prompt_lower or "mint" in prompt_lower:
            events.append("Mint(address indexed sender, uint256 amount0, uint256 amount1)")
        if "burn" in prompt_lower:
            events.append("Burn(address indexed sender, uint256 amount0, uint256 amount1, address indexed to)")

        return events

    def _parse_files(self, response: str) -> list[dict]:
        """Parse files from LLM response."""
        files = []

        # Match code blocks with optional file path comments
        file_pattern = r'(?:\/\/\s*|#\s*)?([a-zA-Z0-9_\-\/\.]+\.(?:yaml|yml|graphql|ts|json))\s*\n```(?:yaml|graphql|typescript|json)?\s*\n([\s\S]*?)```'

        matches = re.findall(file_pattern, response)

        for path, content in matches:
            path = path.strip()
            content = content.strip()

            # Normalize path
            if path.endswith(".ts") and not path.startswith("src/"):
                path = f"src/{path}"

            files.append({
                "path": path,
                "content": content,
            })

        return files

    def _extract_explanation(self, response: str) -> str:
        """Extract explanation from response."""
        parts = response.split("```")
        if len(parts) > 1:
            explanation = parts[-1].strip()
            if explanation:
                return explanation

        return "Generated subgraph for indexing smart contract events."

    def _generate_package_json(self) -> dict:
        """Generate package.json content."""
        return {
            "name": "subgraph",
            "version": "1.0.0",
            "scripts": {
                "codegen": "graph codegen",
                "build": "graph build",
                "deploy": "graph deploy --node https://api.studio.thegraph.com/deploy/",
                "create-local": "graph create --node http://localhost:8020/ subgraph",
                "remove-local": "graph remove --node http://localhost:8020/ subgraph",
                "deploy-local": "graph deploy --node http://localhost:8020/ --ipfs http://localhost:5001 subgraph",
                "test": "graph test",
            },
            "dependencies": {
                "@graphprotocol/graph-cli": "^0.68.0",
                "@graphprotocol/graph-ts": "^0.32.0",
            },
            "devDependencies": {
                "matchstick-as": "^0.6.0",
            },
        }

    def _add_base_files(
        self,
        files: list[dict],
        contract_name: str,
        contract_address: str,
        network: str,
        entities: list[str],
        parsed_events: list[dict],
        start_block: int,
        prompt: str = "",
    ) -> list[dict]:
        """Add base files if not present in generated files."""
        file_paths = [f["path"] for f in files]

        # Infer events from prompt if not provided
        inferred_event_names = []
        if not parsed_events and prompt:
            inferred = self._infer_events_from_prompt(prompt)
            # Extract just the event names
            inferred_event_names = [e.split("(")[0] for e in inferred]

        # Add subgraph.yaml if not present
        if not any("subgraph.yaml" in p for p in file_paths):
            # Build entities list - use inferred events if no entities specified
            if entities:
                entities_list = entities
            elif inferred_event_names:
                entities_list = inferred_event_names
            else:
                entities_list = ["Entity"]
            entities_yaml = "\n".join([f"        - {e}" for e in entities_list])

            # Build event handlers
            if parsed_events:
                handlers_yaml = "\n".join([
                    f"        - event: {e['name']}({','.join([inp.get('type', 'uint256') for inp in e.get('inputs', [])])})\n          handler: handle{e['name']}"
                    for e in parsed_events
                ])
            elif inferred_event_names:
                # Generate handlers for inferred events
                handlers_yaml = "\n".join([
                    f"        - event: {e}(address indexed from, address indexed to, uint256 value)\n          handler: handle{e}"
                    for e in inferred_event_names
                ])
            else:
                handlers_yaml = "        # Add event handlers here"

            subgraph_yaml = SUBGRAPH_YAML_TEMPLATE.format(
                contractName=contract_name,
                contractAddress=contract_address,
                network=network,
                startBlock=start_block,
                entities=entities_yaml,
                eventHandlers=handlers_yaml,
            )

            files.append({
                "path": "subgraph.yaml",
                "content": subgraph_yaml,
            })

        # Add schema.graphql if not present
        if not any("schema.graphql" in p for p in file_paths):
            schema_parts = []
            entity_names = entities or inferred_event_names or ["Entity"]
            for entity_name in entity_names:
                schema_parts.append(SCHEMA_TEMPLATE.format(entityName=entity_name))
            files.append({
                "path": "schema.graphql",
                "content": "\n".join(schema_parts),
            })

        # Add mapping.ts if not present
        if not any("mapping.ts" in p for p in file_paths):
            if parsed_events:
                event_names = ", ".join([e["name"] for e in parsed_events])
            elif inferred_event_names:
                event_names = ", ".join(inferred_event_names)
            else:
                event_names = "Transfer"

            entity_names = ", ".join(entities) if entities else (", ".join(inferred_event_names) if inferred_event_names else "Entity")

            mapping_content = MAPPING_TEMPLATE.format(
                eventNames=event_names,
                contractName=contract_name,
                entityNames=entity_names,
            )

            files.append({
                "path": "src/mapping.ts",
                "content": mapping_content,
            })

        # Add .gitignore
        gitignore_content = """node_modules/
build/
generated/
.env
"""
        if not any(".gitignore" in p for p in file_paths):
            files.append({
                "path": ".gitignore",
                "content": gitignore_content,
            })

        # Add deploy instructions
        readme_content = f"""# {contract_name} Subgraph

This subgraph indexes events from the {contract_name} contract on {network}.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Generate types:
   ```bash
   npm run codegen
   ```

3. Build:
   ```bash
   npm run build
   ```

4. Deploy to The Graph Studio:
   ```bash
   npm run deploy
   ```

## Contract

- Address: `{contract_address}`
- Network: {network}
- Start Block: {start_block}
"""
        if not any("README" in p.upper() for p in file_paths):
            files.append({
                "path": "README.md",
                "content": readme_content,
            })

        return files
