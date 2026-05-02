import { NextRequest, NextResponse } from "next/server";
import { generateFrontend } from "@/lib/tools/generateFrontend";
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
      contractAbi?: string;
      uiFramework?: string;
      template?: string;
    };

    if (!body.prompt) {
      return NextResponse.json(
        { error: "Missing required field: prompt" },
        { status: 400 }
      );
    }

    const result = generateFrontend({
      prompt: body.prompt,
      contractAbi: body.contractAbi,
      uiFramework: body.uiFramework as "daisyui" | "shadcn" | "none" | undefined,
      template: body.template as "base" | "dashboard" | "token" | undefined,
    });

    return NextResponse.json(result, { headers: rl.headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateFrontend:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}
