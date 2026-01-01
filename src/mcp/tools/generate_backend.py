"""
generate_backend MCP Tool.

Generates NestJS/Express backend code with Web3 integration for Arbitrum dApps.
"""

import re
from typing import Optional

from .base import BaseTool
from .get_stylus_context import GetStylusContextTool


SYSTEM_PROMPT = """You are an expert Web3 backend developer specializing in NestJS and Express applications for Arbitrum dApps.

Key patterns to follow:

## NestJS:
1. Use modular architecture with separate modules for each feature
2. Use dependency injection for services
3. Use DTOs for request/response validation with class-validator
4. Use @Controller, @Injectable, @Module decorators properly
5. Use ConfigService for environment variables
6. Use ethers.js or viem for Web3 interactions

## Express:
1. Use router-based architecture
2. Use middleware for auth, validation, error handling
3. Use service layer pattern for business logic
4. Use environment variables with dotenv

## Web3 Integration:
1. Use viem or ethers.js for contract interactions
2. Store ABIs in dedicated files
3. Use proper error handling for blockchain calls
4. Handle transaction status and confirmations
5. Support Arbitrum One and Arbitrum Sepolia networks

## Security:
1. Validate all inputs
2. Use rate limiting for RPC calls
3. Never expose private keys
4. Use environment variables for sensitive data
5. Implement proper CORS configuration

When generating code:
- Generate complete, runnable code with all imports
- Include package.json dependencies
- Add helpful comments for complex logic
- Follow TypeScript best practices
- Include error handling
"""

NESTJS_TEMPLATES = {
    "module": '''import { Module } from '@nestjs/common';
import { {Name}Controller } from './{name}.controller';
import { {Name}Service } from './{name}.service';

@Module({{
  controllers: [{Name}Controller],
  providers: [{Name}Service],
  exports: [{Name}Service],
}})
export class {Name}Module {{}}
''',
    "controller": '''import {{ Controller, Get, Post, Body, Param }} from '@nestjs/common';
import {{ {Name}Service }} from './{name}.service';

@Controller('{route}')
export class {Name}Controller {{
  constructor(private readonly {name}Service: {Name}Service) {{}}

  // Add endpoints here
}}
''',
    "service": '''import {{ Injectable }} from '@nestjs/common';
import {{ createPublicClient, createWalletClient, http }} from 'viem';
import {{ arbitrum, arbitrumSepolia }} from 'viem/chains';

@Injectable()
export class {Name}Service {{
  private readonly publicClient;

  constructor() {{
    this.publicClient = createPublicClient({{
      chain: arbitrum,
      transport: http(),
    }});
  }}

  // Add service methods here
}}
''',
    "web3_service": '''import { Injectable, OnModuleInit, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  createPublicClient,
  createWalletClient,
  http,
  type Address,
} from 'viem';
import { arbitrum, arbitrumSepolia } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';

@Injectable()
export class Web3Service implements OnModuleInit {
  private readonly logger = new Logger(Web3Service.name);
  private publicClient: any;
  private walletClient: any = null;
  private chain: any;

  constructor(private configService: ConfigService) {}

  onModuleInit() {
    const network = this.configService.get<string>('NETWORK', 'arbitrum-sepolia');
    this.chain = network === 'arbitrum' ? arbitrum : arbitrumSepolia;

    const rpcUrl = this.configService.get<string>('RPC_URL') ||
      (this.chain.id === arbitrum.id
        ? 'https://arb1.arbitrum.io/rpc'
        : 'https://sepolia-rollup.arbitrum.io/rpc');

    this.publicClient = createPublicClient({
      chain: this.chain,
      transport: http(rpcUrl),
    });

    const privateKey = this.configService.get<string>('PRIVATE_KEY');
    if (privateKey) {
      const account = privateKeyToAccount(privateKey as `0x${string}`);
      this.walletClient = createWalletClient({
        account,
        chain: this.chain,
        transport: http(rpcUrl),
      });
      this.logger.log('Wallet client initialized');
    }
  }

  async readContract<T>(address: Address, abi: any, functionName: string, args?: any[]): Promise<T> {
    return this.publicClient.readContract({
      address,
      abi,
      functionName,
      args,
    }) as Promise<T>;
  }

  async writeContract(address: Address, abi: any, functionName: string, args?: any[]) {
    if (!this.walletClient) {
      throw new Error('Wallet not configured - set PRIVATE_KEY env variable');
    }
    const { request } = await this.publicClient.simulateContract({
      address,
      abi,
      functionName,
      args,
      account: this.walletClient.account,
    });
    return this.walletClient.writeContract(request);
  }

  async getBalance(address: Address): Promise<bigint> {
    return this.publicClient.getBalance({ address });
  }

  async waitForTransaction(hash: `0x${string}`) {
    return this.publicClient.waitForTransactionReceipt({ hash });
  }

  getChain(): Chain {
    return this.chain;
  }
}
''',
}

