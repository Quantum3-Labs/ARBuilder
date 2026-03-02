/**
 * Generate backend code for Arbitrum dApps (M3 tool)
 */

export const TEMPLATE_DISCLAIMER =
  "This generated code is a starting entrypoint — a working foundation for you to build upon. " +
  "Review, customize, and extend it to match your specific requirements before deploying.";

type BackendFramework = "nestjs" | "express";

interface GenerateBackendArgs {
  prompt: string;
  framework?: BackendFramework;
  contractAbi?: string;
  features?: string[];
}

interface GenerateBackendResult {
  files: Record<string, string>;
  dependencies: Record<string, string>;
  devDependencies: Record<string, string>;
  envVars: string[];
  scripts: Record<string, string>;
  setupInstructions: string[];
  disclaimer: string;
}

// NestJS base template
const NESTJS_BASE = {
  "src/app.module.ts": `import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { Web3Module } from './web3/web3.module';
import { ContractModule } from './contract/contract.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    Web3Module,
    ContractModule,
  ],
})
export class AppModule {}
`,

  "src/main.ts": `import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  });
  app.useGlobalPipes(new ValidationPipe({ transform: true }));
  await app.listen(process.env.PORT || 3001);
  console.log(\`Server running on port \${process.env.PORT || 3001}\`);
}
bootstrap();
`,

  "src/web3/web3.module.ts": `import { Module, Global } from '@nestjs/common';
import { Web3Service } from './web3.service';

@Global()
@Module({
  providers: [Web3Service],
  exports: [Web3Service],
})
export class Web3Module {}
`,

  "src/web3/web3.service.ts": `import { Injectable, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { createPublicClient, createWalletClient, http, Chain } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { arbitrumSepolia, arbitrum } from 'viem/chains';

@Injectable()
export class Web3Service implements OnModuleInit {
  private publicClient: ReturnType<typeof createPublicClient>;
  private walletClient: ReturnType<typeof createWalletClient>;
  private chain: Chain;

  constructor(private configService: ConfigService) {}

  onModuleInit() {
    const network = this.configService.get('NETWORK', 'arbitrum-sepolia');
    this.chain = network === 'arbitrum-one' ? arbitrum : arbitrumSepolia;

    this.publicClient = createPublicClient({
      chain: this.chain,
      transport: http(this.configService.get('RPC_URL')),
    });

    const privateKey = this.configService.get('PRIVATE_KEY');
    if (privateKey) {
      const account = privateKeyToAccount(\`0x\${privateKey.replace('0x', '')}\`);
      this.walletClient = createWalletClient({
        account,
        chain: this.chain,
        transport: http(this.configService.get('RPC_URL')),
      });
    }
  }

  getPublicClient() {
    return this.publicClient;
  }

  getWalletClient() {
    return this.walletClient;
  }

  getChain() {
    return this.chain;
  }
}
`,

  "src/contract/contract.module.ts": `import { Module } from '@nestjs/common';
import { ContractService } from './contract.service';
import { ContractController } from './contract.controller';

@Module({
  providers: [ContractService],
  controllers: [ContractController],
  exports: [ContractService],
})
export class ContractModule {}
`,

  "src/contract/contract.service.ts": `import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Web3Service } from '../web3/web3.service';
import { getContract } from 'viem';

// Import your contract ABI
// import { abi } from './abi';

@Injectable()
export class ContractService {
  private contract: ReturnType<typeof getContract>;

  constructor(
    private web3Service: Web3Service,
    private configService: ConfigService,
  ) {}

  onModuleInit() {
    const contractAddress = this.configService.get('CONTRACT_ADDRESS');
    if (contractAddress) {
      // Initialize contract instance
      // this.contract = getContract({
      //   address: contractAddress as \`0x\${string}\`,
      //   abi,
      //   client: this.web3Service.getPublicClient(),
      // });
    }
  }

  // Add your contract methods here
  async getBalance(address: string): Promise<bigint> {
    const client = this.web3Service.getPublicClient();
    return client.getBalance({ address: address as \`0x\${string}\` });
  }
}
`,

  "src/contract/contract.controller.ts": `import { Controller, Get, Param } from '@nestjs/common';
import { ContractService } from './contract.service';

@Controller('contract')
export class ContractController {
  constructor(private contractService: ContractService) {}

  @Get('balance/:address')
  async getBalance(@Param('address') address: string) {
    const balance = await this.contractService.getBalance(address);
    return { address, balance: balance.toString() };
  }
}
`,
};

