/**
 * Two-window rate limiter: per-minute burst + per-day total.
 *
 * Both windows must allow a request; whichever is exhausted first triggers
 * the 429. Counters are KV-backed, keyed per subject (API key id, or user
 * id for session auth) and per category (chat or tool). Admin Bearer auth
 * bypasses entirely.
 *
 *   minute counter:  rl:{subject}:{category}:m:{YYYY-MM-DDTHH:MM}  TTL 120s
 *   daily counter:   rl:{subject}:{category}:d:{YYYY-MM-DD}        TTL 48h
 *
 * KV is eventually consistent across regions, so a small overshoot is
 * possible under bursty traffic. That's acceptable for a quota.
 */

export type RateLimitCategory = "chat" | "tool";
export type RateLimitTier = "free" | "pro" | "unlimited";

interface TierLimits {
  /** Burst limit per UTC minute. */
  perMinute: number;
  /** Total per UTC day. */
  perDay: number;
}

/**
 * Per-tier limits. Applied identically to both `chat` and `tool` categories
 * (each category maintains its own counters). Tuned to allow normal API usage
 * while putting a worst-case daily cost ceiling on each free key.
 */
const TIER_LIMITS: Record<RateLimitTier, TierLimits> = {
  free: { perMinute: 100, perDay: 1000 },
  pro: { perMinute: 500, perDay: 10000 },
  unlimited: { perMinute: 10000, perDay: 1000000 },
};

export function getLimitsForTier(tier: string): TierLimits {
  return TIER_LIMITS[(tier as RateLimitTier) in TIER_LIMITS ? (tier as RateLimitTier) : "free"];
}

export interface RateLimitDecision {
  allowed: boolean;
  /** Which window denied the request, if any. */
  exceededWindow?: "minute" | "day";
  category: RateLimitCategory;
  tier: string;
  minute: { limit: number; remaining: number; used: number; resetSeconds: number };
  day: { limit: number; remaining: number; used: number; resetSeconds: number };
}

function minuteKey(): string {
  return new Date().toISOString().slice(0, 16); // "YYYY-MM-DDTHH:MM"
}

function dayKey(): string {
  return new Date().toISOString().slice(0, 10);
}

function secondsUntilNextUtcMinute(): number {
  const now = new Date();
  const next = new Date(now);
  next.setUTCSeconds(0, 0);
  next.setUTCMinutes(next.getUTCMinutes() + 1);
  return Math.max(1, Math.floor((next.getTime() - now.getTime()) / 1000));
}

function secondsUntilNextUtcMidnight(): number {
  const now = new Date();
  const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1));
  return Math.max(1, Math.floor((next.getTime() - now.getTime()) / 1000));
}

/**
 * Check both windows, deny if either is over the limit, otherwise increment
 * both. On deny, neither counter is incremented (so a flood of denied requests
 * doesn't push either number arbitrarily high).
 */
export async function enforceRateLimit(
  kv: KVNamespace,
  subject: string,
  category: RateLimitCategory,
  tier: string,
): Promise<RateLimitDecision> {
  const { perMinute, perDay } = getLimitsForTier(tier);
  const mKey = `rl:${subject}:${category}:m:${minuteKey()}`;
  const dKey = `rl:${subject}:${category}:d:${dayKey()}`;
  const minResetSec = secondsUntilNextUtcMinute();
  const dayResetSec = secondsUntilNextUtcMidnight();

  const [mRaw, dRaw] = await Promise.all([kv.get(mKey), kv.get(dKey)]);
  const mUsed = mRaw ? parseInt(mRaw, 10) || 0 : 0;
  const dUsed = dRaw ? parseInt(dRaw, 10) || 0 : 0;

  const overMinute = mUsed >= perMinute;
  const overDay = dUsed >= perDay;

  if (overMinute || overDay) {
    return {
      allowed: false,
      exceededWindow: overMinute ? "minute" : "day",
      category,
      tier,
      minute: { limit: perMinute, remaining: Math.max(0, perMinute - mUsed), used: mUsed, resetSeconds: minResetSec },
      day: { limit: perDay, remaining: Math.max(0, perDay - dUsed), used: dUsed, resetSeconds: dayResetSec },
    };
  }

  // Increment both (best-effort parallel; KV is eventually consistent, small overshoot is acceptable).
  await Promise.all([
    kv.put(mKey, String(mUsed + 1), { expirationTtl: 120 }),
    kv.put(dKey, String(dUsed + 1), { expirationTtl: 60 * 60 * 48 }),
  ]);

  return {
    allowed: true,
    category,
    tier,
    minute: { limit: perMinute, remaining: perMinute - (mUsed + 1), used: mUsed + 1, resetSeconds: minResetSec },
    day: { limit: perDay, remaining: perDay - (dUsed + 1), used: dUsed + 1, resetSeconds: dayResetSec },
  };
}