EXPRESS_TEMPLATES = {
    "server": '''import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { config } from 'dotenv';
import { router } from './routes';
import { errorHandler } from './middleware/error';

config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Routes
app.use('/api', router);

// Error handling
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
''',
    "router": '''import { Router } from 'express';
// Import route modules here

export const router = Router();

// Add routes here
// router.use('/contracts', contractRoutes);
''',
    "web3_service": '''import {
  createPublicClient,
  createWalletClient,
  http,
  Address,
} from 'viem';
import { arbitrum, arbitrumSepolia } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';

const network = process.env.NETWORK || 'arbitrum';
const chain = network === 'arbitrum' ? arbitrum : arbitrumSepolia;

export const publicClient = createPublicClient({
  chain,
  transport: http(process.env.RPC_URL),
});

const privateKey = process.env.PRIVATE_KEY;
export const walletClient = privateKey
  ? createWalletClient({
      account: privateKeyToAccount(privateKey as `0x${string}`),
      chain,
      transport: http(process.env.RPC_URL),
    })
  : null;

export async function readContract(
  address: Address,
  abi: any,
  functionName: string,
  args?: any[],
) {
  return publicClient.readContract({
    address,
    abi,
    functionName,
    args,
  });
}

export async function writeContract(
  address: Address,
  abi: any,
  functionName: string,
  args?: any[],
) {
  if (!walletClient) {
    throw new Error('Wallet not configured');
  }
  return walletClient.writeContract({
    address,
    abi,
    functionName,
    args,
  });
}
''',
}


