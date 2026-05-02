import { NextRequest, NextResponse } from "next/server";
import { generateStylusCode, type GenerateStylusCodeInput } from "@/lib/tools/generateStylusCode";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";
import { checkToolRateLimit } from "@/lib/rateLimit";


export async function POST(request: NextRequest) {
  try {
    // Get Cloudflare bindings
    const { env } = getCloudflareContext();

    // Validate request (supports both user API keys and admin secret)
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;
    const rl = await checkToolRateLimit(env.KV, auth);
    if ("response" in rl) return rl.response;

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

    return NextResponse.json(result, { headers: rl.headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateStylusCode:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}
