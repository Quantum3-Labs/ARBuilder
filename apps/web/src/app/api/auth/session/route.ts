import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { verifyJWT, refreshTokens } from "@/lib/jwt";

export async function GET(request: NextRequest) {
  try {
    const accessToken = request.cookies.get("auth-token")?.value;
    const refreshToken = request.cookies.get("refresh-token")?.value;

    const { env } = getCloudflareContext();

    // Try to verify access token
    if (accessToken) {
      const payload = await verifyJWT(env.DB, accessToken);
      if (payload && payload.type === "access") {
        // Get user from database
        const user = await env.DB
          .prepare(`SELECT id, email, name FROM users WHERE id = ?`)
          .bind(payload.sub)
          .first<{ id: string; email: string; name: string | null }>();

        if (user) {
          return NextResponse.json({
            user: {
              id: user.id,
              email: user.email,
              name: user.name,
            },
          });
        }
      }
    }

    // Access token invalid/expired, try refresh token
    if (refreshToken) {
      const tokens = await refreshTokens(env.DB, refreshToken);

      if (tokens) {
        // Verify the new access token to get user info
        const payload = await verifyJWT(env.DB, tokens.accessToken);
        if (payload) {
          const user = await env.DB
            .prepare(`SELECT id, email, name FROM users WHERE id = ?`)
            .bind(payload.sub)
            .first<{ id: string; email: string; name: string | null }>();

          if (user) {
            const response = NextResponse.json({
              user: {
                id: user.id,
                email: user.email,
                name: user.name,
              },
              refreshed: true,
            });

            // Set new cookies
            response.cookies.set("auth-token", tokens.accessToken, {
              httpOnly: true,
              secure: true,
              sameSite: "lax",
              path: "/",
              maxAge: 15 * 60,
            });

            response.cookies.set("refresh-token", tokens.refreshToken, {
              httpOnly: true,
              secure: true,
              sameSite: "lax",
              path: "/",
              maxAge: 7 * 24 * 60 * 60,
            });

            return response;
          }
        }
      }
    }

    // No valid session
    return NextResponse.json({ user: null });
  } catch (error) {
    console.error("Session error:", error);
    return NextResponse.json({ user: null });
  }
}
