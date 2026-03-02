# ARBuilder Tutorial Video Script

**Duration:** 8-12 minutes
**Deliverable:** SOW #2 - Tutorial video (installation, configuration, usage)

---

## Recording Checklist

### Pre-Recording Setup
- [ ] Clean desktop background
- [ ] Close unnecessary applications
- [ ] Cursor/VS Code with dark theme (better for video)
- [ ] Terminal with large, readable font (14pt+)
- [ ] Screen resolution: 1920x1080 or 2560x1440
- [ ] Microphone tested (clear audio, no echo)
- [ ] API keys ready (will blur in post)
- [ ] Fresh conda environment for demo
- [ ] ChromaDB populated with data
- [ ] Test all demo prompts beforehand

### Recording Software
- [ ] OBS Studio or similar
- [ ] Record at 1080p minimum, 60fps preferred
- [ ] Separate audio track for easier editing

### Post-Recording
- [ ] Blur any API keys or sensitive info
- [ ] Add chapter markers/timestamps
- [ ] Add intro/outro graphics
- [ ] Upload to YouTube (unlisted or public)
- [ ] Add to README with link

---

## Detailed Script

### Scene 1: Introduction (0:00 - 0:30)

**[Screen: ARBuilder logo or GitHub repo page]**

> "Welcome to ARBuilder - an AI-powered development assistant for the Arbitrum ecosystem.
>
> In this tutorial, you'll learn how to:
> - Install ARBuilder locally or use our hosted service
> - Configure it with Cursor or VS Code
> - Generate Stylus smart contracts, bridging code, and full-stack dApps
>
> Let's get started."

---

### Scene 2: Installation Option A - Self-Hosted (0:30 - 2:30)

**[Screen: Terminal]**

> "First, let's set up ARBuilder locally for full control."

**Action: Type commands**

```bash
# Clone the repository
git clone https://github.com/Quantum3-Labs/arbbuilder.git
cd arbbuilder
```

> "Clone the repository from GitHub."

```bash
# Create conda environment
conda env create -f environment.yml
conda activate arbbuilder
```

> "Create and activate the conda environment. This installs all dependencies including the vector database and MCP server."

```bash
# Copy environment template
cp .env.example .env
```

> "Copy the environment template. You'll need an OpenRouter API key."

**[Screen: Show .env file briefly, blur API key]**

```env
OPENROUTER_API_KEY=your-api-key-here
```

> "Add your OpenRouter API key. You can get one at openrouter.ai."

```bash
# Generate the vector database
python -m src.embeddings.vectordb
```

> "Finally, generate the vector database. This embeds all the Stylus documentation and code examples for RAG retrieval."

> "The self-hosted option gives you full control and no rate limits."

---

### Scene 3: Installation Option B - Hosted Service (2:30 - 3:30)

**[Screen: Browser at arbuilder.app]**

> "Alternatively, use our hosted service for zero setup."

**Action: Navigate to website**

> "Go to arbuilder.app and sign up for a free account."

**[Screen: Dashboard with API key]**

> "From the dashboard, copy your API key. The free tier includes 100 API calls per day."

> "This option requires no local setup - just configure your IDE and start building."

---

### Scene 4: Configuration - Cursor (3:30 - 5:00)

**[Screen: Cursor IDE]**

> "Now let's configure ARBuilder with Cursor."

**Action: Open MCP config file**

> "Open your MCP configuration file."

**[Screen: Show file path]**
- macOS: `~/.cursor/mcp.json`
- Windows: `%APPDATA%\Cursor\mcp.json`

**For Hosted Service:**

```json
{
  "mcpServers": {
    "arbbuilder": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://arbuilder.app/mcp",
        "--header",
        "Authorization: Bearer YOUR_API_KEY"
      ]
    }
  }
}
```

> "For the hosted service, use mcp-remote with your API key."

**For Self-Hosted:**

```json
{
  "mcpServers": {
    "arbbuilder": {
      "command": "/path/to/conda/envs/arbbuilder/bin/python3",
      "args": ["-m", "src.mcp.server"],
      "env": {
        "OPENROUTER_API_KEY": "your-api-key",
        "PYTHONPATH": "/path/to/arbbuilder"
      }
    }
  }
}
```

> "For self-hosted, point to your Python environment and set the paths."

**Action: Save and restart Cursor**

> "Save the file and restart Cursor. You should see the ARBuilder tools available."

**[Screen: Show MCP tools list in Cursor]**

> "ARBuilder provides 8 tools for Stylus contracts, bridging, and dApp generation."

---

### Scene 5: Demo - Stylus Code Generation (5:00 - 7:00)

**[Screen: Cursor chat interface]**

