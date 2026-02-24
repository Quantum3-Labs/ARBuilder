import { NextRequest, NextResponse } from "next/server";
import { askBridging, type AskBridgingInput } from "@/lib/tools/askBridging";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

    if (!env.OPENROUTER_API_KEY) {
      return NextResponse.json(
        { error: "OpenRouter API key not configured" },
        { status: 500 }
      );
    }

    const body = (await request.json()) as AskBridgingInput;

    if (!body.question) {
      return NextResponse.json(
        { error: "Missing required field: question" },
        { status: 400 }
      );
    }

    const result = await askBridging(
      env.VECTORIZE,
      env.AI,
      env.OPENROUTER_API_KEY,
      {
        question: body.question,
        includeCodeExample: body.includeCodeExample,
        questionType: body.questionType,
      }
    );

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in askBridging:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}
