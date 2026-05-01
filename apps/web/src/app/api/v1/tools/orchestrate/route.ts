import { NextRequest, NextResponse } from "next/server";
import { orchestrateDapp } from "@/lib/tools/orchestrateDapp";
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
      prompt?: string;
      components?: string[];
      network?: string;
      contractAddress?: string;
      contractAbi?: string;
    };

    if (!body.prompt) {
      return NextResponse.json(
        { error: "Missing required field: prompt" },
        { status: 400 }
      );
    }

    const result = orchestrateDapp({
      prompt: body.prompt,
      components: body.components as Parameters<typeof orchestrateDapp>[0]["components"],
      network: body.network as "arbitrum-sepolia" | "arbitrum-one" | undefined,
      contractAddress: body.contractAddress,
      contractAbi: body.contractAbi,
    });

    return NextResponse.json(result, { headers: rl.headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in orchestrateDapp:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}
