/**
 * Validate AUTH_SECRET for internal API routes.
 */

import { NextRequest, NextResponse } from "next/server";

export function validateAdminSecret(
  request: NextRequest,
  authSecret: string | undefined
): NextResponse | null {
  const authHeader = request.headers.get("Authorization");

  if (!authHeader?.startsWith("Bearer ")) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  const token = authHeader.slice(7);

  if (!authSecret || token !== authSecret) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  return null; // Auth passed
}
