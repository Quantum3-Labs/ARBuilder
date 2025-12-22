import { NextRequest, NextResponse } from "next/server";
import { generateStylusCode, type GenerateStylusCodeInput } from "@/lib/tools/generateStylusCode";
import { getCloudflareContext } from "@opennextjs/cloudflare";

export const runtime = "edge";

export async function POST(request: NextRequest) {
  try {
    // Get Cloudflare bindings
    const { env } = getCloudflareContext();

    // Check for OpenRouter API key
    if (!env.OPENROUTER_API_KEY) {
      return NextResponse.json(
        { error: "OpenRouter API key not configured" },
        { status: 500 }
      );
    }

    // Parse request body
    const body = (await request.json()) as GenerateStylusCodeInput;

    if (!body.prompt) {
      return NextResponse.json(
        { error: "Missing required field: prompt" },
        { status: 400 }
      );
    }

    // Call tool
    const result = await generateStylusCode(
      env.VECTORIZE,
      env.AI,
      env.OPENROUTER_API_KEY,
      {
        prompt: body.prompt,
        contextQuery: body.contextQuery,
        contractType: body.contractType ?? "utility",
        includeTests: body.includeTests ?? false,
        temperature: body.temperature ?? 0.2,
      }
    );

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error in generateStylusCode:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
