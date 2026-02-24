import { NextRequest, NextResponse } from "next/server";
import { generateBackend } from "@/lib/tools/generateBackend";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

    const body = (await request.json()) as {
      prompt?: string;
      framework?: string;
      contractAbi?: string;
      features?: string[];
    };

    if (!body.prompt) {
      return NextResponse.json(
        { error: "Missing required field: prompt" },
        { status: 400 }
      );
    }

    const result = generateBackend({
      prompt: body.prompt,
      framework: body.framework as "nestjs" | "express" | undefined,
      contractAbi: body.contractAbi,
      features: body.features,
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error in generateBackend:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
