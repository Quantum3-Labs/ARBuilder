"""
Generate backend code for dApps.

Supports:
- NestJS with Stylus contract integration
- Express with Stylus contract integration
- NestJS with GraphQL for subgraph querying
- API Gateway for cross-chain operations
"""

import json
from typing import Any, Optional

from .base import BaseTool
from ...templates.backend_templates import (
    BackendTemplate,
    select_backend_template,
    get_backend_template,
    list_backend_templates,
    NESTJS_STYLUS_TEMPLATE,
    EXPRESS_STYLUS_TEMPLATE,
    NESTJS_GRAPHQL_TEMPLATE,
    API_GATEWAY_TEMPLATE,
)


class GenerateBackendTool(BaseTool):
    """Generate backend code for dApps with Web3 integration."""

    name = "generate_backend"
    description = """Generate TypeScript backend code for Arbitrum dApps.

Supports:
- NestJS with Stylus contract integration (viem)
- Express with Stylus contract integration (lightweight)
- NestJS with GraphQL for subgraph querying
- API Gateway for cross-chain L1/L2/L3 operations

The generated code includes controllers, services, and configuration files."""

    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the backend functionality needed",
            },
            "framework": {
                "type": "string",
                "enum": ["nestjs", "express"],
                "description": "Backend framework to use",
                "default": "nestjs",
            },
            "template": {
                "type": "string",
                "enum": ["nestjs_stylus", "express_stylus", "nestjs_graphql", "api_gateway"],
                "description": "Specific template to use (optional, auto-selected if not provided)",
            },
            "contract_abi": {
                "type": "string",
                "description": "Contract ABI JSON string (optional, uses default if not provided)",
            },
            "contract_address": {
                "type": "string",
                "description": "Contract address to integrate with",
            },
            "include_tests": {
                "type": "boolean",
                "description": "Include test files",
                "default": False,
            },
        },
        "required": ["prompt"],
    }

    def __init__(self, vectordb=None):
        """Initialize with optional vector database for context."""
        super().__init__()
        self.vectordb = vectordb

    def execute(self, **kwargs) -> dict[str, Any]:
        """Generate backend code based on the request."""
        prompt = kwargs.get("prompt", "")
        framework = kwargs.get("framework", "nestjs")
        template_name = kwargs.get("template")
        contract_abi = kwargs.get("contract_abi")
        contract_address = kwargs.get("contract_address", "0x...")
        include_tests = kwargs.get("include_tests", False)

        # Validate inputs
        if not prompt:
            return {"error": "prompt is required"}

        # Select template
        if template_name:
            template = get_backend_template(template_name)
            if not template:
                return {"error": f"Unknown template: {template_name}"}
        else:
            template = select_backend_template(framework, prompt)

        # Context retrieval (template-based generation doesn't require RAG)
        context = []

        # Customize template based on prompt
        files = self._customize_template(template, prompt, contract_abi, contract_address)

        # Generate package.json
        package_json = self._generate_package_json(template, prompt)

        # Add test files if requested
        if include_tests:
            test_files = self._generate_tests(template, prompt)
            files.update(test_files)

        # Build response
        result = {
            "template_used": template.name,
            "framework": template.framework,
            "files": files,
            "package_json": package_json,
            "dependencies": template.dependencies,
            "dev_dependencies": template.dev_dependencies,
            "env_vars": template.env_vars,
            "scripts": template.scripts,
            "setup_instructions": self._get_setup_instructions(template),
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
        template: BackendTemplate,
        prompt: str,
        contract_abi: Optional[str],
        contract_address: str,
    ) -> dict[str, str]:
        """Customize template files based on user requirements."""
        files = dict(template.files)

        # Replace placeholder contract address
        for path, content in files.items():
            if "0x0000000000000000000000000000000000000000" in content:
                files[path] = content.replace(
                    "0x0000000000000000000000000000000000000000",
                    contract_address,
                )
            if "0x..." in content:
                files[path] = content.replace("0x...", contract_address)

        # If custom ABI provided, update contract configuration
        if contract_abi:
            try:
                abi = json.loads(contract_abi)
                abi_content = self._generate_abi_file(abi)

                # Add or update ABI configuration based on framework
                if template.framework == "nestjs":
                    files["src/contract/contract.abi.ts"] = abi_content
                else:
                    files["src/config/contract.abi.ts"] = abi_content
            except json.JSONDecodeError:
                pass  # Use default ABI

        return files

    def _generate_abi_file(self, abi: list) -> str:
        """Generate TypeScript ABI file from JSON ABI."""
        abi_json = json.dumps(abi, indent=2)
        return f'''import {{ parseAbi }} from 'viem';

// Contract ABI
export const CONTRACT_ABI = {abi_json} as const;

// For viem usage, parse the ABI
export const PARSED_ABI = parseAbi([
  // Add function signatures here
]);
'''

    def _generate_package_json(self, template: BackendTemplate, prompt: str) -> dict:
        """Generate package.json content."""
        # Derive package name from prompt
        words = prompt.lower().split()[:3]
        name = "-".join(w for w in words if w.isalnum())[:20] or "dapp-backend"

        return {
            "name": name,
            "version": "0.1.0",
            "description": f"Backend for: {prompt[:100]}",
            "scripts": template.scripts,
            "dependencies": template.dependencies,
            "devDependencies": template.dev_dependencies,
        }

    def _generate_tests(self, template: BackendTemplate, prompt: str) -> dict[str, str]:
        """Generate test files for the backend."""
        tests = {}

        if template.framework == "nestjs":
            tests["test/contract.e2e-spec.ts"] = '''import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';
import { AppModule } from '../src/app.module';

describe('ContractController (e2e)', () => {
  let app: INestApplication;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  it('/health (GET)', () => {
    return request(app.getHttpServer())
      .get('/health')
      .expect(200)
      .expect((res) => {
        expect(res.body.status).toBe('ok');
      });
  });

  it('/contract/number (GET)', () => {
    return request(app.getHttpServer())
      .get('/contract/number')
      .expect(200)
      .expect((res) => {
        expect(res.body).toHaveProperty('number');
      });
  });
});
'''
            tests["test/jest-e2e.json"] = '''{
  "moduleFileExtensions": ["js", "json", "ts"],
  "rootDir": ".",
  "testEnvironment": "node",
  "testRegex": ".e2e-spec.ts$",
  "transform": {
    "^.+\\\\.(t|j)s$": "ts-jest"
  }
}
'''

        elif template.framework == "express":
            tests["test/contract.test.ts"] = '''import request from 'supertest';
import express from 'express';
import { contractRouter } from '../src/routes/contract';
import { healthRouter } from '../src/routes/health';

const app = express();
app.use(express.json());
app.use('/health', healthRouter);
app.use('/contract', contractRouter);

describe('API Tests', () => {
  describe('GET /health', () => {
    it('should return status ok', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('ok');
    });
  });

  describe('GET /contract/number', () => {
    it('should return a number', async () => {
      const res = await request(app).get('/contract/number');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('number');
    });
  });
});
'''

        return tests

    def _get_setup_instructions(self, template: BackendTemplate) -> list[str]:
        """Get setup instructions for the template."""
        instructions = [
            "1. Create a new directory and copy the generated files",
            "2. Copy .env.example to .env and fill in the values",
            "3. Run: npm install",
        ]

        if template.framework == "nestjs":
            instructions.extend([
                "4. Run in development: npm run start:dev",
                "5. Build for production: npm run build",
                "6. Run in production: npm run start:prod",
            ])
        else:
            instructions.extend([
                "4. Run in development: npm run dev",
                "5. Build: npm run build",
                "6. Run in production: npm start",
            ])

        return instructions
