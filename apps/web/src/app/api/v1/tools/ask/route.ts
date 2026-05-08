import { NextRequest, NextResponse } from "next/server";
import { askStylus, type AskStylusInput } from "@/lib/tools/askStylus";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";
import { checkToolRateLimit } from "@/lib/rateLimit";
import { evaluateCors, preflightResponse } from "@/lib/cors";


export async function POST(request: NextRequest) {
  try {
    // Get Cloudflare bindings
    const { env } = getCloudflareContext();

    // Validate request (supports both user API keys and admin secret)
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;
    const rl = await checkToolRateLimit(env.KV, auth);
    if ("response" in rl) return rl.response;
    const cors = evaluateCors(request, auth.allowedOrigins);
    if (!cors.ok) return cors.response;

    // Check for OpenRouter API key
    if (!env.OPENROUTER_API_KEY) {
      return NextResponse.json(
        { error: "OpenRouter API key not configured" },
        { status: 500 }
      );
    }

    // Parse request body
    const body = (await request.json()) as AskStylusInput;

    if (!body.question) {
      return NextResponse.json(
        { error: "Missing required field: question" },
        { status: 400 }
      );
    }

    // Call tool
    const result = await askStylus(
      env.VECTORIZE,
      env.AI,
      env.OPENROUTER_API_KEY,
      {
        question: body.question,
        codeContext: body.codeContext,
        questionType: body.questionType ?? "general",
      }
    );

    return NextResponse.json(result, { headers: { ...rl.headers, ...cors.headers } });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in askStylus:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}

export async function OPTIONS(request: NextRequest) {
  return preflightResponse(request, "POST, OPTIONS");
}
