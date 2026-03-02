import { NextRequest, NextResponse } from "next/server";
import { generateOrbitConfig } from "@/lib/tools/generateOrbitConfig";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

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

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateOrbitConfig:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}
