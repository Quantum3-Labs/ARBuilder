/**
 * GET /api/keys/usage
 *
 * Session-auth only. Returns current rate-limit counters and 24h activity
 * for every active key owned by the logged-in user. Used by /dashboard/keys
 * to render per-key usage widgets without making the user paste their keys.
 *
 * Like /api/v1/usage, this does NOT increment any counter.
 */

import { NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { auth } from "@/auth";
import { peekUsage, getLimitsForTier } from "@/lib/rateLimit";

interface KeyRow {
  id: string;
  rate_limit_tier: string;
  last_used_at: string | null;
}

interface UsageRow {
  api_key_id: string;
  total: number;
  ok: number | null;
  last: string | null;
}

export async function GET() {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { env } = getCloudflareContext();

    const keysRes = await env.DB
      .prepare(
        `SELECT id, rate_limit_tier, last_used_at
         FROM api_keys
         WHERE user_id = ? AND revoked_at IS NULL`,
      )
      .bind(session.user.id)
      .all<KeyRow>();

    const keys = keysRes.results ?? [];
    if (keys.length === 0) return NextResponse.json({ usage: {} });

    // Single 24h-window aggregate query for all of the user's keys.
    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const placeholders = keys.map(() => "?").join(",");
    const params = [...keys.map((k) => k.id), since];
    const usageRes = await env.DB
      .prepare(
        `SELECT api_key_id,
                COUNT(*) AS total,
                SUM(success) AS ok,
                MAX(created_at) AS last
         FROM usage_logs
         WHERE api_key_id IN (${placeholders}) AND created_at >= ?
         GROUP BY api_key_id`,
      )
      .bind(...params)
      .all<UsageRow>();

    const recentByKey = new Map<string, UsageRow>();
    for (const r of usageRes.results ?? []) recentByKey.set(r.api_key_id, r);

    // Read live counters from KV per key + category in parallel.
    const peeks = await Promise.all(
      keys.flatMap((k) => [
        peekUsage(env.KV, `key:${k.id}`, "chat", k.rate_limit_tier).then((d) => ({ id: k.id, cat: "chat" as const, d })),
        peekUsage(env.KV, `key:${k.id}`, "tool", k.rate_limit_tier).then((d) => ({ id: k.id, cat: "tool" as const, d })),
      ]),
    );

    const usage: Record<string, unknown> = {};
    for (const k of keys) {
      const chat = peeks.find((p) => p.id === k.id && p.cat === "chat")!.d;
      const tool = peeks.find((p) => p.id === k.id && p.cat === "tool")!.d;
      const r = recentByKey.get(k.id);
      const total = r?.total ?? 0;
      usage[k.id] = {
        tier: k.rate_limit_tier,
        limits: getLimitsForTier(k.rate_limit_tier),
        chat: { minute: chat.minute, day: chat.day },
        tool: { minute: tool.minute, day: tool.day },
        recent: {
          calls24h: total,
          lastCallAt: r?.last ?? null,
          successRate: total > 0 ? (r?.ok ?? 0) / total : null,
        },
      };
    }

    return NextResponse.json({ usage });
  } catch (e) {
    console.error("/api/keys/usage failed:", e);
    return NextResponse.json({ error: (e as Error).message || String(e) }, { status: 500 });
  }
}
