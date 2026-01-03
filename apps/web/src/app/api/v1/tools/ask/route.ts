import { NextRequest, NextResponse } from "next/server";
import { askStylus, type AskStylusInput } from "@/lib/tools/askStylus";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";


export async function POST(request: NextRequest) {
  try {
    // Get Cloudflare bindings
    const { env } = getCloudflareContext();

    // Validate request (supports both user API keys and admin secret)
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

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

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error in askStylus:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
