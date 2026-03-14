export function GET() {
  const content = `# ARBuilder

> Accelerate smart contract and dApp development on Arbitrum with 19 AI-powered MCP tools

ARBuilder is an MCP (Model Context Protocol) server that helps developers ship smart contracts and dApps faster on Arbitrum. It works with Cursor, Claude Code, VS Code, and any MCP-compatible IDE.

## Tools

### M1: Stylus Smart Contracts (6 tools)
- get_stylus_context: RAG retrieval for Arbitrum Stylus docs and code examples
- generate_stylus_code: Generate Stylus contracts (Rust/WASM) from natural language
- ask_stylus: Q&A for Stylus development, debugging, concepts
- generate_tests: Generate unit, integration, and fuzz tests
- get_workflow: Build/deploy/test workflow guidance
- validate_stylus_code: Compile-check code via Docker cargo check

### M2: Arbitrum SDK Bridging (3 tools)
- generate_bridge_code: ETH/ERC20 bridging (L1<>L2, L1->L3, L3->L2)
- generate_messaging_code: Cross-chain messaging via retryable tickets
- ask_bridging: Bridging Q&A and patterns

### M3: Full dApp Builder (5 tools)
- generate_backend: NestJS/Express backend with viem integration
- generate_frontend: Next.js + wagmi + RainbowKit frontend
- generate_indexer: The Graph subgraph generation
- generate_oracle: Chainlink oracle integrations
- orchestrate_dapp: Full dApp scaffolding coordinator

### M4: Orbit Chain Integration (5 tools)
- generate_orbit_config: Orbit chain configuration (Rollup, AnyTrust, custom gas tokens)
- generate_orbit_deployment: Rollup and token bridge deployment
- generate_validator_setup: Validator, batch poster, and DAC keyset management
- ask_orbit: Orbit chain Q&A
- orchestrate_orbit: Full Orbit chain project scaffolding

## Quick Start

Hosted (no setup):
\`\`\`
claude mcp add arbbuilder -- npx -y mcp-remote https://arbuilder.app/mcp --header "Authorization: Bearer YOUR_API_KEY"
\`\`\`

## Links
- Website: https://arbuilder.app
- GitHub: https://github.com/Quantum3-Labs/ARBuilder
- Playground: https://arbuilder.app/playground
`;

  return new Response(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