class GenerateBackendTool(BaseTool):
    """
    Generates NestJS/Express backend code with Web3 integration.

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
        framework: str = "nestjs",
        features: Optional[list[str]] = None,
        contract_abi: Optional[str] = None,
        database: str = "postgresql",
        temperature: float = 0.2,
        **kwargs,
    ) -> dict:
        """
        Generate backend code.

        Args:
            prompt: Description of the backend to generate.
            framework: "nestjs" or "express" (default: nestjs).
            features: List of features to include (auth, database, web3, api).
            contract_abi: Optional ABI to generate contract interactions.
            database: Database type (postgresql, mongodb, none).
            temperature: Generation temperature (0-1).

        Returns:
            Dict with files, package_json, explanation, warnings, context_used.
        """
        if not prompt or not prompt.strip():
            return {"error": "Prompt is required and cannot be empty"}

        prompt = prompt.strip()
        features = features or ["api", "web3"]
        framework = framework.lower()
        warnings = []

        if framework not in ["nestjs", "express"]:
            warnings.append(f"Unknown framework '{framework}', defaulting to nestjs")
            framework = "nestjs"

        try:
            # Retrieve relevant context
            context_used = []
            context_text = ""

            context_result = self.context_tool.execute(
                query=f"backend api {framework} web3 viem ethers arbitrum {prompt}",
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

            # Build generation prompt
            user_prompt = self._build_prompt(
                prompt=prompt,
                framework=framework,
                features=features,
                contract_abi=contract_abi,
                database=database,
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
            package_json = self._generate_package_json(framework, features, database)

            # Add base files if missing
            files = self._add_base_files(files, framework)

            return {
                "files": files,
                "package_json": package_json,
                "explanation": explanation,
                "warnings": warnings if warnings else [],
                "context_used": context_used,
                "framework": framework,
                "prerequisites": {
                    "required": ["node >= 18", "npm >= 9"],
                    "install": {
                        "macos": "brew install node",
                        "linux": "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs",
                        "windows": "Download from https://nodejs.org/",
                    },
                    "verify": "node --version && npm --version",
                },
            }

        except Exception as e:
            return {"error": f"Backend generation failed: {str(e)}"}

    def _build_prompt(
        self,
        prompt: str,
        framework: str,
        features: list[str],
        contract_abi: Optional[str],
        database: str,
        context_text: str,
    ) -> str:
        """Build the generation prompt."""
        parts = []

        # Add framework template hints
        if framework == "nestjs":
            parts.append("Generate a NestJS backend application with the following structure:")
            parts.append("- Use modular architecture with separate modules")
            parts.append("- Use ConfigModule for environment configuration")
            parts.append("- Use class-validator for DTO validation")
            parts.append("")
            parts.append("Base Web3 service to extend:")
            parts.append(f"```typescript\n{NESTJS_TEMPLATES['web3_service']}\n```")
        else:
            parts.append("Generate an Express.js backend application with:")
            parts.append("- Router-based architecture")
            parts.append("- Service layer pattern")
            parts.append("")
            parts.append("Base structure:")
            parts.append(f"```typescript\n{EXPRESS_TEMPLATES['server']}\n```")

        parts.append("")

        # Add features
        parts.append(f"Features to include: {', '.join(features)}")

        # Add database
        if database != "none":
            parts.append(f"Database: {database}")
            if database == "postgresql":
                parts.append("Use Prisma or TypeORM for database access")
            elif database == "mongodb":
                parts.append("Use Mongoose for MongoDB access")

        # Add contract ABI if provided
        if contract_abi:
            parts.append("\nContract ABI to integrate:")
            parts.append(f"```json\n{contract_abi}\n```")
            parts.append("Generate typed contract interaction methods based on this ABI.")

        # Add context if available
        if context_text:
            parts.append("\nHere are some relevant code examples for reference:")
            parts.append(context_text)

        # Add main request
        parts.append(f"\nGenerate backend code for the following requirement:")
        parts.append(f"\n{prompt}\n")

        parts.append("\nProvide:")
        parts.append("1. Complete TypeScript code for all files")
        parts.append("2. File paths as comments (e.g., // src/app.module.ts)")
        parts.append("3. A brief explanation of the implementation")
        parts.append("\nFormat each file with its path as a comment before the code block.")

        return "\n".join(parts)

    def _parse_files(self, response: str) -> list[dict]:
        """Parse files from LLM response."""
        files = []

        # Pattern 1: File path comment BEFORE code block
        # // path/to/file.ts
        # ```typescript
        # code...
        # ```
        file_pattern = r'(?:\/\/\s*|#\s*)([a-zA-Z0-9_\-\/\.]+\.(?:ts|js|json|yaml|yml|prisma|env))\s*\n```(?:typescript|javascript|json|yaml|prisma)?\s*\n([\s\S]*?)```'
        matches = re.findall(file_pattern, response)

        for path, content in matches:
            normalized = self._normalize_file(path.strip(), content.strip())
            if self._is_valid_code(normalized["path"], normalized["content"]):
                files.append(normalized)

        # Pattern 2: File path comment INSIDE code block (first line)
        # ```typescript
        # // path/to/file.ts
        # code...
        # ```
        if not files:
            code_blocks = re.findall(r'```(?:typescript|javascript|json)?\s*\n([\s\S]*?)```', response)
            for content in code_blocks:
                content = content.strip()
                # Check if first line is a file path comment
                lines = content.split('\n')
                if lines and lines[0].startswith('//'):
                    path_match = re.match(r'^\/\/\s*([a-zA-Z0-9_\-\/\.]+\.(?:ts|js|json|env))', lines[0])
                    if path_match:
                        path = path_match.group(1)
                        actual_content = '\n'.join(lines[1:]).strip()
                        normalized = self._normalize_file(path, actual_content)
                        if self._is_valid_code(normalized["path"], normalized["content"]):
                            files.append(normalized)
                        continue

                # Skip blocks without valid file paths - likely explanation text
                # Only save as .ts if it looks like actual code
                if self._is_valid_code("check.ts", content):
                    files.append({
                        "path": f"src/file_{len(files) + 1}.ts",
                        "content": content,
                    })

        return files

    def _is_valid_code(self, path: str, content: str) -> bool:
        """Check if content looks like valid code, not explanatory text."""
        if not content or len(content) < 10:
            return False

        # Skip if content is mostly prose (no code indicators)
        content_lower = content.lower()
        lines = content.split('\n')

        # Check for TypeScript/JavaScript code indicators
        code_indicators = [
            'import ', 'export ', 'const ', 'let ', 'var ',
            'function ', 'class ', 'interface ', 'type ',
            '@Injectable', '@Controller', '@Module', '@Get', '@Post',
            'async ', 'await ', 'return ', '=>',
            '{', '}', '(', ')', ';',
        ]

        # Check for non-code indicators (prose/explanation)
        prose_indicators = [
            'this file ', 'this code ', 'here is ', 'above is ',
            'you can ', 'you need ', 'make sure ', 'note that ',
            'step 1', 'step 2', 'first,', 'then,', 'finally,',
        ]

        # Count indicators
        code_count = sum(1 for indicator in code_indicators if indicator in content)
        prose_count = sum(1 for indicator in prose_indicators if indicator in content_lower)

        # Prisma schema detection
        if path.endswith('.prisma'):
            return 'model ' in content or 'datasource ' in content or 'generator ' in content

        # JSON detection
        if path.endswith('.json'):
            return content.strip().startswith('{') or content.strip().startswith('[')

        # TypeScript/JavaScript: needs code indicators and minimal prose
        if path.endswith('.ts') or path.endswith('.js'):
            # Must have at least some code indicators
            if code_count < 2:
                return False
            # Too much prose suggests it's explanatory text
            if prose_count > 2:
                return False
            # Check first line isn't a description
            first_line = lines[0].strip().lower()
            if first_line and not first_line.startswith('//') and not first_line.startswith('import') and not first_line.startswith('export') and not first_line.startswith('@'):
                if any(word in first_line for word in ['this', 'here', 'the following', 'below']):
                    return False

        return True

    def _normalize_file(self, path: str, content: str) -> dict:
        """Normalize file path and return file dict."""
        # Normalize path
        if not path.startswith("src/") and not path.startswith("./"):
            if path.endswith(".module.ts") or path.endswith(".service.ts") or path.endswith(".controller.ts"):
                path = f"src/{path}"
            elif path == "package.json" or path.endswith(".env"):
                pass  # Keep at root
            else:
                path = f"src/{path}"

        return {"path": path, "content": content}

    def _extract_explanation(self, response: str) -> str:
        """Extract explanation from response."""
        # Look for explanation after the last code block
        parts = response.split("```")
        if len(parts) > 1:
            explanation = parts[-1].strip()
            if explanation:
                return explanation

        return "Generated backend code based on the provided requirements."

    def _generate_package_json(
        self,
        framework: str,
        features: list[str],
        database: str,
    ) -> dict:
        """Generate package.json content."""
        if framework == "nestjs":
            package = {
                "name": "backend",
                "version": "1.0.0",
                "scripts": {
                    "build": "nest build",
                    "start": "nest start",
                    "start:dev": "nest start --watch",
                    "start:prod": "node dist/main",
                },
                "dependencies": {
                    "@nestjs/common": "^10.0.0",
                    "@nestjs/core": "^10.0.0",
                    "@nestjs/platform-express": "^10.0.0",
                    "@nestjs/config": "^3.0.0",
                    "@nestjs/swagger": "^7.0.0",
                    "@nestjs/schedule": "^4.0.0",
                    "viem": "2.17.0",
                    "reflect-metadata": "^0.1.13",
                    "rxjs": "^7.8.1",
                    "class-validator": "^0.14.0",
                    "class-transformer": "^0.5.1",
                },
                "devDependencies": {
                    "@nestjs/cli": "^10.0.0",
                    "@types/node": "^20.0.0",
                    "typescript": "^5.3.0",
                },
            }

            if "auth" in features:
                package["dependencies"]["@nestjs/jwt"] = "^10.0.0"
                package["dependencies"]["@nestjs/passport"] = "^10.0.0"
                package["dependencies"]["passport-jwt"] = "^4.0.1"

            if database == "postgresql":
                package["dependencies"]["@prisma/client"] = "^5.0.0"
                package["devDependencies"]["prisma"] = "^5.0.0"
            elif database == "mongodb":
                package["dependencies"]["@nestjs/mongoose"] = "^10.0.0"
                package["dependencies"]["mongoose"] = "^8.0.0"

        else:  # express
            package = {
                "name": "backend",
                "version": "1.0.0",
                "scripts": {
                    "build": "tsc",
                    "start": "node dist/server.js",
                    "dev": "ts-node-dev --respawn src/server.ts",
                },
                "dependencies": {
                    "express": "^4.18.0",
                    "cors": "^2.8.5",
                    "helmet": "^7.0.0",
                    "dotenv": "^16.0.0",
                    "viem": "^2.0.0",
                },
                "devDependencies": {
                    "@types/express": "^4.17.0",
                    "@types/cors": "^2.8.0",
                    "@types/node": "^20.0.0",
                    "typescript": "^5.0.0",
                    "ts-node-dev": "^2.0.0",
                },
            }

            if "auth" in features:
                package["dependencies"]["jsonwebtoken"] = "^9.0.0"
                package["dependencies"]["bcryptjs"] = "^2.4.3"
                package["devDependencies"]["@types/jsonwebtoken"] = "^9.0.0"
                package["devDependencies"]["@types/bcryptjs"] = "^2.4.0"

            if database == "postgresql":
                package["dependencies"]["@prisma/client"] = "^5.0.0"
                package["devDependencies"]["prisma"] = "^5.0.0"
            elif database == "mongodb":
                package["dependencies"]["mongoose"] = "^8.0.0"

        return package

    def _add_base_files(self, files: list[dict], framework: str) -> list[dict]:
        """Add base files if not present in generated files."""
        file_paths = [f["path"] for f in files]

        if framework == "nestjs":
            # Add main.ts entry point if not present
            if not any("main.ts" in p for p in file_paths):
                files.append({
                    "path": "src/main.ts",
                    "content": '''import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe({ transform: true }));
  app.enableCors();
  await app.listen(process.env.PORT || 3000);
}
bootstrap();
''',
                })

            # Add app.module.ts if not present
            if not any("app.module.ts" in p for p in file_paths):
                files.append({
                    "path": "src/app.module.ts",
                    "content": '''import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
  ],
  controllers: [],
  providers: [],
})
export class AppModule {}
''',
                })

            # Add tsconfig.json for NestJS
            if not any("tsconfig.json" in p for p in file_paths):
                files.append({
                    "path": "tsconfig.json",
                    "content": '''{
  "compilerOptions": {
    "module": "commonjs",
    "declaration": true,
    "removeComments": true,
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true,
    "allowSyntheticDefaultImports": true,
    "target": "ES2021",
    "sourceMap": true,
    "outDir": "./dist",
    "baseUrl": "./",
    "incremental": true,
    "skipLibCheck": true,
    "strictNullChecks": false,
    "noImplicitAny": false,
    "strictBindCallApply": false,
    "forceConsistentCasingInFileNames": false,
    "noFallthroughCasesInSwitch": false
  }
}
''',
                })

            # Add nest-cli.json
            if not any("nest-cli.json" in p for p in file_paths):
                files.append({
                    "path": "nest-cli.json",
                    "content": '''{
  "$schema": "https://json.schemastore.org/nest-cli",
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": {
    "deleteOutDir": true
  }
}
''',
                })

            # Add web3.service.ts if not present
            if not any("web3" in p.lower() for p in file_paths):
                files.append({
                    "path": "src/web3/web3.service.ts",
                    "content": NESTJS_TEMPLATES["web3_service"],
                })
                files.append({
                    "path": "src/web3/web3.module.ts",
                    "content": '''import { Module, Global } from '@nestjs/common';
import { Web3Service } from './web3.service';

@Global()
@Module({
  providers: [Web3Service],
  exports: [Web3Service],
})
export class Web3Module {}
''',
                })
        else:
            # Express framework
            # Add tsconfig.json
            if not any("tsconfig.json" in p for p in file_paths):
                files.append({
                    "path": "tsconfig.json",
                    "content": '''{
  "compilerOptions": {
    "target": "ES2021",
    "module": "commonjs",
    "lib": ["ES2021"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": false,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}
''',
                })

            # Add web3 service if not present
            if not any("web3" in p.lower() for p in file_paths):
                files.append({
                    "path": "src/services/web3.ts",
                    "content": EXPRESS_TEMPLATES["web3_service"],
                })

        # Add .env.example
        env_content = """# Server
PORT=3000

# Arbitrum Network (arbitrum or arbitrum-sepolia)
NETWORK=arbitrum-sepolia

# RPC URL
RPC_URL=https://sepolia-rollup.arbitrum.io/rpc

# Private key for signing transactions (optional)
# PRIVATE_KEY=0x...

# Database (if using)
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname
"""
        if not any(".env" in p for p in file_paths):
            files.append({
                "path": ".env.example",
                "content": env_content,
            })

        return files
