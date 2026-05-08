/**
 * GET /api/v1/usage
 *
 * Returns the current rate-limit state for the authenticated key:
 *   - tier
 *   - chat counters (minute + day windows)
 *   - tool counters (minute + day windows)
 *   - recent activity summary (24h call count + last call time, from D1)
 *
 * This endpoint is itself rate-limit free (it does not increment any
 * counters), so clients can poll it to plan around the limits without
 * burning a slot. Auth is the same as every other v1 endpoint.
 */

import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";
import { peekUsage, subjectFor } from "@/lib/rateLimit";
import { evaluateCors, preflightResponse } from "@/lib/cors";

export async function GET(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();

    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

    const cors = evaluateCors(request, auth.allowedOrigins);
    if (!cors.ok) return cors.response;

    const subj = subjectFor(auth);
    const tier = subj?.tier ?? (auth.isAdmin ? "unlimited" : "free");

    // Admin requests have no subject — return tier limits with zero usage.
    if (!subj) {
      const placeholder = await peekUsage(env.KV, "admin", "chat", tier);
      const placeholderTool = await peekUsage(env.KV, "admin", "tool", tier);
      return NextResponse.json({
        tier,
        admin: true,
        chat: { minute: placeholder.minute, day: placeholder.day },
        tool: { minute: placeholderTool.minute, day: placeholderTool.day },
        recent: null,
      }, { headers: cors.headers });
    }

    const [chatUsage, toolUsage] = await Promise.all([
      peekUsage(env.KV, subj.subject, "chat", tier),
      peekUsage(env.KV, subj.subject, "tool", tier),
    ]);

    // 24h activity summary from usage_logs (only for API-key auth — session
    // auth doesn't have a key_id to filter on).
    let recent: {
      calls24h: number;
      lastCallAt: string | null;
      successRate: number | null;
    } | null = null;
    if (auth.keyId) {
      const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
      const row = await env.DB
        .prepare(
          `SELECT COUNT(*) AS total,
                  SUM(success) AS ok,
                  MAX(created_at) AS last
           FROM usage_logs
           WHERE api_key_id = ? AND created_at >= ?`,
        )
        .bind(auth.keyId, since)
        .first<{ total: number; ok: number | null; last: string | null }>();
      const total = row?.total ?? 0;
      recent = {
        calls24h: total,
        lastCallAt: row?.last ?? null,
        successRate: total > 0 ? (row?.ok ?? 0) / total : null,
      };
    }

    return NextResponse.json({
      tier,
      admin: false,
      chat: { minute: chatUsage.minute, day: chatUsage.day },
      tool: { minute: toolUsage.minute, day: toolUsage.day },
      recent,
    }, { headers: cors.headers });
  } catch (e) {
    console.error("usage endpoint failed:", e);
    return NextResponse.json(
      { error: (e as Error).message || String(e) },
      { status: 500 },
    );
  }
}

export async function OPTIONS(request: NextRequest) {
  return preflightResponse(request, "GET, OPTIONS");
}
