import { NextRequest, NextResponse } from "next/server";
import { generateOrbitConfig } from "@/lib/tools/generateOrbitConfig";
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
      prompt?: string;
      chainId?: number;
      owner?: string;
      isAnyTrust?: boolean;
      nativeToken?: string;
      parentChain?: string;
    };

    if (!body.prompt) {
      return NextResponse.json(
        { error: "Missing required field: prompt" },
        { status: 400 }
      );
    }

    const result = generateOrbitConfig({
      prompt: body.prompt,
      chainId: body.chainId,
      owner: body.owner,
      isAnyTrust: body.isAnyTrust,
      nativeToken: body.nativeToken,
      parentChain: body.parentChain as Parameters<typeof generateOrbitConfig>[0]["parentChain"],
    });

    return NextResponse.json(result, { headers: { ...rl.headers, ...cors.headers } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateOrbitConfig:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}

export async function OPTIONS(request: NextRequest) {
  return preflightResponse(request, "POST, OPTIONS");
}
