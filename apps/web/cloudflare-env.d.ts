/**
 * Cloudflare environment bindings type definitions.
 *
 * Run `wrangler types` to regenerate full runtime types if needed.
 */

declare namespace Cloudflare {
  interface Env {
    // KV Namespace
    KV: KVNamespace;

    // D1 Database
    DB: D1Database;

    // Vectorize Index
    VECTORIZE: VectorizeIndex;

    // Workers AI
    AI: Ai;

    // Environment variables
    NEXTJS_ENV: string;
    AUTH_SECRET: string;
    AUTH_GITHUB_ID: string;
    AUTH_GITHUB_SECRET: string;
    AUTH_GOOGLE_ID: string;
    AUTH_GOOGLE_SECRET: string;
    OPENROUTER_API_KEY: string;

    // Auto-generated bindings
    WORKER_SELF_REFERENCE: Fetcher;
    IMAGES: ImagesBinding;
    ASSETS: Fetcher;
  }
}

interface CloudflareEnv extends Cloudflare.Env {}

declare namespace NodeJS {
  interface ProcessEnv {
    NEXTJS_ENV?: string;
    AUTH_SECRET?: string;
    AUTH_GITHUB_ID?: string;
    AUTH_GITHUB_SECRET?: string;
    AUTH_GOOGLE_ID?: string;
    AUTH_GOOGLE_SECRET?: string;
    OPENROUTER_API_KEY?: string;
  }
}
