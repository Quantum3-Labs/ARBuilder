import { NextRequest, NextResponse } from "next/server";
import { generateBridgeCode } from "@/lib/tools/generateBridgeCode";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";
import { checkToolRateLimit } from "@/lib/rateLimit";

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;
    const rl = await checkToolRateLimit(env.KV, auth);
    if ("response" in rl) return rl.response;

    const body = (await request.json()) as {
      bridgeType?: string;
      amount?: string;
      tokenAddress?: string;
      destinationAddress?: string;
    };

    if (!body.bridgeType) {
      return NextResponse.json(
        { error: "Missing required field: bridgeType" },
        { status: 400 }
      );
    }

    const result = generateBridgeCode({
      bridgeType: body.bridgeType as Parameters<typeof generateBridgeCode>[0]["bridgeType"],
      amount: body.amount,
      tokenAddress: body.tokenAddress,
      destinationAddress: body.destinationAddress,
    });

    return NextResponse.json(result, { headers: rl.headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateBridgeCode:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}