> "Let's generate a Stylus smart contract. I'll ask Claude to create an ERC20 token."

**Prompt 1: Generate Contract**

```
Create an ERC20 token called "MyToken" with symbol "MTK" and 1 million initial supply using Stylus
```

**[Wait for response, show generated code]**

> "ARBuilder retrieves relevant patterns from the knowledge base and generates a complete ERC20 contract in Rust."

**[Highlight key parts of the generated code]**

> "Notice it includes proper imports from stylus-sdk, storage definitions, and all required ERC20 methods."

---

**Prompt 2: Q&A**

```
How do I handle reentrancy protection in Stylus?
```

**[Wait for response]**

> "The ask_stylus tool provides accurate answers with code examples from official documentation."

---

**Prompt 3: Generate Tests**

```
Generate unit tests for this ERC20 contract
```

**[Wait for response]**

> "ARBuilder generates comprehensive tests using the motsu testing framework."

---

**Prompt 4: Get Workflow**

```
How do I deploy this contract to Arbitrum Sepolia?
```

**[Wait for response showing deployment steps]**

> "The get_workflow tool provides step-by-step deployment commands with network configurations."

---

### Scene 6: Demo - Arbitrum SDK Bridging (7:00 - 8:30)

**[Screen: New chat or continue]**

> "Now let's generate bridging code using the Arbitrum SDK."

**Prompt 1: ETH Bridging**

```
Generate code to deposit ETH from Ethereum to Arbitrum
```

**[Wait for response]**

> "ARBuilder generates TypeScript code using the EthBridger class with proper gas estimation and status tracking."

---

**Prompt 2: Cross-Chain Messaging**

```
Generate code for L1 to L2 messaging with retryable tickets
```

**[Wait for response]**

> "This generates complete retryable ticket code including gas estimation via NodeInterface."

---

**Prompt 3: Bridging Q&A**

```
How long does an L2 to L1 withdrawal take?
```

**[Wait for response]**

> "The ask_bridging tool explains the 7-day challenge period and provides context about the withdrawal process."

---

### Scene 7: Demo - Full dApp Generation (8:30 - 10:00)

**[Screen: New chat]**

> "Finally, let's generate a complete full-stack dApp."

**Prompt:**

```
Generate a full-stack NFT marketplace dApp with minting, listing, and buying functionality
```

**[Wait for response - this may take longer]**

> "ARBuilder orchestrates multiple generators to create a complete monorepo."

**[Show the generated structure]**

> "We get:
> - A Stylus smart contract for the NFT marketplace
> - A NestJS backend with Web3 integration
> - A Next.js frontend with RainbowKit wallet connection
> - A subgraph for indexing marketplace events
> - And an integration guide for connecting everything"

**[Scroll through some of the generated code]**

> "Each component follows production patterns from real Arbitrum projects in our knowledge base."

---

### Scene 8: Wrap-up (10:00 - 10:30)

**[Screen: GitHub repo or website]**

> "That's ARBuilder - your AI-powered assistant for building on Arbitrum.
>
> To get started:
> - Visit our GitHub repo to set up locally
> - Or use our hosted service at arbuilder.app
>
> If you found this helpful, please star the repository and share it with other developers.
>
> Happy building on Arbitrum!"

**[Screen: Links overlay]**
- GitHub: github.com/Quantum3-Labs/arbbuilder
- Hosted: arbuilder.app
- Docs: (link to documentation)

---

## Timestamps for YouTube

```
0:00 Introduction
0:30 Installation - Self-Hosted
2:30 Installation - Hosted Service
3:30 Configuration - Cursor/VS Code
5:00 Demo - Stylus Smart Contracts
7:00 Demo - Arbitrum SDK Bridging
8:30 Demo - Full dApp Generation
10:00 Wrap-up & Resources
```

---

## Backup Prompts (if primary ones fail)

### Stylus
- "Create a simple counter contract in Stylus"
- "Show me how to use storage mappings in Stylus"
- "Generate a vending machine contract in Rust"

### Bridging
- "Generate code to withdraw ETH from Arbitrum to Ethereum"
- "How do retryable tickets work?"
- "Generate ERC20 token bridging code"

### Full dApp
- "Generate a token staking dApp"
- "Create a simple voting dApp with frontend"

---

## Notes for Recording

1. **Pace**: Speak slowly and clearly. Viewers can speed up but can't slow down.

2. **Pauses**: Allow 2-3 seconds after each prompt for the response to generate.

3. **Errors**: If a tool returns an error, either re-record or explain the error and retry.

4. **Length**: Aim for 10 minutes. Better to have extra footage than not enough.

5. **Editing**: Plan for 20-30% to be cut in editing.
