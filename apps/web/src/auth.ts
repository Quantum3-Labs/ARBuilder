/**
 * Custom JWT-based authentication using ECDSA signing.
 * Replaces Auth.js for better control and reliability.
 */

import { cookies } from "next/headers";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { verifyJWT } from "@/lib/jwt";

export interface Session {
  user: {
    id: string;
    email: string;
    name?: string | null;
  };
}

/**
 * Get the current session from the JWT cookie (server-side).
 * Note: For client-side session checks, use /api/auth/session
 * which handles token refresh automatically.
 */
export async function auth(): Promise<Session | null> {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("auth-token")?.value;

    if (!token) {
      return null;
    }

    const { env } = getCloudflareContext();
    const payload = await verifyJWT(env.DB, token);

    if (!payload || payload.type !== "access") {
      return null;
    }

    // Get user from database
    const user = await env.DB
      .prepare(`SELECT id, email, name FROM users WHERE id = ?`)
      .bind(payload.sub)
      .first<{ id: string; email: string; name: string | null }>();

    if (!user) {
      return null;
    }

    return {
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
      },
    };
  } catch {
    return null;
  }
}

/**
 * Sign out by clearing auth cookies.
 */
export async function signOut(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete("auth-token");
  cookieStore.delete("refresh-token");
}