/**
 * Standard rate-limit response headers. Reports both windows so clients can
 * see which one is closer to exhaustion. The single-valued headers
 * (X-RateLimit-Limit / -Remaining / -Reset) reflect the *bottleneck* —
 * whichever window has fewer remaining calls — for clients that only check
 * the canonical names. Retry-After on a 429 uses the bottleneck window.
 */
export function rateLimitHeaders(d: RateLimitDecision): Record<string, string> {
  const bottleneck = d.minute.remaining <= d.day.remaining ? d.minute : d.day;
  const headers: Record<string, string> = {
    "X-RateLimit-Limit": String(bottleneck.limit),
    "X-RateLimit-Remaining": String(bottleneck.remaining),
    "X-RateLimit-Reset": String(bottleneck.resetSeconds),
    "X-RateLimit-Tier": d.tier,
    "X-RateLimit-Limit-Minute": String(d.minute.limit),
    "X-RateLimit-Remaining-Minute": String(d.minute.remaining),
    "X-RateLimit-Reset-Minute": String(d.minute.resetSeconds),
    "X-RateLimit-Limit-Day": String(d.day.limit),
    "X-RateLimit-Remaining-Day": String(d.day.remaining),
    "X-RateLimit-Reset-Day": String(d.day.resetSeconds),
  };
  if (!d.allowed) {
    const denyWindow = d.exceededWindow === "minute" ? d.minute : d.day;
    headers["Retry-After"] = String(denyWindow.resetSeconds);
  }
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
 * Read-only snapshot of current usage for `subject` in `category`. Does NOT
 * increment counters — used by GET /api/v1/usage so callers can plan around
 * the limits without burning a slot.
 */
export async function peekUsage(
  kv: KVNamespace,
  subject: string,
  category: RateLimitCategory,
  tier: string,
): Promise<RateLimitDecision> {
  const { perMinute, perDay } = getLimitsForTier(tier);
  const mKey = `rl:${subject}:${category}:m:${minuteKey()}`;
  const dKey = `rl:${subject}:${category}:d:${dayKey()}`;

  const [mRaw, dRaw] = await Promise.all([kv.get(mKey), kv.get(dKey)]);
  const mUsed = mRaw ? parseInt(mRaw, 10) || 0 : 0;
  const dUsed = dRaw ? parseInt(dRaw, 10) || 0 : 0;

  const overMinute = mUsed >= perMinute;
  const overDay = dUsed >= perDay;
  const allowed = !(overMinute || overDay);

  return {
    allowed,
    exceededWindow: allowed ? undefined : overMinute ? "minute" : "day",
    category,
    tier,
    minute: {
      limit: perMinute,
      remaining: Math.max(0, perMinute - mUsed),
      used: mUsed,
      resetSeconds: secondsUntilNextUtcMinute(),
    },
    day: {
      limit: perDay,
      remaining: Math.max(0, perDay - dUsed),
      used: dUsed,
      resetSeconds: secondsUntilNextUtcMidnight(),
    },
  };
}

/**
 * One-shot helper for `/api/v1/tools/*` routes. Returns either a 429 response
 * (when over either limit) or a `headers` map to attach to the success response.
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
    const denyWindow = decision.exceededWindow === "minute" ? decision.minute : decision.day;
    const windowLabel = decision.exceededWindow === "minute" ? "per-minute" : "per-day";
    const body = {
      error: `Tool rate limit exceeded (${windowLabel}: ${denyWindow.limit} on tier '${decision.tier}'). Try again in ${denyWindow.resetSeconds}s.`,
      type: "rate_limit_exceeded",
      window: decision.exceededWindow,
      limit: denyWindow.limit,
      used: denyWindow.used,
      resetSeconds: denyWindow.resetSeconds,
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
