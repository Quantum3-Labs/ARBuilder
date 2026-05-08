import { NextRequest, NextResponse } from "next/server";
import { generateMessagingCode } from "@/lib/tools/generateMessagingCode";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";
import { checkToolRateLimit } from "@/lib/rateLimit";
import { evaluateCors, preflightResponse } from "@/lib/cors";

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;
    const rl = await checkToolRateLimit(env.KV, auth);
    if ("response" in rl) return rl.response;
    const cors = evaluateCors(request, auth.allowedOrigins);
    if (!cors.ok) return cors.response;

    const body = (await request.json()) as {
      messageType?: string;
      includeExample?: boolean;
    };

    if (!body.messageType) {
      return NextResponse.json(
        { error: "Missing required field: messageType" },
        { status: 400 }
      );
    }

    const result = generateMessagingCode({
      messageType: body.messageType as Parameters<typeof generateMessagingCode>[0]["messageType"],
      includeExample: body.includeExample,
    });

    return NextResponse.json(result, { headers: { ...rl.headers, ...cors.headers } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateMessagingCode:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}

export async function OPTIONS(request: NextRequest) {
  return preflightResponse(request, "POST, OPTIONS");
}
