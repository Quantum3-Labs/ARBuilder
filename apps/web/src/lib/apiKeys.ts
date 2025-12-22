/**
 * API Key management utilities.
 *
 * Handles creation, validation, and revocation of API keys.
 * Uses Web Crypto API for Edge runtime compatibility.
 */

export interface ApiKey {
  id: string;
  userId: string;
  keyPrefix: string;
  name: string | null;
  createdAt: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
}

export interface ApiKeyWithSecret extends ApiKey {
  key: string; // Full key, only returned on creation
}

/**
 * Generate random bytes as hex string using Web Crypto API.
 */
function randomHex(bytes: number): string {
  const array = new Uint8Array(bytes);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Hash an API key for storage using Web Crypto API.
 */
export async function hashApiKey(key: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(key);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Generate a new API key.
 * Format: arb_<32 random hex characters>
 */
export async function generateApiKey(): Promise<{
  key: string;
  keyHash: string;
  keyPrefix: string;
}> {
  const randomPart = randomHex(16);
  const key = `arb_${randomPart}`;
  const keyHash = await hashApiKey(key);
  const keyPrefix = `arb_${randomPart.slice(0, 8)}...`;

  return { key, keyHash, keyPrefix };
}

/**
 * Create a new API key in the database.
 */
export async function createApiKey(
  db: D1Database,
  userId: string,
  name?: string
): Promise<ApiKeyWithSecret> {
  const { key, keyHash, keyPrefix } = await generateApiKey();
  const id = randomHex(8);
  const now = new Date().toISOString();

  await db
    .prepare(
      `INSERT INTO api_keys (id, user_id, key_hash, key_prefix, name, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`
    )
    .bind(id, userId, keyHash, keyPrefix, name || null, now)
    .run();

  return {
    id,
    userId,
    keyPrefix,
    name: name || null,
    createdAt: now,
    lastUsedAt: null,
    revokedAt: null,
    key, // Only returned on creation
  };
}

/**
 * List all API keys for a user.
 */
export async function listApiKeys(
  db: D1Database,
  userId: string
): Promise<ApiKey[]> {
  const result = await db
    .prepare(
      `SELECT id, user_id as userId, key_prefix as keyPrefix, name,
              created_at as createdAt, last_used_at as lastUsedAt, revoked_at as revokedAt
       FROM api_keys
       WHERE user_id = ? AND revoked_at IS NULL
       ORDER BY created_at DESC`
    )
    .bind(userId)
    .all<ApiKey>();

  return result.results;
}

/**
 * Revoke an API key.
 */
export async function revokeApiKey(
  db: D1Database,
  keyId: string,
  userId: string
): Promise<boolean> {
  const now = new Date().toISOString();

  const result = await db
    .prepare(
      `UPDATE api_keys SET revoked_at = ?
       WHERE id = ? AND user_id = ? AND revoked_at IS NULL`
    )
    .bind(now, keyId, userId)
    .run();

  return result.meta.changes > 0;
}

/**
 * Validate an API key and return the associated user.
 */
export async function validateApiKey(
  db: D1Database,
  key: string
): Promise<{ userId: string; keyId: string } | null> {
  const keyHash = await hashApiKey(key);

  const result = await db
    .prepare(
      `SELECT id, user_id as userId FROM api_keys
       WHERE key_hash = ? AND revoked_at IS NULL`
    )
    .bind(keyHash)
    .first<{ id: string; userId: string }>();

  if (result) {
    // Update last used timestamp
    await db
      .prepare(`UPDATE api_keys SET last_used_at = ? WHERE id = ?`)
      .bind(new Date().toISOString(), result.id)
      .run();

    return { userId: result.userId, keyId: result.id };
  }

  return null;
}

/**
 * Log API usage.
 */
export async function logApiUsage(
  db: D1Database,
  apiKeyId: string,
  tool: string,
  tokensUsed: number,
  latencyMs: number,
  success: boolean = true,
  errorMessage?: string
): Promise<void> {
  const id = randomHex(8);

  await db
    .prepare(
      `INSERT INTO usage_logs (id, api_key_id, tool, tokens_used, latency_ms, success, error_message, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(
      id,
      apiKeyId,
      tool,
      tokensUsed,
      latencyMs,
      success ? 1 : 0,
      errorMessage || null,
      new Date().toISOString()
    )
    .run();
}

/**
 * Get usage statistics for a user.
 */
export async function getUsageStats(
  db: D1Database,
  userId: string,
  days: number = 30
): Promise<{
  totalCalls: number;
  totalTokens: number;
  callsByTool: Record<string, number>;
  dailyUsage: Array<{ date: string; calls: number; tokens: number }>;
}> {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - days);
  const cutoffStr = cutoffDate.toISOString();

  // Get total stats
  const totals = await db
    .prepare(
      `SELECT COUNT(*) as totalCalls, COALESCE(SUM(tokens_used), 0) as totalTokens
       FROM usage_logs ul
       JOIN api_keys ak ON ul.api_key_id = ak.id
       WHERE ak.user_id = ? AND ul.created_at >= ?`
    )
    .bind(userId, cutoffStr)
    .first<{ totalCalls: number; totalTokens: number }>();

  // Get calls by tool
  const byTool = await db
    .prepare(
      `SELECT ul.tool, COUNT(*) as count
       FROM usage_logs ul
       JOIN api_keys ak ON ul.api_key_id = ak.id
       WHERE ak.user_id = ? AND ul.created_at >= ?
       GROUP BY ul.tool`
    )
    .bind(userId, cutoffStr)
    .all<{ tool: string; count: number }>();

  const callsByTool: Record<string, number> = {};
  for (const row of byTool.results) {
    callsByTool[row.tool] = row.count;
  }

  // Get daily usage
  const daily = await db
    .prepare(
      `SELECT DATE(ul.created_at) as date, COUNT(*) as calls, COALESCE(SUM(tokens_used), 0) as tokens
       FROM usage_logs ul
       JOIN api_keys ak ON ul.api_key_id = ak.id
       WHERE ak.user_id = ? AND ul.created_at >= ?
       GROUP BY DATE(ul.created_at)
       ORDER BY date DESC`
    )
    .bind(userId, cutoffStr)
    .all<{ date: string; calls: number; tokens: number }>();

  return {
    totalCalls: totals?.totalCalls ?? 0,
    totalTokens: totals?.totalTokens ?? 0,
    callsByTool,
    dailyUsage: daily.results,
  };
}
