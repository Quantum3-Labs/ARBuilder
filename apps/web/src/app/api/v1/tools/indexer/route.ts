import { NextRequest, NextResponse } from "next/server";
import { generateIndexer } from "@/lib/tools/generateIndexer";
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
      contractAddress?: string;
      subgraphType?: string;
      abi?: string;
      events?: string[];
      network?: string;
    };

    if (!body.contractAddress) {
      return NextResponse.json(
        { error: "Missing required field: contractAddress" },
        { status: 400 }
      );
    }

    const result = generateIndexer({
      contractAddress: body.contractAddress,
      subgraphType: body.subgraphType as "erc20" | "erc721" | "defi" | "custom" | undefined,
      abi: body.abi,
      events: body.events,
      network: body.network,
    });

    return NextResponse.json(result, { headers: rl.headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateIndexer:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}
