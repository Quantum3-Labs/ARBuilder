/**
 * OTP utilities for email verification.
 * Generates 6-digit codes, stores in D1, and sends via Resend.
 */

const OTP_EXPIRY_MINUTES = 10;
const OTP_LENGTH = 6;
const MAX_ATTEMPTS_PER_EMAIL = 5; // Per hour

/**
 * Generate random hex string
 */
function randomHex(bytes: number): string {
  const array = new Uint8Array(bytes);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Generate a cryptographically secure 6-digit OTP code.
 */
export function generateOTPCode(): string {
  const array = new Uint32Array(1);
  crypto.getRandomValues(array);
  // Generate a number between 0 and 999999, then pad to 6 digits
  const code = (array[0] % 1000000).toString().padStart(OTP_LENGTH, "0");
  return code;
}

/**
 * Hash an OTP code for storage.
 */
async function hashOTP(code: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(code);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Check rate limiting for OTP requests.
 */
export async function checkRateLimit(
  db: D1Database,
  email: string
): Promise<boolean> {
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();

  const result = await db
    .prepare(
      `SELECT COUNT(*) as count FROM otp_codes
       WHERE email = ? AND created_at > ?`
    )
    .bind(email.toLowerCase(), oneHourAgo)
    .first<{ count: number }>();

  return (result?.count ?? 0) < MAX_ATTEMPTS_PER_EMAIL;
}

/**
 * Create and store an OTP code.
 */
export async function createOTP(
  db: D1Database,
  email: string
): Promise<{ code: string; expiresAt: Date } | null> {
  // Check rate limit
  const allowed = await checkRateLimit(db, email);
  if (!allowed) {
    return null;
  }

  const code = generateOTPCode();
  const codeHash = await hashOTP(code);
  const id = randomHex(16);
  const now = new Date();
  const expiresAt = new Date(now.getTime() + OTP_EXPIRY_MINUTES * 60 * 1000);

  // Invalidate any existing unused codes for this email
  await db
    .prepare(
      `UPDATE otp_codes SET used_at = datetime('now')
       WHERE email = ? AND used_at IS NULL`
    )
    .bind(email.toLowerCase())
    .run();

  // Insert new code
  await db
    .prepare(
      `INSERT INTO otp_codes (id, email, code, expires_at, created_at)
       VALUES (?, ?, ?, ?, ?)`
    )
    .bind(
      id,
      email.toLowerCase(),
      codeHash,
      expiresAt.toISOString(),
      now.toISOString()
    )
    .run();

  return { code, expiresAt };
}

/**
 * Verify an OTP code.
 */
export async function verifyOTP(
  db: D1Database,
  email: string,
  code: string
): Promise<boolean> {
  const codeHash = await hashOTP(code);
  const now = new Date().toISOString();

  // Find valid OTP
  const otp = await db
    .prepare(
      `SELECT id FROM otp_codes
       WHERE email = ? AND code = ? AND used_at IS NULL AND expires_at > ?
       ORDER BY created_at DESC
       LIMIT 1`
    )
    .bind(email.toLowerCase(), codeHash, now)
    .first<{ id: string }>();

  if (!otp) {
    return false;
  }

  // Mark as used
  await db
    .prepare(`UPDATE otp_codes SET used_at = ? WHERE id = ?`)
    .bind(now, otp.id)
    .run();

  return true;
}

/**
 * Send OTP email via Resend.
 */
export async function sendOTPEmail(
  resendApiKey: string,
  email: string,
  code: string
): Promise<boolean> {
  try {
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${resendApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: "ARBuilder <noreply@whymelabs.com>",
        to: [email],
        subject: `Your ARBuilder verification code: ${code}`,
        html: `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f9fafb; padding: 40px 20px; margin: 0;">
  <div style="max-width: 400px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
    <div style="text-align: center; margin-bottom: 32px;">
      <div style="display: inline-block; background: linear-gradient(135deg, #2563eb, #4f46e5); width: 48px; height: 48px; border-radius: 12px; line-height: 48px; color: white; font-weight: bold; font-size: 18px;">AR</div>
      <h1 style="margin: 16px 0 0; font-size: 24px; color: #111827;">ARBuilder</h1>
    </div>

    <p style="color: #4b5563; font-size: 16px; line-height: 1.5; margin-bottom: 24px; text-align: center;">
      Enter this verification code to sign in:
    </p>

    <div style="background: #f3f4f6; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px;">
      <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #111827; font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;">${code}</span>
    </div>

    <p style="color: #6b7280; font-size: 14px; text-align: center; margin-bottom: 8px;">
      This code expires in 10 minutes.
    </p>

    <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 32px;">
      If you didn't request this code, you can safely ignore this email.
    </p>
  </div>
</body>
</html>
        `,
        text: `Your ARBuilder verification code is: ${code}\n\nThis code expires in 10 minutes.\n\nIf you didn't request this code, you can safely ignore this email.`,
      }),
    });

    return response.ok;
  } catch (error) {
    console.error("Failed to send OTP email:", error);
    return false;
  }
}

/**
 * Clean up expired OTP codes (can be called periodically).
 */
export async function cleanupExpiredOTPs(db: D1Database): Promise<number> {
  const result = await db
    .prepare(
      `DELETE FROM otp_codes
       WHERE expires_at < datetime('now', '-1 hour')`
    )
    .run();

  return result.meta.changes;
}