// Express base template
const EXPRESS_BASE = {
  "src/index.ts": `import express from 'express';
import cors from 'cors';
import { config } from 'dotenv';
import { createPublicClient, http } from 'viem';
import { arbitrumSepolia, arbitrum } from 'viem/chains';
import contractRoutes from './routes/contract';

config();

const app = express();
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
}));
app.use(express.json());

// Initialize viem client
const chain = process.env.NETWORK === 'arbitrum-one' ? arbitrum : arbitrumSepolia;
export const publicClient = createPublicClient({
  chain,
  transport: http(process.env.RPC_URL),
});

// Routes
app.use('/api/contract', contractRoutes);

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', chain: chain.name });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(\`Server running on port \${PORT}\`);
});
`,

  "src/routes/contract.ts": `import { Router } from 'express';
import { publicClient } from '../index';

const router = Router();

router.get('/balance/:address', async (req, res) => {
  try {
    const { address } = req.params;
    const balance = await publicClient.getBalance({
      address: address as \`0x\${string}\`,
    });
    res.json({ address, balance: balance.toString() });
  } catch (error) {
    res.status(500).json({ error: 'Failed to get balance' });
  }
});

export default router;
`,
};

const NESTJS_DEPS = {
  "@nestjs/common": "^10.0.0",
  "@nestjs/core": "^10.0.0",
  "@nestjs/config": "^3.0.0",
  "@nestjs/platform-express": "^10.0.0",
  "viem": "^2.21.0",
  "reflect-metadata": "^0.1.13",
  "rxjs": "^7.8.0",
};

const NESTJS_DEV_DEPS = {
  "@nestjs/cli": "^10.0.0",
  "@nestjs/testing": "^10.0.0",
  "@types/node": "^20.0.0",
  "typescript": "^5.3.0",
  "ts-node": "^10.9.0",
};

const EXPRESS_DEPS = {
  "express": "^4.18.0",
  "cors": "^2.8.5",
  "dotenv": "^16.0.0",
  "viem": "^2.21.0",
};

const EXPRESS_DEV_DEPS = {
  "@types/express": "^4.17.0",
  "@types/cors": "^2.8.0",
  "@types/node": "^20.0.0",
  "typescript": "^5.3.0",
  "ts-node": "^10.9.0",
  "nodemon": "^3.0.0",
};

interface AbiFunc {
  name: string;
  args: { type: string; name: string }[];
}

