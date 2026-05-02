import { NextRequest, NextResponse } from "next/server";
import { generateOrbitDeployment } from "@/lib/tools/generateOrbitDeployment";
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
      deploymentType?: string;
      validators?: string[];
      batchPosters?: string[];
      nativeToken?: string;
      parentChain?: string;
      rollupVersion?: string;
      chainId?: number;
      isAnyTrust?: boolean;
      rollupAddress?: string;
    };

    if (!body.prompt) {
      return NextResponse.json(
        { error: "Missing required field: prompt" },
        { status: 400 }
      );
    }

    const result = generateOrbitDeployment({
      prompt: body.prompt,
      deploymentType: body.deploymentType as Parameters<typeof generateOrbitDeployment>[0]["deploymentType"],
      validators: body.validators,
      batchPosters: body.batchPosters,
      nativeToken: body.nativeToken,
      parentChain: body.parentChain as Parameters<typeof generateOrbitDeployment>[0]["parentChain"],
      rollupVersion: body.rollupVersion as Parameters<typeof generateOrbitDeployment>[0]["rollupVersion"],
      chainId: body.chainId,
      isAnyTrust: body.isAnyTrust,
      rollupAddress: body.rollupAddress,
    });

    return NextResponse.json(result, { headers: rl.headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateOrbitDeployment:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}
