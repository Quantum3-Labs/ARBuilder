import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { verifyJWT, revokeAllRefreshTokens } from "@/lib/jwt";

export async function POST(request: NextRequest) {
  const response = NextResponse.json({ success: true });

  // Try to revoke refresh tokens for the user
  try {
    const accessToken = request.cookies.get("auth-token")?.value;
    if (accessToken) {
      const { env } = getCloudflareContext();
      const payload = await verifyJWT(env.DB, accessToken);
      if (payload) {
        await revokeAllRefreshTokens(env.DB, payload.sub);
      }
    }
  } catch {
    // Ignore errors during logout
  }

  // Clear both cookies
  response.cookies.set("auth-token", "", {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });

  response.cookies.set("refresh-token", "", {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });

  return response;
}
