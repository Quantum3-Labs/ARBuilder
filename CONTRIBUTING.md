# Contributing to ARBuilder

Thanks for your interest in contributing to ARBuilder! This guide will help you get started.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ARBuilder.git
   cd ARBuilder
   ```
3. Set up the development environment:
   ```bash
   conda env create -f environment.yml
   conda activate arbbuilder
   ```
4. Create a branch for your work:
   ```bash
   git checkout -b feat/your-feature-name
   ```

## Development Workflow

### Code Quality

Before submitting, make sure your code passes linting and tests:

```bash
# Python formatting and linting
black .
ruff check .

# Run tests
pytest tests/ -v

# TypeScript type checking (if modifying apps/web)
cd apps/web && npx tsc --noEmit
```

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `test:` — Adding or updating tests
- `refactor:` — Code changes that neither fix a bug nor add a feature

### Pull Requests

1. Keep PRs focused — one feature or fix per PR
2. Update `README.md` and relevant docs for architectural changes
3. Add tests for new MCP tools
4. Make sure all existing tests pass
5. Write a clear PR description explaining what and why

## Project Structure

The codebase has two main parts:

- **Python (`src/`)** — MCP server, RAG pipeline, templates, and tools (self-hosted)
- **TypeScript (`apps/web/`)** — Hosted service on Cloudflare Workers (Next.js + Workers AI)

When adding or modifying tools, keep both implementations in sync.

### Adding a New MCP Tool

1. Create a tool class in `src/mcp/tools/` inheriting from `BaseTool`
2. Define `name`, `description`, and `input_schema`
3. Implement the `execute()` method
4. Register it in `src/mcp/tools/__init__.py`
5. Add the TypeScript equivalent in `apps/web/src/lib/tools/`
6. Add an API route in `apps/web/src/app/api/v1/tools/`
7. Add tests in `tests/mcp_tools/`

### Updating the Knowledge Base

If you're adding new documentation sources:

1. Add entries to `sources.json`
2. Run the local pipeline: `python -m scraper.run && python -m src.preprocessing.processor`
3. Verify with `python scripts/audit_data.py`

## Stylus Code Guidelines

When working on Stylus-related templates or tools, follow the conventions documented in [CLAUDE.md](CLAUDE.md) under "Stylus Development Guidelines". Key points:

- Target SDK `0.10.0` (use `self.vm()` API, not deprecated `msg::sender()`)
- Package names must use underscores, not hyphens
- Include `Stylus.toml`, `rust-toolchain.toml`, and `src/main.rs`

## Reporting Issues

- Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) template for bugs
- Use the [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) template for new ideas
- Check existing issues before creating a new one

## Questions?

- Open a [Discussion](https://github.com/Quantum3-Labs/ARBuilder/discussions) for general questions
- Join the [Arbitrum Discord](https://discord.gg/arbitrum) #stylus channel