function injectNestJSAbiMethods(
  files: Record<string, string>,
  readFuncs: AbiFunc[],
  writeFuncs: AbiFunc[]
): void {
  // Generate service methods
  const methods: string[] = [];
  for (const func of readFuncs) {
    const pascal = func.name[0].toUpperCase() + func.name.slice(1);
    methods.push(
      `  async read${pascal}(): Promise<unknown> {\n` +
      `    return await this.contract.read.${func.name}();\n` +
      `  }`
    );
  }
  for (const func of writeFuncs) {
    const pascal = func.name[0].toUpperCase() + func.name.slice(1);
    const argNames = func.args.map((_, i) => `arg${i}`);
    const params = argNames.map((a) => `${a}: unknown`).join(", ");
    const argsList = argNames.join(", ");
    methods.push(
      `  async write${pascal}(${params}): Promise<\`0x\${string}\`> {\n` +
      `    return await this.contract.write.${func.name}([${argsList}]);\n` +
      `  }`
    );
  }

  const serviceKey = "src/contract/contract.service.ts";
  if (files[serviceKey]) {
    let content = files[serviceKey];
    // Uncomment ABI import
    content = content.replace(
      "// import { abi } from './abi';",
      "import { CONTRACT_ABI } from './abi';"
    );
    // Uncomment contract initialization
    content = content.replace(
      `    if (contractAddress) {
      // Initialize contract instance
      // this.contract = getContract({
      //   address: contractAddress as \`0x\${string}\`,
      //   abi,
      //   client: this.web3Service.getPublicClient(),
      // });
    }`,
      `    if (contractAddress) {
      this.contract = getContract({
        address: contractAddress as \`0x\${string}\`,
        abi: CONTRACT_ABI,
        client: this.web3Service.getPublicClient(),
      });
    }`
    );
    // Replace generic method with ABI-aware methods
    content = content.replace(
      `  // Add your contract methods here
  async getBalance(address: string): Promise<bigint> {
    const client = this.web3Service.getPublicClient();
    return client.getBalance({ address: address as \`0x\${string}\` });
  }`,
      `  // ABI-generated methods\n` + methods.join("\n\n")
    );
    files[serviceKey] = content;
  }

  // Generate matching controller endpoints
  const controllerKey = "src/contract/contract.controller.ts";
  if (files[controllerKey]) {
    const endpoints: string[] = [];
    for (const func of readFuncs) {
      const pascal = func.name[0].toUpperCase() + func.name.slice(1);
      endpoints.push(
        `  @Get('${func.name}')\n` +
        `  async get${pascal}() {\n` +
        `    const result = await this.contractService.read${pascal}();\n` +
        `    return { ${func.name}: result?.toString() };\n` +
        `  }`
      );
    }
    for (const func of writeFuncs) {
      const pascal = func.name[0].toUpperCase() + func.name.slice(1);
      const argNames = func.args.map((_, i) => `arg${i}`);
      const bodyArgs = argNames.map((a) => `body.${a}`).join(", ");
      endpoints.push(
        `  @Post('${func.name}')\n` +
        `  async post${pascal}(@Body() body: Record<string, unknown>) {\n` +
        `    const hash = await this.contractService.write${pascal}(${bodyArgs});\n` +
        `    return { hash };\n` +
        `  }`
      );
    }

    files[controllerKey] = `import { Controller, Get, Post, Body } from '@nestjs/common';
import { ContractService } from './contract.service';

@Controller('contract')
export class ContractController {
  constructor(private contractService: ContractService) {}

${endpoints.join("\n\n")}
}
`;
  }
}

function injectExpressAbiRoutes(
  files: Record<string, string>,
  readFuncs: AbiFunc[],
  writeFuncs: AbiFunc[]
): void {
  const routes: string[] = [];
  for (const func of readFuncs) {
    routes.push(
      `router.get('/${func.name}', async (req, res) => {\n` +
      `  try {\n` +
      `    const result = await publicClient.readContract({\n` +
      `      address: process.env.CONTRACT_ADDRESS as \`0x\${string}\`,\n` +
      `      abi: CONTRACT_ABI,\n` +
      `      functionName: '${func.name}',\n` +
      `    });\n` +
      `    res.json({ ${func.name}: result?.toString() });\n` +
      `  } catch (error) {\n` +
      `    res.status(500).json({ error: 'Failed to read ${func.name}' });\n` +
      `  }\n` +
      `});`
    );
  }
  for (const func of writeFuncs) {
    routes.push(
      `router.post('/${func.name}', async (req, res) => {\n` +
      `  try {\n` +
      `    // Note: write operations require a wallet client\n` +
      `    res.json({ function: '${func.name}', args: req.body });\n` +
      `  } catch (error) {\n` +
      `    res.status(500).json({ error: 'Failed to call ${func.name}' });\n` +
      `  }\n` +
      `});`
    );
  }

  const routeKey = "src/routes/contract.ts";
  files[routeKey] = `import { Router } from 'express';
import { publicClient } from '../index';
import { CONTRACT_ABI } from '../config/abi';

const router = Router();

${routes.join("\n\n")}

export default router;
`;

  // Also add the ABI file in the Express location
  if (files["src/contract/abi.ts"]) {
    files["src/config/abi.ts"] = files["src/contract/abi.ts"];
  }
}

