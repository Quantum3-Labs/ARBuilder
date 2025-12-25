import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { refreshTokens } from "@/lib/jwt";

export async function POST(request: NextRequest) {
  try {
    // Get refresh token from cookie
    const refreshToken = request.cookies.get("refresh-token")?.value;

    if (!refreshToken) {
      return NextResponse.json(
        { error: "No refresh token provided" },
        { status: 401 }
      );
    }

    const { env } = getCloudflareContext();

    // Refresh the tokens
    const tokens = await refreshTokens(env.DB, refreshToken);

    if (!tokens) {
      // Clear cookies on invalid refresh token
      const response = NextResponse.json(
        { error: "Invalid or expired refresh token" },
        { status: 401 }
      );
      response.cookies.set("auth-token", "", { maxAge: 0, path: "/" });
      response.cookies.set("refresh-token", "", { maxAge: 0, path: "/" });
      return response;
    }

    // Set new cookies
    const response = NextResponse.json({ success: true });

    response.cookies.set("auth-token", tokens.accessToken, {
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: 15 * 60, // 15 minutes
    });

    response.cookies.set("refresh-token", tokens.refreshToken, {
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: 7 * 24 * 60 * 60, // 7 days
    });

    return response;
  } catch (error) {
    console.error("Token refresh error:", error);
    return NextResponse.json(
      { error: "An error occurred" },
      { status: 500 }
    );
  }
}
