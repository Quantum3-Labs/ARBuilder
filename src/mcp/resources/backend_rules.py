"""
Backend Coding Rules Resource.

Provides coding guidelines and patterns for NestJS/Express backend development
with Web3 integration for Arbitrum dApps.
"""

BACKEND_CODING_RULES = {
    "name": "Backend Coding Rules",
    "version": "1.0.0",
    "description": "Guidelines for generating Web3-integrated backend services",

    "frameworks": {
        "nestjs": {
            "version": "10.x",
            "description": "Full-featured Node.js framework with decorators and dependency injection",
            "use_when": [
                "Complex API with multiple modules",
                "Need dependency injection",
                "GraphQL integration required",
                "Enterprise-grade applications",
            ],
        },
        "express": {
            "version": "4.x",
            "description": "Minimal, flexible Node.js web framework",
            "use_when": [
                "Simple REST API",
                "Lightweight requirements",
                "Quick prototypes",
                "Minimal overhead needed",
            ],
        },
    },

    "web3_integration": {
        "library": "viem",
        "version": "2.x",
        "description": "Type-safe Ethereum library (successor to ethers.js)",
        "advantages": [
            "Full TypeScript support",
            "Tree-shakeable",
            "Better performance than ethers",
            "Native BigInt support",
        ],
        "basic_setup": '''import { createPublicClient, createWalletClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { arbitrumSepolia } from 'viem/chains';

// Read-only client
const publicClient = createPublicClient({
  chain: arbitrumSepolia,
  transport: http(process.env.RPC_URL),
});

// Write client (requires private key)
const account = privateKeyToAccount(process.env.PRIVATE_KEY as `0x${string}`);
const walletClient = createWalletClient({
  account,
  chain: arbitrumSepolia,
  transport: http(process.env.RPC_URL),
});''',
    },

    "patterns": {
        "contract_service": {
            "description": "Service pattern for contract interactions",
            "nestjs_example": '''@Injectable()
export class ContractService implements OnModuleInit {
  private publicClient: PublicClient;
  private walletClient: WalletClient;

  constructor(private configService: ConfigService) {}

  async onModuleInit() {
    // Initialize clients
    this.publicClient = createPublicClient({
      chain: arbitrumSepolia,
      transport: http(this.configService.get('RPC_URL')),
    });
  }

  async readContract<T>(
    address: Address,
    abi: Abi,
    functionName: string,
    args?: unknown[],
  ): Promise<T> {
    return this.publicClient.readContract({
      address,
      abi,
      functionName,
      args,
    }) as Promise<T>;
  }

  async writeContract(
    address: Address,
    abi: Abi,
    functionName: string,
    args?: unknown[],
  ): Promise<Hash> {
    return this.walletClient.writeContract({
      address,
      abi,
      functionName,
      args,
    });
  }
}''',
        },

        "error_handling": {
            "description": "Handle blockchain errors gracefully",
            "example": '''async function safeContractCall<T>(
  fn: () => Promise<T>,
): Promise<{ success: true; data: T } | { success: false; error: string }> {
  try {
    const data = await fn();
    return { success: true, data };
  } catch (error) {
    if (error instanceof ContractFunctionExecutionError) {
      return { success: false, error: error.shortMessage };
    }
    if (error instanceof TransactionExecutionError) {
      return { success: false, error: 'Transaction failed' };
    }
    throw error;
  }
}''',
        },

        "transaction_tracking": {
            "description": "Wait for and track transaction confirmations",
            "example": '''async function executeAndWait(
  writeContract: () => Promise<Hash>,
): Promise<TransactionReceipt> {
  const hash = await writeContract();

  const receipt = await publicClient.waitForTransactionReceipt({
    hash,
    confirmations: 1,
  });

  if (receipt.status === 'reverted') {
    throw new Error('Transaction reverted');
  }

  return receipt;
}''',
        },

        "abi_management": {
            "description": "Type-safe ABI handling",
            "example": '''import { parseAbi } from 'viem';

// Define ABI as const for type inference
export const CONTRACT_ABI = parseAbi([
  'function balanceOf(address) view returns (uint256)',
  'function transfer(address to, uint256 amount) returns (bool)',
  'event Transfer(address indexed from, address indexed to, uint256 value)',
]);

// Or import from JSON
import ContractABI from '../abis/Contract.json';''',
        },
    },

    "security": {
        "private_key_handling": {
            "rules": [
                "Never hardcode private keys",
                "Use environment variables",
                "Consider using AWS KMS or HashiCorp Vault for production",
                "Never log private keys or transactions with sensitive data",
            ],
            "example": '''// Good
const privateKey = process.env.PRIVATE_KEY;
if (!privateKey) {
  throw new Error('PRIVATE_KEY environment variable required');
}

// Bad - NEVER do this
const privateKey = '0x1234...'; // Hardcoded key''',
        },

        "input_validation": {
            "rules": [
                "Validate all user inputs",
                "Use class-validator in NestJS",
                "Validate addresses with viem's isAddress",
                "Sanitize BigInt inputs",
            ],
            "example": '''import { isAddress, parseEther } from 'viem';
import { IsString, IsNotEmpty, Validate } from 'class-validator';

export class TransferDto {
  @IsString()
  @Validate((value: string) => isAddress(value), {
    message: 'Invalid Ethereum address',
  })
  to: string;

  @IsString()
  @IsNotEmpty()
  amount: string;
}''',
        },

        "rate_limiting": {
            "description": "Protect against abuse",
            "example": '''// NestJS throttler
import { ThrottlerGuard, ThrottlerModule } from '@nestjs/throttler';

@Module({
  imports: [
    ThrottlerModule.forRoot([{
      ttl: 60000,  // 1 minute
      limit: 10,   // 10 requests per minute
    }]),
  ],
})
export class AppModule {}''',
        },
    },

    "best_practices": [
        "Use TypeScript strict mode",
        "Implement health check endpoints",
        "Add request logging middleware",
        "Use connection pooling for RPC calls",
        "Implement retry logic for failed transactions",
        "Cache read-only contract data when appropriate",
        "Use BigInt for all token amounts",
        "Handle network-specific configurations",
    ],

    "dependencies": {
        "core": {
            "viem": "^2.0.0",
            "dotenv": "^16.0.0",
        },
        "nestjs": {
            "@nestjs/common": "^10.0.0",
            "@nestjs/core": "^10.0.0",
            "@nestjs/config": "^3.1.0",
            "class-validator": "^0.14.0",
            "class-transformer": "^0.5.1",
        },
        "express": {
            "express": "^4.18.0",
            "cors": "^2.8.5",
        },
    },

    "environment_variables": {
        "required": [
            "RPC_URL - Arbitrum RPC endpoint",
            "PRIVATE_KEY - Wallet private key (for write operations)",
            "CONTRACT_ADDRESS - Deployed contract address",
        ],
        "optional": [
            "PORT - Server port (default: 3001)",
            "NODE_ENV - Environment (development/production)",
            "LOG_LEVEL - Logging verbosity",
        ],
    },
}
