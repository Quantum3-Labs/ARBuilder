"""
Generate subgraph indexer code for The Graph.

Supports:
- ERC20 token indexing (transfers, balances, holders)
- ERC721 NFT indexing (ownership, metadata, transfers)
- DeFi protocol indexing (swaps, liquidity, pools)
- Custom event indexing (configurable)
"""

import json
from typing import Any, Optional

from .base import BaseTool
from ...templates.indexer_templates import (
    IndexerTemplate,
    select_indexer_template,
    get_indexer_template,
    list_indexer_templates,
    ERC20_SUBGRAPH_TEMPLATE,
    ERC721_SUBGRAPH_TEMPLATE,
    DEFI_SUBGRAPH_TEMPLATE,
    CUSTOM_EVENTS_SUBGRAPH_TEMPLATE,
)
# Removed: agentic_rag import (template-based generation)


class GenerateIndexerTool(BaseTool):
    """Generate subgraph code for The Graph protocol."""

    name = "generate_indexer"
    description = """Generate subgraph code for indexing Arbitrum contracts with The Graph.

Supports:
- ERC20 token subgraphs (transfers, balances, holders)
- ERC721 NFT subgraphs (ownership, metadata, transfers)
- DeFi subgraphs (swaps, liquidity pools, volume)
- Custom event subgraphs (configurable)

The generated code includes schema.graphql, mappings, and configuration."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the indexing requirements",
            },
            "template": {
                "type": "string",
                "enum": ["erc20", "erc721", "defi", "custom"],
                "description": "Type of subgraph template to use",
            },
            "contract_address": {
                "type": "string",
                "description": "Contract address to index",
            },
            "contract_abi": {
                "type": "string",
                "description": "Contract ABI JSON string for custom events",
            },
            "start_block": {
                "type": "integer",
                "description": "Block number to start indexing from",
                "default": 0,
            },
            "network": {
                "type": "string",
                "enum": ["arbitrum-one", "arbitrum-sepolia"],
                "description": "Network to deploy the subgraph",
                "default": "arbitrum-sepolia",
            },
            "events": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of event names to index (for custom template)",
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database for context."""
        super().__init__()
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate subgraph code based on the request."""
        prompt = kwargs.get("prompt", "")
        template_name = kwargs.get("template")
        contract_address = kwargs.get("contract_address", "0x0000000000000000000000000000000000000000")
        contract_abi = kwargs.get("contract_abi")
        start_block = kwargs.get("start_block", 0)
        network = kwargs.get("network", "arbitrum-sepolia")
        events = kwargs.get("events", [])

        # Validate inputs
        if not prompt:
            return {"error": "prompt is required"}

        # Select template
        if template_name:
            template = get_indexer_template(template_name)
            if not template:
                return {"error": f"Unknown template: {template_name}"}
        else:
            template = select_indexer_template(prompt)

        # Context retrieval (template-based generation doesn't require RAG)
        context = []

        # Customize template
        files = self._customize_template(
            template,
            prompt,
            contract_address,
            contract_abi,
            start_block,
            network,
            events,
        )

        # Build response
        result = {
            "template_used": template.name,
            "template_type": template.template_type,
            "files": files,
            "dependencies": template.dependencies,
            "networks": template.networks,
            "setup_instructions": self._get_setup_instructions(template, network),
            "deployment_commands": self._get_deployment_commands(network),
        }

        if context:
            result["references"] = [
                {
                    "source": c.get("metadata", {}).get("source", "Unknown"),
                    "relevance": c.get("distance", 0),
                }
                for c in context[:3]
            ]

        return result

    def _customize_template(
        self,
        template: IndexerTemplate,
        prompt: str,
        contract_address: str,
        contract_abi: Optional[str],
        start_block: int,
        network: str,
        events: list[str],
    ) -> dict[str, str]:
        """Customize template files based on user requirements."""
        files = dict(template.files)

        # Update subgraph.yaml with actual values
        if "subgraph.yaml" in files:
            yaml_content = files["subgraph.yaml"]
            yaml_content = yaml_content.replace(
                "0x0000000000000000000000000000000000000000",
                contract_address,
            )
            yaml_content = yaml_content.replace(
                "startBlock: 0",
                f"startBlock: {start_block}",
            )
            yaml_content = yaml_content.replace(
                "network: arbitrum-sepolia",
                f"network: {network}",
            )
            files["subgraph.yaml"] = yaml_content

        # If custom ABI provided, generate custom handlers
        if contract_abi and template.template_type == "custom":
            try:
                abi = json.loads(contract_abi)
                custom_files = self._generate_custom_subgraph(abi, events, contract_address, network, start_block)
                files.update(custom_files)
            except json.JSONDecodeError:
                pass  # Use default template

        return files

    def _generate_custom_subgraph(
        self,
        abi: list,
        events: list[str],
        contract_address: str,
        network: str,
        start_block: int,
    ) -> dict[str, str]:
        """Generate custom subgraph from ABI."""
        files = {}

        # Filter events from ABI
        event_items = [
            item for item in abi
            if item.get("type") == "event"
            and (not events or item.get("name") in events)
        ]

        if not event_items:
            return {
                "warning": (
                    "No indexable events found in the provided ABI. "
                    "Custom subgraphs require at least one event definition. "
                    "Ensure your ABI contains event entries, e.g.: "
                    '{"type": "event", "name": "Transfer", "inputs": [...]}'
                ),
            }

        # Generate schema.graphql
        schema_lines = ['"""', "Custom indexed events", '"""']
        for event in event_items:
            name = event.get("name", "Event")
            schema_lines.append(f"\ntype {name} @entity(immutable: true) {{")
            schema_lines.append("  id: Bytes!")

            for inp in event.get("inputs", []):
                inp_name = inp.get("name", "field")
                inp_type = self._solidity_to_graphql_type(inp.get("type", ""))
                schema_lines.append(f"  {inp_name}: {inp_type}!")

            schema_lines.append("  blockNumber: BigInt!")
            schema_lines.append("  blockTimestamp: BigInt!")
            schema_lines.append("  transactionHash: Bytes!")
            schema_lines.append("}")

        files["schema.graphql"] = "\n".join(schema_lines)

        # Generate mapping.ts
        mapping_lines = ['import { BigInt, Bytes } from "@graphprotocol/graph-ts";']

        # Add event imports
        for event in event_items:
            name = event.get("name", "Event")
            mapping_lines.append(f'import {{ {name} as {name}Event }} from "../generated/Contract/Contract";')

        # Add entity imports
        entity_names = [event.get("name", "Event") for event in event_items]
        mapping_lines.append(f'import {{ {", ".join(entity_names)} }} from "../generated/schema";')
        mapping_lines.append("")

        # Generate handlers
        for event in event_items:
            name = event.get("name", "Event")
            mapping_lines.append(f"export function handle{name}(event: {name}Event): void {{")
            mapping_lines.append(f"  let entity = new {name}(")
            mapping_lines.append("    event.transaction.hash.concatI32(event.logIndex.toI32())")
            mapping_lines.append("  );")
            mapping_lines.append("")

            for inp in event.get("inputs", []):
                inp_name = inp.get("name", "field")
                mapping_lines.append(f"  entity.{inp_name} = event.params.{inp_name};")

            mapping_lines.append("  entity.blockNumber = event.block.number;")
            mapping_lines.append("  entity.blockTimestamp = event.block.timestamp;")
            mapping_lines.append("  entity.transactionHash = event.transaction.hash;")
            mapping_lines.append("  entity.save();")
            mapping_lines.append("}")
            mapping_lines.append("")

        files["src/mapping.ts"] = "\n".join(mapping_lines)

        # Generate subgraph.yaml
        event_handlers = []
        for event in event_items:
            name = event.get("name", "Event")
            inputs = event.get("inputs", [])

            # Build event signature
            params = ",".join(
                f"{'indexed ' if i.get('indexed') else ''}{i.get('type', '')}"
                for i in inputs
            )
            event_handlers.append(f"        - event: {name}({params})")
            event_handlers.append(f"          handler: handle{name}")

        yaml_content = f'''specVersion: 1.0.0
indexerHints:
  prune: auto
schema:
  file: ./schema.graphql
dataSources:
  - kind: ethereum
    name: Contract
    network: {network}
    source:
      address: "{contract_address}"
      abi: Contract
      startBlock: {start_block}
    mapping:
      kind: ethereum/events
      apiVersion: 0.0.7
      language: wasm/assemblyscript
      entities:
{chr(10).join(f"        - {e.get('name', 'Event')}" for e in event_items)}
      abis:
        - name: Contract
          file: ./abis/Contract.json
      eventHandlers:
{chr(10).join(event_handlers)}
      file: ./src/mapping.ts
'''
        files["subgraph.yaml"] = yaml_content

        # Generate ABI file
        files["abis/Contract.json"] = json.dumps(abi, indent=2)

        return files

    def _solidity_to_graphql_type(self, sol_type: str) -> str:
        """Convert Solidity type to GraphQL type."""
        type_map = {
            "address": "Bytes",
            "bool": "Boolean",
            "string": "String",
            "bytes": "Bytes",
            "bytes32": "Bytes",
        }

        # Handle uint/int types
        if sol_type.startswith("uint") or sol_type.startswith("int"):
            return "BigInt"

        return type_map.get(sol_type, "Bytes")

    def _get_setup_instructions(self, template: IndexerTemplate, network: str) -> list[str]:
        """Get setup instructions for the subgraph."""
        return [
            "1. Install dependencies: npm install",
            "2. Create a subgraph on Subgraph Studio: https://thegraph.com/studio/",
            "3. Authenticate: graph auth --studio <deploy-key>",
            "4. Generate types: npm run codegen",
            "5. Build: npm run build",
            "6. Deploy: npm run deploy",
            f"7. Query your subgraph at the studio URL for {network}",
        ]

    def _get_deployment_commands(self, network: str) -> dict[str, str]:
        """Get deployment commands for different environments."""
        return {
            "codegen": "graph codegen",
            "build": "graph build",
            "deploy_studio": "graph deploy --studio <subgraph-name>",
            "deploy_hosted": f"graph deploy --node https://api.thegraph.com/deploy/ --ipfs https://api.thegraph.com/ipfs/ <github-user>/<subgraph-name>",
            "create_local": "graph create --node http://localhost:8020/ <subgraph-name>",
            "deploy_local": "graph deploy --node http://localhost:8020/ --ipfs http://localhost:5001 <subgraph-name>",
        }
