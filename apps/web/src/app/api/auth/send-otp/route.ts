import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { createOTP, sendOTPEmail } from "@/lib/otp";

export async function POST(request: NextRequest) {
  try {
    const { token, email } = (await request.json()) as {
      token?: string;
      email?: string;
    };

    // Validate email
    if (!email || !email.includes("@")) {
      return NextResponse.json(
        { error: "Valid email is required" },
        { status: 400 }
      );
    }

    // Validate turnstile token
    if (!token) {
      return NextResponse.json(
        { error: "Captcha verification required" },
        { status: 400 }
      );
    }

    const { env } = getCloudflareContext();

    // Verify turnstile token
    const formData = new FormData();
    formData.append("secret", env.TURNSTILE_SECRET_KEY);
    formData.append("response", token);

    const verifyResponse = await fetch(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      {
        method: "POST",
        body: formData,
      }
    );

    const turnstileResult = (await verifyResponse.json()) as {
      success: boolean;
      "error-codes"?: string[];
    };

    if (!turnstileResult.success) {
      return NextResponse.json(
        {
          error: "Captcha verification failed",
          codes: turnstileResult["error-codes"],
        },
        { status: 400 }
      );
    }

    // Create OTP
    const otpResult = await createOTP(env.DB, email);

    if (!otpResult) {
      return NextResponse.json(
        { error: "Too many requests. Please try again later." },
        { status: 429 }
      );
    }

    // Send OTP email
    const emailSent = await sendOTPEmail(
      env.RESEND_API_KEY,
      email,
      otpResult.code
    );

    if (!emailSent) {
      return NextResponse.json(
        { error: "Failed to send verification email" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "Verification code sent",
      expiresAt: otpResult.expiresAt.toISOString(),
    });
  } catch (error) {
    console.error("Send OTP error:", error);
    return NextResponse.json(
      { error: "An error occurred" },
      { status: 500 }
    );
  }
}
