import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { verifyOTP } from "@/lib/otp";
import { createTokenPair } from "@/lib/jwt";

/**
 * Generate random hex string
 */
function randomHex(bytes: number): string {
  const array = new Uint8Array(bytes);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

export async function POST(request: NextRequest) {
  try {
    const { email, code } = (await request.json()) as {
      email?: string;
      code?: string;
    };

    // Validate input
    if (!email || !code) {
      return NextResponse.json(
        { error: "Email and verification code are required" },
        { status: 400 }
      );
    }

    // Validate code format (6 digits)
    if (!/^\d{6}$/.test(code)) {
      return NextResponse.json(
        { error: "Invalid verification code format" },
        { status: 400 }
      );
    }

    const { env } = getCloudflareContext();

    // Verify OTP
    const isValid = await verifyOTP(env.DB, email, code);

    if (!isValid) {
      return NextResponse.json(
        { error: "Invalid or expired verification code" },
        { status: 400 }
      );
    }

    // Get or create user
    let user = await env.DB
      .prepare(`SELECT id, email, name FROM users WHERE email = ?`)
      .bind(email.toLowerCase())
      .first<{ id: string; email: string; name: string | null }>();

    if (!user) {
      // Create new user
      const userId = randomHex(16);
      const now = new Date().toISOString();

      await env.DB
        .prepare(
          `INSERT INTO users (id, email, emailVerified, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)`
        )
        .bind(userId, email.toLowerCase(), now, now, now)
        .run();

      user = { id: userId, email: email.toLowerCase(), name: null };
    }

    // Generate token pair
    const tokens = await createTokenPair(env.DB, {
      sub: user.id,
      email: user.email,
    });

    // Create response with cookies
    const response = NextResponse.json({
      success: true,
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
      },
    });

    // Set access token cookie (15 minutes)
    response.cookies.set("auth-token", tokens.accessToken, {
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: 15 * 60,
    });

    // Set refresh token cookie (7 days)
    response.cookies.set("refresh-token", tokens.refreshToken, {
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
      maxAge: 7 * 24 * 60 * 60,
    });

    return response;
  } catch (error) {
    console.error("Verify OTP error:", error);
    return NextResponse.json(
      { error: "An error occurred" },
      { status: 500 }
    );
  }
}