export function generateBackend(args: GenerateBackendArgs): GenerateBackendResult {
  const { framework = "nestjs", contractAbi } = args;

  const isNestJS = framework === "nestjs";
  const baseFiles = isNestJS ? { ...NESTJS_BASE } : { ...EXPRESS_BASE };
  const dependencies = isNestJS ? { ...NESTJS_DEPS } : { ...EXPRESS_DEPS };
  const devDependencies = isNestJS ? { ...NESTJS_DEV_DEPS } : { ...EXPRESS_DEV_DEPS };

  const files: Record<string, string> = { ...baseFiles };

  // Add ABI file and generate ABI-aware endpoints if provided
  if (contractAbi) {
    try {
      const abi = JSON.parse(contractAbi);
      files["src/contract/abi.ts"] = `export const CONTRACT_ABI = ${JSON.stringify(abi, null, 2)} as const;\n`;

      // Parse ABI functions into read/write categories
      const readFuncs: { name: string; args: { type: string; name: string }[] }[] = [];
      const writeFuncs: { name: string; args: { type: string; name: string }[] }[] = [];
      for (const item of abi) {
        if (item.type !== "function") continue;
        const entry = {
          name: item.name,
          args: (item.inputs || []).map((inp: { type: string; name: string }) => ({
            type: inp.type,
            name: inp.name,
          })),
        };
        if (item.stateMutability === "view" || item.stateMutability === "pure") {
          readFuncs.push(entry);
        } else {
          writeFuncs.push(entry);
        }
      }

      if (readFuncs.length > 0 || writeFuncs.length > 0) {
        if (isNestJS) {
          injectNestJSAbiMethods(files, readFuncs, writeFuncs);
        } else {
          injectExpressAbiRoutes(files, readFuncs, writeFuncs);
        }
      }
    } catch {
      // Invalid ABI, skip
    }
  }

  // Add package.json
  files["package.json"] = JSON.stringify(
    {
      name: "arbbuilder-backend",
      version: "1.0.0",
      scripts: isNestJS
        ? {
            build: "nest build",
            start: "nest start",
            "start:dev": "nest start --watch",
            "start:prod": "node dist/main",
          }
        : {
            build: "tsc",
            start: "node dist/index.js",
            dev: "nodemon --exec ts-node src/index.ts",
          },
      dependencies,
      devDependencies,
    },
    null,
    2
  );

  // Add tsconfig.json
  files["tsconfig.json"] = JSON.stringify(
    {
      compilerOptions: {
        module: "commonjs",
        target: "ES2021",
        lib: ["ES2021"],
        outDir: "./dist",
        rootDir: "./src",
        strict: true,
        esModuleInterop: true,
        skipLibCheck: true,
        experimentalDecorators: isNestJS,
        emitDecoratorMetadata: isNestJS,
      },
      include: ["src/**/*"],
      exclude: ["node_modules"],
    },
    null,
    2
  );

  // Add .env.example
  files[".env.example"] = `# Network: arbitrum-sepolia or arbitrum-one
NETWORK=arbitrum-sepolia
RPC_URL=https://sepolia-rollup.arbitrum.io/rpc
PORT=3001

# Optional: For write operations
PRIVATE_KEY=your-private-key

# Optional: Contract address
CONTRACT_ADDRESS=0x...

# CORS - Frontend origin
FRONTEND_URL=http://localhost:3000
`;

  return {
    files,
    dependencies,
    devDependencies,
    envVars: ["NETWORK", "RPC_URL", "PORT", "PRIVATE_KEY", "CONTRACT_ADDRESS", "FRONTEND_URL"],
    scripts: isNestJS
      ? { build: "nest build", dev: "nest start --watch", start: "node dist/main" }
      : { build: "tsc", dev: "nodemon --exec ts-node src/index.ts", start: "node dist/index.js" },
    setupInstructions: [
      "1. Install dependencies: npm install",
      "2. Copy .env.example to .env and configure",
      "3. Run development server: npm run dev",
      "4. Build for production: npm run build",
    ],
    disclaimer: TEMPLATE_DISCLAIMER,
  };
}
