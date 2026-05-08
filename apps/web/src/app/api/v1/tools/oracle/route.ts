import { NextRequest, NextResponse } from "next/server";
import { generateOracle } from "@/lib/tools/generateOracle";
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
      oracleType?: string;
      network?: string;
      feeds?: string[];
    };

    if (!body.oracleType) {
      return NextResponse.json(
        { error: "Missing required field: oracleType" },
        { status: 400 }
      );
    }

    const result = generateOracle({
      oracleType: body.oracleType as Parameters<typeof generateOracle>[0]["oracleType"],
      network: body.network as "arbitrum-one" | "arbitrum-sepolia" | undefined,
      feeds: body.feeds,
    });

    return NextResponse.json(result, { headers: { ...rl.headers, ...cors.headers } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateOracle:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}

export async function OPTIONS(request: NextRequest) {
  return preflightResponse(request, "POST, OPTIONS");
}
