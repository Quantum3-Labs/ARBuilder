/**
 * CORS handling shared by every authenticated API route.
 *
 * Two layers:
 *   1. Preflight (OPTIONS) — permissive: we don't know which API key the
 *      caller will use, so we allow any origin to ask the question. Browsers
 *      will only proceed to the real request if the actual response also
 *      passes CORS.
 *   2. Actual request — enforced against the API key's `allowed_origins`
 *      column. If the Origin header is set and doesn't match, we 403.
 *      Server-to-server callers (no Origin header) bypass entirely; the
 *      column is purely a browser-protection mechanism.
 *
 * Responses always include `Vary: Origin` so caches don't serve a response
 * built for one origin to a request from another.
 */

import { NextRequest, NextResponse } from "next/server";

/**
 * Decide what `Access-Control-Allow-Origin` to send and whether the request
 * is allowed. Call this after auth, before doing any work.
 *
 * Returns:
 *   - { ok: true, headers }  — attach `headers` to the response
 *   - { ok: false, response } — the request must be rejected (403 with
 *     CORS body so the browser surfaces a useful error)
 */
export function evaluateCors(
  request: NextRequest,
  allowedOrigins: string[] | null | undefined,
): { ok: true; headers: Record<string, string> } | { ok: false; response: NextResponse } {
  const origin = request.headers.get("Origin");

  // No Origin → server-to-server, allowlist doesn't apply.
  if (!origin) {
    return { ok: true, headers: { Vary: "Origin" } };
  }

  // No restriction set on the key → reflect the origin so it works in browsers
  // without exposing `*` to credentialed flows.
  if (allowedOrigins == null) {
    return { ok: true, headers: corsAllowHeaders(origin) };
  }

  // Explicit "any" wildcard.
  if (allowedOrigins.includes("*")) {
    return { ok: true, headers: corsAllowHeaders(origin) };
  }

  // Locked or non-matching.
  if (!allowedOrigins.includes(origin)) {
    const body = {
      error: `Origin '${origin}' is not in this API key's allowlist.`,
      type: "origin_not_allowed",
      allowedOrigins,
    };
    const response = new NextResponse(JSON.stringify(body), {
      status: 403,
      headers: { "Content-Type": "application/json", Vary: "Origin" },
    });
    return { ok: false, response };
  }

  return { ok: true, headers: corsAllowHeaders(origin) };
}

function corsAllowHeaders(origin: string): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Expose-Headers":
      "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, X-RateLimit-Tier, " +
      "X-RateLimit-Limit-Minute, X-RateLimit-Remaining-Minute, X-RateLimit-Reset-Minute, " +
      "X-RateLimit-Limit-Day, X-RateLimit-Remaining-Day, X-RateLimit-Reset-Day, Retry-After",
    Vary: "Origin",
  };
}

/**
 * Standardised OPTIONS preflight. Permissive by design — browsers send
 * preflights without Authorization, so we can't validate against a key's
 * allowlist here. Reflects the request's Origin so credentialed mode works.
 */
export function preflightResponse(request: NextRequest, methods = "POST, OPTIONS"): NextResponse {
  const origin = request.headers.get("Origin") ?? "*";
  const requestedHeaders = request.headers.get("Access-Control-Request-Headers")
    ?? "Content-Type, Authorization, X-Admin-Secret";
  return new NextResponse(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Credentials": "true",
      "Access-Control-Allow-Methods": methods,
      "Access-Control-Allow-Headers": requestedHeaders,
      "Access-Control-Max-Age": "86400",
      Vary: "Origin, Access-Control-Request-Headers",
    },
  });
}

/**
 * Parse the JSON-array column. Tolerant of legacy NULL or malformed values.
 */
export function parseAllowedOrigins(raw: string | null | undefined): string[] | null {
  if (raw == null) return null;
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.every((v) => typeof v === "string")) return parsed;
    return null;
  } catch {
    return null;
  }
}

/**
 * Validate origin strings provided by users (e.g., via PATCH /api/keys/[id]).
 * Accepts full URLs with scheme + host (no path/query/fragment), or "*".
 * Returns the normalised list, or throws with a helpful message.
 */
export function validateOriginList(origins: unknown): string[] {
  if (!Array.isArray(origins)) throw new Error("allowedOrigins must be an array of origin strings");
  const out: string[] = [];
  for (const raw of origins) {
    if (typeof raw !== "string") throw new Error("allowedOrigins entries must be strings");
    const v = raw.trim();
    if (!v) continue;
    if (v === "*") {
      out.push("*");
      continue;
    }
    let url: URL;
    try {
      url = new URL(v);
    } catch {
      throw new Error(`Invalid origin '${v}' — must be a full URL (e.g., 'https://docs.example.com') or '*'`);
    }
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      throw new Error(`Origin '${v}' must use http or https`);
    }
    if (url.pathname !== "/" && url.pathname !== "") {
      throw new Error(`Origin '${v}' must not include a path`);
    }
    // Canonical form: scheme://host[:port]
    out.push(`${url.protocol}//${url.host}`);
  }
  // De-dupe.
  return Array.from(new Set(out));
}
