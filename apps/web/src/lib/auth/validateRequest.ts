/**
 * Unified request validation for API routes.
 *
 * Supports both:
 * - User API keys (arb_*) validated against database
 * - Admin secret (AUTH_SECRET) for internal use
 */

import { NextRequest, NextResponse } from "next/server";
import { hashApiKey } from "@/lib/apiKeys";

export interface AuthResult {
  success: true;
  userId: string | null;
  keyId: string | null;
  isAdmin: boolean;
}

export interface AuthError {
  success: false;
  response: NextResponse;
}

/**
 * Validate a request using either user API key or admin secret.
 *
 * @param request - The incoming request
 * @param db - D1 database instance (optional, needed for user API keys)
 * @param authSecret - AUTH_SECRET env var (optional, for admin access)
 * @returns AuthResult if valid, AuthError if invalid
 */
export async function validateRequest(
  request: NextRequest,
  db?: D1Database,
  authSecret?: string
): Promise<AuthResult | AuthError> {
  const authHeader = request.headers.get("Authorization");

  if (!authHeader?.startsWith("Bearer ")) {
    return {
      success: false,
      response: NextResponse.json(
        { error: "Unauthorized - Missing or invalid Authorization header" },
        { status: 401 }
      ),
    };
  }

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

      return {
        success: true,
        userId: result.userId,
        keyId: result.id,
        isAdmin: false,
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

  // Neither valid user key nor admin secret
  return {
    success: false,
    response: NextResponse.json(
      { error: "Unauthorized - Invalid credentials" },
      { status: 401 }
    ),
  };
}
