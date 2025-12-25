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
    RESEND_API_KEY: string;
    TURNSTILE_SITE_KEY: string;
    TURNSTILE_SECRET_KEY: string;
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
    RESEND_API_KEY?: string;
    TURNSTILE_SITE_KEY?: string;
    TURNSTILE_SECRET_KEY?: string;
    OPENROUTER_API_KEY?: string;
    NEXT_PUBLIC_TURNSTILE_SITE_KEY?: string;
  }
}
