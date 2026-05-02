/**
 * Admin API for managing per-key rate-limit tiers.
 *
 *   GET    /api/admin/rate-limits             — list all api_keys with tier + recent usage
 *   PATCH  /api/admin/rate-limits             — body: { keyId, tier } — update tier on a key
 *
 * Headers: X-Admin-Secret: <AUTH_SECRET>
 *
 * Tiers are validated against TIER_LIMITS in @/lib/rateLimit.
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { getLimitsForTier, type RateLimitTier } from "@/lib/rateLimit";

const VALID_TIERS: RateLimitTier[] = ["free", "pro", "unlimited"];

function verifyAuth(request: NextRequest, authSecret: string): boolean {
  return request.headers.get("X-Admin-Secret") === authSecret;
}

interface KeyRow {
  id: string;
  user_id: string;
  user_email: string | null;
  key_prefix: string;
  name: string | null;
  rate_limit_tier: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
  calls_24h: number;
}

export async function GET(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

    const result = await env.DB
      .prepare(
        `SELECT k.id, k.user_id, u.email AS user_email, k.key_prefix, k.name,
                k.rate_limit_tier, k.created_at, k.last_used_at, k.revoked_at,
                COALESCE(c.cnt, 0) AS calls_24h
         FROM api_keys k
         LEFT JOIN users u ON u.id = k.user_id
         LEFT JOIN (
           SELECT api_key_id, COUNT(*) AS cnt
           FROM usage_logs
           WHERE created_at >= ?
           GROUP BY api_key_id
         ) c ON c.api_key_id = k.id
         ORDER BY k.created_at DESC
         LIMIT 500`,
      )
      .bind(since)
      .all<KeyRow>();

    const keys = (result.results ?? []).map((r) => {
      const lim = getLimitsForTier(r.rate_limit_tier);
      return {
        id: r.id,
        userId: r.user_id,
        userEmail: r.user_email,
        keyPrefix: r.key_prefix,
        name: r.name,
        tier: r.rate_limit_tier,
        limits: { perMinute: lim.perMinute, perDay: lim.perDay },
        createdAt: r.created_at,
        lastUsedAt: r.last_used_at,
        revokedAt: r.revoked_at,
        calls24h: r.calls_24h,
      };
    });

    return NextResponse.json({ tiers: VALID_TIERS, keys });
  } catch (e) {
    console.error("admin/rate-limits GET failed:", e);
    return NextResponse.json({ error: (e as Error).message || String(e) }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    if (!verifyAuth(request, env.AUTH_SECRET)) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = (await request.json().catch(() => ({}))) as {
      keyId?: string;
      tier?: string;
    };
    if (!body.keyId || !body.tier) {
      return NextResponse.json({ error: "Missing keyId or tier" }, { status: 400 });
    }
    if (!VALID_TIERS.includes(body.tier as RateLimitTier)) {
      return NextResponse.json(
        { error: `Invalid tier. Must be one of: ${VALID_TIERS.join(", ")}` },
        { status: 400 },
      );
    }

    const r = await env.DB
      .prepare(`UPDATE api_keys SET rate_limit_tier = ? WHERE id = ?`)
      .bind(body.tier, body.keyId)
      .run();

    if (r.meta.changes === 0) {
      return NextResponse.json({ error: "Key not found" }, { status: 404 });
    }

    const lim = getLimitsForTier(body.tier);
    return NextResponse.json({
      ok: true,
      keyId: body.keyId,
      tier: body.tier,
      limits: { perMinute: lim.perMinute, perDay: lim.perDay },
    });
  } catch (e) {
    console.error("admin/rate-limits PATCH failed:", e);
    return NextResponse.json({ error: (e as Error).message || String(e) }, { status: 500 });
  }
}
