"""
Backend templates for NestJS and Express applications.
These templates provide scaffolding for dApp backends with Web3 integration.

Templates:
- NestJS + Stylus: Full NestJS app with contract integration
- Express + Stylus: Lightweight Express backend
- NestJS + GraphQL: NestJS with GraphQL for subgraph querying
- API Gateway: Cross-chain proxy for L1/L2/L3
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Placeholder marker replaced at generation time with actual contract ABI
ABI_PLACEHOLDER = "__ABI_PLACEHOLDER__"


@dataclass
class BackendTemplate:
    """A curated backend template."""

    name: str
    description: str
    framework: str  # "nestjs" | "express"
    features: List[str]
    files: Dict[str, str]  # path -> content
    dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str] = field(default_factory=dict)
    env_vars: List[str] = field(default_factory=list)
    scripts: Dict[str, str] = field(default_factory=dict)


# NestJS + Stylus Contract Integration Template
NESTJS_STYLUS_TEMPLATE = BackendTemplate(
    name="NestJS + Stylus",
    description="Full NestJS backend with Stylus contract integration via viem",
    framework="nestjs",
    features=[
        "viem integration",
        "contract service",
        "REST API",
        "health checks",
        "environment config",
        "validation pipes",
    ],
    files={
        "src/main.ts": '''import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.useGlobalPipes(new ValidationPipe({
    whitelist: true,
    transform: true,
  }));

  app.enableCors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  });

  const port = process.env.PORT || 3001;
  await app.listen(port);
  console.log(`Server running on http://localhost:${port}`);
}
bootstrap();
''',
        "src/app.module.ts": '''import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { ContractModule } from './contract/contract.module';
import { HealthModule } from './health/health.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
    ContractModule,
    HealthModule,
  ],
})
export class AppModule {}
''',
        "src/contract/contract.module.ts": '''import { Module } from '@nestjs/common';
import { ContractService } from './contract.service';
import { ContractController } from './contract.controller';

@Module({
  providers: [ContractService],
  controllers: [ContractController],
  exports: [ContractService],
})
export class ContractModule {}
''',
        "src/contract/contract.service.ts": '''import { Injectable, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import {
  createPublicClient,
  createWalletClient,
  http,
  getContract,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { arbitrumSepolia } from 'viem/chains';

// Contract ABI - auto-generated from Stylus contract by ARBuilder
const CONTRACT_ABI = __ABI_PLACEHOLDER__ as const;

@Injectable()
export class ContractService implements OnModuleInit {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private publicClient: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private contract: any;

  constructor(private configService: ConfigService) {}

  async onModuleInit() {
    const rpcUrl = this.configService.get<string>('RPC_URL');
    const privateKey = this.configService.get<string>('PRIVATE_KEY');
    const contractAddress = this.configService.get<string>('CONTRACT_ADDRESS') as `0x${string}`;

    // Create public client for read operations
    this.publicClient = createPublicClient({
      chain: arbitrumSepolia,
      transport: http(rpcUrl),
    });

    // Create wallet client for write operations
    if (privateKey) {
      const account = privateKeyToAccount(privateKey as `0x${string}`);
      const walletClient = createWalletClient({
        account,
        chain: arbitrumSepolia,
        transport: http(rpcUrl),
      });

      // Create contract instance for easy read/write
      this.contract = getContract({
        address: contractAddress,
        abi: CONTRACT_ABI,
        client: {
          public: this.publicClient,
          wallet: walletClient,
        },
      });
    }
  }

  async readNumber(): Promise<bigint> {
    return await this.contract.read.number();
  }

  async setNumber(newNumber: bigint): Promise<`0x${string}`> {
    return await this.contract.write.setNumber([newNumber]);
  }

  async increment(): Promise<`0x${string}`> {
    return await this.contract.write.increment([]);
  }

  async waitForTransaction(hash: `0x${string}`) {
    return this.publicClient.waitForTransactionReceipt({ hash });
  }
}
''',
        "src/contract/contract.controller.ts": '''import { Controller, Get, Post, Body, HttpException, HttpStatus } from '@nestjs/common';
import { ContractService } from './contract.service';
import { SetNumberDto } from './dto/set-number.dto';

@Controller('contract')
export class ContractController {
  constructor(private readonly contractService: ContractService) {}

  @Get('number')
  async getNumber() {
    try {
      const number = await this.contractService.readNumber();
      return { number: number.toString() };
    } catch (error) {
      throw new HttpException(
        `Failed to read number: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('number')
  async setNumber(@Body() dto: SetNumberDto) {
    try {
      const hash = await this.contractService.setNumber(BigInt(dto.number));
      const receipt = await this.contractService.waitForTransaction(hash);
      return {
        hash,
        blockNumber: receipt.blockNumber.toString(),
        status: receipt.status,
      };
    } catch (error) {
      throw new HttpException(
        `Failed to set number: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('increment')
  async increment() {
    try {
      const hash = await this.contractService.increment();
      const receipt = await this.contractService.waitForTransaction(hash);
      return {
        hash,
        blockNumber: receipt.blockNumber.toString(),
        status: receipt.status,
      };
    } catch (error) {
      throw new HttpException(
        `Failed to increment: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}
''',
        "src/contract/dto/set-number.dto.ts": '''import { IsString, IsNotEmpty } from 'class-validator';

export class SetNumberDto {
  @IsString()
  @IsNotEmpty()
  number: string;
}
''',
        "src/health/health.module.ts": '''import { Module } from '@nestjs/common';
import { HealthController } from './health.controller';

@Module({
  controllers: [HealthController],
})
export class HealthModule {}
''',
        "src/health/health.controller.ts": '''import { Controller, Get } from '@nestjs/common';

@Controller('health')
export class HealthController {
  @Get()
  check() {
    return {
      status: 'ok',
      timestamp: new Date().toISOString(),
    };
  }
}
''',
        ".env.example": '''# RPC Configuration
RPC_URL=https://sepolia-rollup.arbitrum.io/rpc

# Contract Configuration
CONTRACT_ADDRESS=0x...

# Wallet Configuration (for write operations)
PRIVATE_KEY=0x...

# Server Configuration
PORT=3001

# CORS - Frontend origin
FRONTEND_URL=http://localhost:3000
''',
        "tsconfig.json": '''{
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
    "strictNullChecks": true,
    "noImplicitAny": true,
    "strictBindCallApply": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true
  }
}
''',
    },
    dependencies={
        "@nestjs/common": "^10.0.0",
        "@nestjs/core": "^10.0.0",
        "@nestjs/platform-express": "^10.0.0",
        "@nestjs/config": "^3.1.0",
        "class-validator": "^0.14.0",
        "class-transformer": "^0.5.1",
        "viem": "^2.21.0",
        "reflect-metadata": "^0.1.13",
        "rxjs": "^7.8.1",
    },
    dev_dependencies={
        "@nestjs/cli": "^10.0.0",
        "@nestjs/testing": "^10.0.0",
        "@types/node": "^20.0.0",
        "typescript": "^5.3.0",
        "ts-node": "^10.9.0",
    },
    env_vars=["RPC_URL", "CONTRACT_ADDRESS", "PRIVATE_KEY", "PORT", "FRONTEND_URL"],
    scripts={
        "build": "nest build",
        "start": "nest start",
        "start:dev": "nest start --watch",
        "start:prod": "node dist/main",
    },
)


# Express + Stylus Lightweight Template
EXPRESS_STYLUS_TEMPLATE = BackendTemplate(
    name="Express + Stylus",
    description="Lightweight Express backend with Stylus contract integration",
    framework="express",
    features=[
        "viem integration",
        "minimal setup",
        "REST API",
        "error handling",
    ],
    files={
        "src/index.ts": '''import express from 'express';
import cors from 'cors';
import { config } from 'dotenv';
import { contractRouter } from './routes/contract';
import { healthRouter } from './routes/health';

config();

const app = express();
const port = process.env.PORT || 3001;

app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
}));
app.use(express.json());

app.use('/health', healthRouter);
app.use('/contract', contractRouter);

// Error handling middleware
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: err.message });
});

app.listen(port, () => {
  console.log(`Server running on http://localhost:${port}`);
});
''',
        "src/routes/contract.ts": '''import { Router } from 'express';
import { getClient, getWalletClient, CONTRACT_ADDRESS, CONTRACT_ABI } from '../config/web3';

export const contractRouter = Router();

contractRouter.get('/number', async (req, res, next) => {
  try {
    const client = getClient();
    const result = await client.readContract({
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: 'number',
    });
    res.json({ number: result.toString() });
  } catch (error) {
    next(error);
  }
});

contractRouter.post('/number', async (req, res, next) => {
  try {
    const { number } = req.body;
    const walletClient = getWalletClient();
    const client = getClient();

    const hash = await walletClient.writeContract({
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: 'setNumber',
      args: [BigInt(number)],
    });

    const receipt = await client.waitForTransactionReceipt({ hash });
    res.json({
      hash,
      blockNumber: receipt.blockNumber.toString(),
      status: receipt.status,
    });
  } catch (error) {
    next(error);
  }
});

contractRouter.post('/increment', async (req, res, next) => {
  try {
    const walletClient = getWalletClient();
    const client = getClient();

    const hash = await walletClient.writeContract({
      address: CONTRACT_ADDRESS,
      abi: CONTRACT_ABI,
      functionName: 'increment',
    });

    const receipt = await client.waitForTransactionReceipt({ hash });
    res.json({
      hash,
      blockNumber: receipt.blockNumber.toString(),
      status: receipt.status,
    });
  } catch (error) {
    next(error);
  }
});
''',
        "src/routes/health.ts": '''import { Router } from 'express';

export const healthRouter = Router();

healthRouter.get('/', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
  });
});
''',
        "src/config/web3.ts": '''import {
  createPublicClient,
  createWalletClient,
  http,
  parseAbi,
  type PublicClient,
  type WalletClient,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { arbitrumSepolia } from 'viem/chains';

export const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS as `0x${string}`;

export const CONTRACT_ABI = parseAbi(__ABI_PLACEHOLDER__);

let publicClient: PublicClient;
let walletClient: WalletClient;

export function getClient(): PublicClient {
  if (!publicClient) {
    publicClient = createPublicClient({
      chain: arbitrumSepolia,
      transport: http(process.env.RPC_URL),
    });
  }
  return publicClient;
}

export function getWalletClient(): WalletClient {
  if (!walletClient) {
    const privateKey = process.env.PRIVATE_KEY as `0x${string}`;
    const account = privateKeyToAccount(privateKey);
    walletClient = createWalletClient({
      account,
      chain: arbitrumSepolia,
      transport: http(process.env.RPC_URL),
    });
  }
  return walletClient;
}
''',
        ".env.example": '''RPC_URL=https://sepolia-rollup.arbitrum.io/rpc
CONTRACT_ADDRESS=0x...
PRIVATE_KEY=0x...
PORT=3001
FRONTEND_URL=http://localhost:3000
''',
        "tsconfig.json": '''{
  "compilerOptions": {
    "target": "ES2021",
    "module": "commonjs",
    "lib": ["ES2021"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}
''',
    },
    dependencies={
        "express": "^4.18.0",
        "cors": "^2.8.5",
        "dotenv": "^16.0.0",
        "viem": "^2.0.0",
    },
    dev_dependencies={
        "@types/express": "^4.17.0",
        "@types/cors": "^2.8.0",
        "@types/node": "^20.0.0",
        "typescript": "^5.0.0",
        "ts-node": "^10.9.0",
        "nodemon": "^3.0.0",
    },
    env_vars=["RPC_URL", "CONTRACT_ADDRESS", "PRIVATE_KEY", "PORT", "FRONTEND_URL"],
    scripts={
        "build": "tsc",
        "start": "node dist/index.js",
        "dev": "nodemon --exec ts-node src/index.ts",
    },
)


# NestJS + GraphQL for Subgraph Querying
NESTJS_GRAPHQL_TEMPLATE = BackendTemplate(
    name="NestJS + GraphQL",
    description="NestJS backend with GraphQL client for subgraph querying",
    framework="nestjs",
    features=[
        "GraphQL client",
        "subgraph integration",
        "type-safe queries",
        "caching",
    ],
    files={
        "src/main.ts": '''import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
  app.enableCors();

  const port = process.env.PORT || 3001;
  await app.listen(port);
  console.log(`Server running on http://localhost:${port}`);
}
bootstrap();
''',
        "src/app.module.ts": '''import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { SubgraphModule } from './subgraph/subgraph.module';
import { HealthModule } from './health/health.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    SubgraphModule,
    HealthModule,
  ],
})
export class AppModule {}
''',
        "src/subgraph/subgraph.module.ts": '''import { Module } from '@nestjs/common';
import { SubgraphService } from './subgraph.service';
import { SubgraphController } from './subgraph.controller';

@Module({
  providers: [SubgraphService],
  controllers: [SubgraphController],
  exports: [SubgraphService],
})
export class SubgraphModule {}
''',
        "src/subgraph/subgraph.service.ts": '''import { Injectable, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { GraphQLClient } from 'graphql-request';

@Injectable()
export class SubgraphService implements OnModuleInit {
  private client: GraphQLClient;

  constructor(private configService: ConfigService) {}

  onModuleInit() {
    const endpoint = this.configService.get<string>('SUBGRAPH_URL');
    this.client = new GraphQLClient(endpoint);
  }

  async query<T>(query: string, variables?: Record<string, unknown>): Promise<T> {
    return this.client.request<T>(query, variables);
  }

  // Example: Get recent transfers
  async getRecentTransfers(first: number = 10) {
    const query = `
      query GetTransfers($first: Int!) {
        transfers(first: $first, orderBy: blockTimestamp, orderDirection: desc) {
          id
          from
          to
          value
          blockTimestamp
          transactionHash
        }
      }
    `;
    return this.query<{ transfers: Transfer[] }>(query, { first });
  }

  // Example: Get token balances
  async getTokenBalances(account: string) {
    const query = `
      query GetBalances($account: String!) {
        account(id: $account) {
          id
          balance
          transfersFrom {
            id
            to
            value
          }
          transfersTo {
            id
            from
            value
          }
        }
      }
    `;
    return this.query<{ account: Account }>(query, { account: account.toLowerCase() });
  }
}

interface Transfer {
  id: string;
  from: string;
  to: string;
  value: string;
  blockTimestamp: string;
  transactionHash: string;
}

interface Account {
  id: string;
  balance: string;
  transfersFrom: Transfer[];
  transfersTo: Transfer[];
}
''',
        "src/subgraph/subgraph.controller.ts": '''import { Controller, Get, Query, Param } from '@nestjs/common';
import { SubgraphService } from './subgraph.service';

@Controller('subgraph')
export class SubgraphController {
  constructor(private readonly subgraphService: SubgraphService) {}

  @Get('transfers')
  async getTransfers(@Query('first') first?: string) {
    const limit = first ? parseInt(first, 10) : 10;
    return this.subgraphService.getRecentTransfers(limit);
  }

  @Get('account/:address')
  async getAccount(@Param('address') address: string) {
    return this.subgraphService.getTokenBalances(address);
  }
}
''',
        "src/health/health.module.ts": '''import { Module } from '@nestjs/common';
import { HealthController } from './health.controller';

@Module({
  controllers: [HealthController],
})
export class HealthModule {}
''',
        "src/health/health.controller.ts": '''import { Controller, Get } from '@nestjs/common';

@Controller('health')
export class HealthController {
  @Get()
  check() {
    return { status: 'ok', timestamp: new Date().toISOString() };
  }
}
''',
        ".env.example": '''SUBGRAPH_URL=https://api.thegraph.com/subgraphs/name/your-subgraph
PORT=3001
''',
    },
    dependencies={
        "@nestjs/common": "^10.0.0",
        "@nestjs/core": "^10.0.0",
        "@nestjs/platform-express": "^10.0.0",
        "@nestjs/config": "^3.1.0",
        "class-validator": "^0.14.0",
        "class-transformer": "^0.5.1",
        "graphql": "^16.8.0",
        "graphql-request": "^6.1.0",
        "reflect-metadata": "^0.1.13",
        "rxjs": "^7.8.1",
    },
    dev_dependencies={
        "@nestjs/cli": "^10.0.0",
        "@types/node": "^20.0.0",
        "typescript": "^5.0.0",
    },
    env_vars=["SUBGRAPH_URL", "PORT"],
    scripts={
        "build": "nest build",
        "start": "nest start",
        "start:dev": "nest start --watch",
    },
)


# API Gateway for Cross-Chain Operations
API_GATEWAY_TEMPLATE = BackendTemplate(
    name="API Gateway",
    description="Cross-chain proxy for L1/L2/L3 operations with Arbitrum SDK",
    framework="nestjs",
    features=[
        "multi-chain support",
        "Arbitrum SDK",
        "deposit/withdraw proxying",
        "transaction status",
    ],
    files={
        "src/main.ts": '''import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
  app.enableCors();

  const port = process.env.PORT || 3001;
  await app.listen(port);
  console.log(`API Gateway running on http://localhost:${port}`);
}
bootstrap();
''',
        "src/app.module.ts": '''import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { BridgeModule } from './bridge/bridge.module';
import { HealthModule } from './health/health.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    BridgeModule,
    HealthModule,
  ],
})
export class AppModule {}
''',
        "src/bridge/bridge.module.ts": '''import { Module } from '@nestjs/common';
import { BridgeService } from './bridge.service';
import { BridgeController } from './bridge.controller';

@Module({
  providers: [BridgeService],
  controllers: [BridgeController],
  exports: [BridgeService],
})
export class BridgeModule {}
''',
        "src/bridge/bridge.service.ts": '''import { Injectable, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { createPublicClient, createWalletClient, http, parseEther } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { mainnet, arbitrum, arbitrumSepolia, sepolia } from 'viem/chains';

type NetworkType = 'mainnet' | 'sepolia';

interface ChainConfig {
  l1: typeof mainnet | typeof sepolia;
  l2: typeof arbitrum | typeof arbitrumSepolia;
}

@Injectable()
export class BridgeService implements OnModuleInit {
  private chainConfigs: Record<NetworkType, ChainConfig> = {
    mainnet: { l1: mainnet, l2: arbitrum },
    sepolia: { l1: sepolia, l2: arbitrumSepolia },
  };

  private network: NetworkType;

  constructor(private configService: ConfigService) {}

  onModuleInit() {
    this.network = this.configService.get<NetworkType>('NETWORK', 'sepolia');
  }

  getChainConfig(): ChainConfig {
    return this.chainConfigs[this.network];
  }

  createL1Client() {
    const { l1 } = this.getChainConfig();
    return createPublicClient({
      chain: l1,
      transport: http(this.configService.get('L1_RPC_URL')),
    });
  }

  createL2Client() {
    const { l2 } = this.getChainConfig();
    return createPublicClient({
      chain: l2,
      transport: http(this.configService.get('L2_RPC_URL')),
    });
  }

  async getL1Balance(address: `0x${string}`) {
    const client = this.createL1Client();
    const balance = await client.getBalance({ address });
    return { address, balance: balance.toString(), chain: 'L1' };
  }

  async getL2Balance(address: `0x${string}`) {
    const client = this.createL2Client();
    const balance = await client.getBalance({ address });
    return { address, balance: balance.toString(), chain: 'L2' };
  }

  async getTransactionStatus(hash: `0x${string}`, layer: 'L1' | 'L2') {
    const client = layer === 'L1' ? this.createL1Client() : this.createL2Client();

    try {
      const receipt = await client.getTransactionReceipt({ hash });
      return {
        hash,
        layer,
        status: receipt.status,
        blockNumber: receipt.blockNumber.toString(),
        gasUsed: receipt.gasUsed.toString(),
      };
    } catch (error) {
      return { hash, layer, status: 'pending', error: error.message };
    }
  }
}
''',
        "src/bridge/bridge.controller.ts": '''import { Controller, Get, Param, Query } from '@nestjs/common';
import { BridgeService } from './bridge.service';

@Controller('bridge')
export class BridgeController {
  constructor(private readonly bridgeService: BridgeService) {}

  @Get('balance/l1/:address')
  async getL1Balance(@Param('address') address: string) {
    return this.bridgeService.getL1Balance(address as `0x${string}`);
  }

  @Get('balance/l2/:address')
  async getL2Balance(@Param('address') address: string) {
    return this.bridgeService.getL2Balance(address as `0x${string}`);
  }

  @Get('tx/:hash')
  async getTransactionStatus(
    @Param('hash') hash: string,
    @Query('layer') layer: 'L1' | 'L2' = 'L2',
  ) {
    return this.bridgeService.getTransactionStatus(hash as `0x${string}`, layer);
  }
}
''',
        "src/health/health.module.ts": '''import { Module } from '@nestjs/common';
import { HealthController } from './health.controller';

@Module({
  controllers: [HealthController],
})
export class HealthModule {}
''',
        "src/health/health.controller.ts": '''import { Controller, Get } from '@nestjs/common';

@Controller('health')
export class HealthController {
  @Get()
  check() {
    return { status: 'ok', timestamp: new Date().toISOString() };
  }
}
''',
        ".env.example": '''# Network: mainnet or sepolia
NETWORK=sepolia

# L1 RPC (Ethereum)
L1_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY

# L2 RPC (Arbitrum)
L2_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc

# Server
PORT=3001
''',
    },
    dependencies={
        "@nestjs/common": "^10.0.0",
        "@nestjs/core": "^10.0.0",
        "@nestjs/platform-express": "^10.0.0",
        "@nestjs/config": "^3.1.0",
        "class-validator": "^0.14.0",
        "class-transformer": "^0.5.1",
        "viem": "^2.0.0",
        "reflect-metadata": "^0.1.13",
        "rxjs": "^7.8.1",
    },
    dev_dependencies={
        "@nestjs/cli": "^10.0.0",
        "@types/node": "^20.0.0",
        "typescript": "^5.0.0",
    },
    env_vars=["NETWORK", "L1_RPC_URL", "L2_RPC_URL", "PORT"],
    scripts={
        "build": "nest build",
        "start": "nest start",
        "start:dev": "nest start --watch",
    },
)


# All templates indexed by name
BACKEND_TEMPLATES = {
    "nestjs_stylus": NESTJS_STYLUS_TEMPLATE,
    "express_stylus": EXPRESS_STYLUS_TEMPLATE,
    "nestjs_graphql": NESTJS_GRAPHQL_TEMPLATE,
    "api_gateway": API_GATEWAY_TEMPLATE,
}


def select_backend_template(framework: str, prompt: str) -> BackendTemplate:
    """Select the best backend template based on framework and prompt keywords."""
    lower_prompt = prompt.lower()

    if "graphql" in lower_prompt or "subgraph" in lower_prompt:
        return NESTJS_GRAPHQL_TEMPLATE

    if "gateway" in lower_prompt or "cross-chain" in lower_prompt or "multi-chain" in lower_prompt:
        return API_GATEWAY_TEMPLATE

    if framework == "express":
        return EXPRESS_STYLUS_TEMPLATE

    return NESTJS_STYLUS_TEMPLATE


def get_backend_template(name: str) -> Optional[BackendTemplate]:
    """Get a specific backend template by name."""
    return BACKEND_TEMPLATES.get(name)


def list_backend_templates() -> List[BackendTemplate]:
    """List all available backend templates."""
    return [
        NESTJS_STYLUS_TEMPLATE,
        EXPRESS_STYLUS_TEMPLATE,
        NESTJS_GRAPHQL_TEMPLATE,
        API_GATEWAY_TEMPLATE,
    ]


def generate_service_from_abi(abi: List[str], framework: str) -> Optional[str]:
    """Generate service methods and routes from ABI human-readable strings.

    Creates one method per ABI function:
    - GET endpoints for view/pure functions
    - POST endpoints for state-mutating functions

    Args:
        abi: Human-readable ABI strings.
        framework: "nestjs" or "express".

    Returns:
        TypeScript source for the service/routes, or None if no functions found.
    """
    read_funcs = []
    write_funcs = []

    for entry in abi:
        entry = entry.strip()
        if not entry.startswith("function "):
            continue

        func_part = entry[len("function "):]
        paren_idx = func_part.index("(")
        func_name = func_part[:paren_idx]

        # Parse arguments
        args_str = func_part[paren_idx + 1:func_part.index(")")]
        args = [a.strip() for a in args_str.split(",") if a.strip()]

        is_view = " view " in entry or " pure " in entry

        if is_view:
            read_funcs.append({"name": func_name, "args": args})
        else:
            write_funcs.append({"name": func_name, "args": args})

    if not read_funcs and not write_funcs:
        return None

    if framework == "express":
        return _generate_express_routes(read_funcs, write_funcs)
    return _generate_nestjs_service(read_funcs, write_funcs)


def _generate_nestjs_service(read_funcs: list, write_funcs: list) -> str:
    """Generate NestJS service methods from parsed ABI functions."""
    methods = []
    for func in read_funcs:
        name = func["name"]
        pascal = name[0].upper() + name[1:]
        methods.append(
            f"  async read{pascal}(): Promise<unknown> {{\n"
            f"    return await this.contract.read.{name}();\n"
            f"  }}"
        )
    for func in write_funcs:
        name = func["name"]
        pascal = name[0].upper() + name[1:]
        arg_names = [f"arg{i}" for i in range(len(func["args"]))]
        params = ", ".join(f"{a}: unknown" for a in arg_names)
        args_list = ", ".join(arg_names)
        methods.append(
            f"  async write{pascal}({params}): Promise<`0x${{string}}`> {{\n"
            f"    return await this.contract.write.{name}([{args_list}]);\n"
            f"  }}"
        )
    return "\n\n".join(methods)


def _generate_express_routes(read_funcs: list, write_funcs: list) -> str:
    """Generate Express route handlers from parsed ABI functions."""
    routes = []
    for func in read_funcs:
        name = func["name"]
        routes.append(
            f"contractRouter.get('/{name}', async (req, res, next) => {{\n"
            f"  try {{\n"
            f"    const client = getClient();\n"
            f"    const result = await client.readContract({{\n"
            f"      address: CONTRACT_ADDRESS,\n"
            f"      abi: CONTRACT_ABI,\n"
            f"      functionName: '{name}',\n"
            f"    }});\n"
            f"    res.json({{ {name}: result?.toString() }});\n"
            f"  }} catch (error) {{\n"
            f"    next(error);\n"
            f"  }}\n"
            f"}});"
        )
    for func in write_funcs:
        name = func["name"]
        routes.append(
            f"contractRouter.post('/{name}', async (req, res, next) => {{\n"
            f"  try {{\n"
            f"    const walletClient = getWalletClient();\n"
            f"    const client = getClient();\n"
            f"    const hash = await walletClient.writeContract({{\n"
            f"      address: CONTRACT_ADDRESS,\n"
            f"      abi: CONTRACT_ABI,\n"
            f"      functionName: '{name}',\n"
            f"      args: req.body.args || [],\n"
            f"    }});\n"
            f"    const receipt = await client.waitForTransactionReceipt({{ hash }});\n"
            f"    res.json({{ hash, blockNumber: receipt.blockNumber.toString(), status: receipt.status }});\n"
            f"  }} catch (error) {{\n"
            f"    next(error);\n"
            f"  }}\n"
            f"}});"
        )
    return "\n\n".join(routes)


def render_with_abi(files: Dict[str, str], abi_json: list, abi_human_readable: List[str]) -> Dict[str, str]:
    """Replace ABI placeholders in backend template files with actual ABI.

    If ABI is available, also regenerates service methods and routes.

    Args:
        files: Dict of path -> content from a BackendTemplate.
        abi_json: JSON ABI list (for NestJS full ABI format).
        abi_human_readable: Human-readable ABI strings (for Express parseAbi).

    Returns:
        New files dict with placeholders replaced and ABI-aware routes.
    """
    rendered = {}
    for path, content in files.items():
        if ABI_PLACEHOLDER in content:
            # For Express web3.ts using parseAbi([...])
            if "parseAbi(" in content:
                hr_lines = json.dumps(abi_human_readable, indent=2)
                content = content.replace(ABI_PLACEHOLDER, hr_lines)
            else:
                # For NestJS using full JSON ABI
                content = content.replace(
                    ABI_PLACEHOLDER,
                    json.dumps(abi_json, indent=2),
                )
        rendered[path] = content
    return rendered
