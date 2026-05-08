/**
 * Unified request validation for API routes.
 *
 * Supports:
 * - User API keys (arb_*) validated against database
 * - Session cookies (auth-token JWT) for logged-in users
 * - Admin secret (AUTH_SECRET) for internal use
 */

import { NextRequest, NextResponse } from "next/server";
import { hashApiKey } from "@/lib/apiKeys";
import { verifyJWT } from "@/lib/jwt";
import { parseAllowedOrigins } from "@/lib/cors";

export interface AuthResult {
  success: true;
  userId: string | null;
  keyId: string | null;
  isAdmin: boolean;
  /** Rate limit tier; only set for API-key auth. Session auth uses 'free' implicitly. */
  rateLimitTier?: string;
  /** CORS allowlist; only set for API-key auth. null = unrestricted. */
  allowedOrigins?: string[] | null;
}

export interface AuthError {
  success: false;
  response: NextResponse;
}

/**
 * Validate a request using API key, session cookie, or admin secret.
 *
 * @param request - The incoming request
 * @param db - D1 database instance (optional, needed for user API keys and session auth)
 * @param authSecret - AUTH_SECRET env var (optional, for admin access)
 * @returns AuthResult if valid, AuthError if invalid
 */
export async function validateRequest(
  request: NextRequest,
  db?: D1Database,
  authSecret?: string
): Promise<AuthResult | AuthError> {
  const authHeader = request.headers.get("Authorization");

  // Try Bearer token auth (API key or admin secret)
  if (authHeader?.startsWith("Bearer ")) {
    const token = authHeader.slice(7);

    if (!token) {
      return {
        success: false,
        response: NextResponse.json(
          { error: "Unauthorized - Empty token" },
          { status: 401 }
        ),
      };
    }

    // Check if it's a user API key (starts with arb_)
    if (token.startsWith("arb_") && db) {
      const keyHash = await hashApiKey(token);

      const result = await db
        .prepare(
          `SELECT id, user_id as userId, rate_limit_tier as rateLimitTier,
                  allowed_origins as allowedOrigins
           FROM api_keys
           WHERE key_hash = ? AND revoked_at IS NULL`
        )
        .bind(keyHash)
        .first<{ id: string; userId: string; rateLimitTier: string | null; allowedOrigins: string | null }>();

      if (result) {
        // Update last used timestamp
        await db
          .prepare(`UPDATE api_keys SET last_used_at = ? WHERE id = ?`)
          .bind(new Date().toISOString(), result.id)
          .run();

        return {
          success: true,
          userId: result.userId,
          keyId: result.id,
          isAdmin: false,
          rateLimitTier: result.rateLimitTier ?? "free",
          allowedOrigins: parseAllowedOrigins(result.allowedOrigins),
        };
      }

      // Invalid or revoked API key
      return {
        success: false,
        response: NextResponse.json(
          { error: "Unauthorized - Invalid or revoked API key" },
          { status: 401 }
        ),
      };
    }

    // Check if it's the admin secret
    if (authSecret && token === authSecret) {
      return {
        success: true,
        userId: null,
        keyId: null,
        isAdmin: true,
      };
    }
  }

  // Try session cookie auth (for logged-in users via browser)
  const sessionToken = request.cookies.get("auth-token")?.value;
  if (sessionToken && db) {
    try {
      const payload = await verifyJWT(db, sessionToken);
      if (payload && payload.type === "access") {
        const user = await db
          .prepare(`SELECT id FROM users WHERE id = ?`)
          .bind(payload.sub)
          .first<{ id: string }>();

        if (user) {
          return {
            success: true,
            userId: user.id,
            keyId: null,
            isAdmin: false,
          };
        }
      }
    } catch (err) {
      console.error("Session auth error:", err);
      // Session token invalid, fall through to error
    }
  }

  // If we had a session token but it failed, return a specific message
  if (sessionToken) {
    return {
      success: false,
      response: NextResponse.json(
        { error: "Session expired - please refresh the page to re-authenticate" },
        { status: 401 }
      ),
    };
  }

  // No valid auth found
  return {
    success: false,
    response: NextResponse.json(
      { error: "Unauthorized - Missing or invalid credentials" },
      { status: 401 }
    ),
  };
}
