import { NextRequest, NextResponse } from "next/server";
import { orchestrateDapp } from "@/lib/tools/orchestrateDapp";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

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

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error in orchestrateDapp:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
