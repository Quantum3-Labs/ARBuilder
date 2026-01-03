import { NextRequest, NextResponse } from "next/server";
import { getStylusContext, type GetStylusContextInput } from "@/lib/tools/getStylusContext";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";


export async function POST(request: NextRequest) {
  try {
    // Get Cloudflare bindings
    const { env } = getCloudflareContext();

    // Validate request (supports both user API keys and admin secret)
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

    // Parse request body
    const body = (await request.json()) as GetStylusContextInput;

    if (!body.query) {
      return NextResponse.json(
        { error: "Missing required field: query" },
        { status: 400 }
      );
    }

    // Call tool
    const result = await getStylusContext(env.VECTORIZE, env.AI, {
      query: body.query,
      nResults: body.nResults ?? 5,
      contentType: body.contentType ?? "all",
      rerank: body.rerank ?? true,
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error in getStylusContext:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
