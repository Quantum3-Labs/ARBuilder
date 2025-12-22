// Extend Cloudflare environment with our custom bindings
declare global {
  namespace Cloudflare {
    interface Env {
      // D1 Database
      DB: D1Database;

      // Vectorize index
      VECTORIZE: VectorizeIndex;

      // Workers AI
      AI: Ai;

      // KV namespace
      KV: KVNamespace;

      // Auth.js secrets
      AUTH_SECRET: string;
      AUTH_GITHUB_ID: string;
      AUTH_GITHUB_SECRET: string;
      AUTH_GOOGLE_ID: string;
      AUTH_GOOGLE_SECRET: string;

      // OpenRouter
      OPENROUTER_API_KEY: string;
    }
  }
}

export {};
