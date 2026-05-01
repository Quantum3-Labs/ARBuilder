/**
 * KV-backed daily rate limits keyed by API key (or userId for session auth).
 *
 * Counters live at `rl:{subject}:{category}:{YYYY-MM-DD}` with a 48h TTL so
 * day-rollover gracefully expires. Admin requests bypass entirely. Each tool
 * route + the chat route calls `enforceRateLimit()` once after auth.
 *
 * Tiers are intentionally code-defined (not in the DB) so they can be tuned
 * without a migration; api_keys.rate_limit_tier just stores the name.
 */

export type RateLimitCategory = "chat" | "tool";
export type RateLimitTier = "free" | "pro" | "unlimited";

interface TierLimits {
  chat: number;
  tool: number;
}

/**
 * Daily quota per tier per category. Tuned to match worst-case OpenRouter
 * spend on `openai/gpt-oss-120b` (chat ReAct loop is the dominant cost).
 *
 *   free: ~$1.50/key/day worst case (chat-heavy)
 *   pro:  ~$15/key/day worst case
 *   unlimited: effectively uncapped
 */
const TIER_LIMITS: Record<RateLimitTier, TierLimits> = {
  free: { chat: 30, tool: 100 },
  pro: { chat: 300, tool: 1000 },
  unlimited: { chat: 10000, tool: 10000 },
};

export function getLimitsForTier(tier: string): TierLimits {
  return TIER_LIMITS[(tier as RateLimitTier) in TIER_LIMITS ? (tier as RateLimitTier) : "free"];
}

export interface RateLimitDecision {
  allowed: boolean;
  limit: number;
  remaining: number;
  used: number;
  /** Seconds until counter resets (next UTC midnight). */
  resetSeconds: number;
  category: RateLimitCategory;
  tier: string;
}

function todayKey(): string {
  return new Date().toISOString().slice(0, 10);
}

function secondsUntilNextUtcMidnight(): number {
  const now = new Date();
  const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1));
  return Math.max(1, Math.floor((next.getTime() - now.getTime()) / 1000));
}

/**
 * Read-and-increment the daily counter for `subject` in `category`.
 *
 * Returns a decision before mutation: if the request is over the limit, the
 * counter is NOT incremented (so a flood of denied requests doesn't push the
 * number arbitrarily high). On allow, increments by 1 and writes back with a
 * 48-hour TTL.
 *
 * KV is eventually consistent across regions — a small overshoot is possible
 * under bursty traffic, which is acceptable for a per-day quota.
 */
export async function enforceRateLimit(
  kv: KVNamespace,
  subject: string,
  category: RateLimitCategory,
  tier: string,
): Promise<RateLimitDecision> {
  const limits = getLimitsForTier(tier);
  const limit = limits[category];
  const day = todayKey();
  const key = `rl:${subject}:${category}:${day}`;

  const raw = await kv.get(key);
  const used = raw ? parseInt(raw, 10) || 0 : 0;

  if (used >= limit) {
    return {
      allowed: false,
      limit,
      remaining: 0,
      used,
      resetSeconds: secondsUntilNextUtcMidnight(),
      category,
      tier,
    };
  }

  // 48h TTL — survives day rollover so late requests on the prior day
  // don't double-count, then auto-expires.
  await kv.put(key, String(used + 1), { expirationTtl: 60 * 60 * 48 });

  return {
    allowed: true,
    limit,
    remaining: limit - (used + 1),
    used: used + 1,
    resetSeconds: secondsUntilNextUtcMidnight(),
    category,
    tier,
  };
}

/**
 * Standard rate-limit response headers, matching the Cloudflare/Stripe convention.
 */
export function rateLimitHeaders(d: RateLimitDecision): Record<string, string> {
  const headers: Record<string, string> = {
    "X-RateLimit-Limit": String(d.limit),
    "X-RateLimit-Remaining": String(d.remaining),
    "X-RateLimit-Reset": String(d.resetSeconds),
    "X-RateLimit-Tier": d.tier,
  };
  if (!d.allowed) headers["Retry-After"] = String(d.resetSeconds);
  return headers;
}

/**
 * Rate-limit "subject" — what we count against. API keys count per key (so
 * a user can have a high-tier key and a free key separately). Session-auth
 * requests count per user. Admin is null (skip enforcement).
 */
export function subjectFor(auth: { keyId: string | null; userId: string | null; isAdmin: boolean }):
  | { subject: string; tier: string }
  | null {
  if (auth.isAdmin) return null;
  if (auth.keyId) {
    const tier = (auth as { rateLimitTier?: string }).rateLimitTier ?? "free";
    return { subject: `key:${auth.keyId}`, tier };
  }
  if (auth.userId) {
    // Session auth — always free tier, scoped per user.
    return { subject: `user:${auth.userId}`, tier: "free" };
  }
  return null;
}

/**
 * One-shot helper for `/api/v1/tools/*` routes. Returns either a 429 response
 * (when over limit) or a `headers` map to attach to the success response.
 *
 * Usage:
 *   const rl = await checkToolRateLimit(env.KV, auth);
 *   if ("response" in rl) return rl.response;
 *   return NextResponse.json(result, { headers: rl.headers });
 */
export async function checkToolRateLimit(
  kv: KVNamespace,
  auth: { keyId: string | null; userId: string | null; isAdmin: boolean; rateLimitTier?: string },
): Promise<{ headers: Record<string, string> } | { response: Response }> {
  const subj = subjectFor(auth);
  if (!subj) return { headers: {} };
  const decision = await enforceRateLimit(kv, subj.subject, "tool", subj.tier);
  const headers = rateLimitHeaders(decision);
  if (!decision.allowed) {
    const body = {
      error: `Daily tool rate limit exceeded (${decision.limit}/day on tier '${decision.tier}'). Try again in ${decision.resetSeconds}s.`,
      type: "rate_limit_exceeded",
      limit: decision.limit,
      used: decision.used,
      resetSeconds: decision.resetSeconds,
      tier: decision.tier,
    };
    return {
      response: new Response(JSON.stringify(body), {
        status: 429,
        headers: { "Content-Type": "application/json", ...headers },
      }),
    };
  }
  return { headers };
}
