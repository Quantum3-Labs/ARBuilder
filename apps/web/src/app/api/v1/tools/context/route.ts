import { NextRequest, NextResponse } from "next/server";
import { getStylusContext, type GetStylusContextInput } from "@/lib/tools/getStylusContext";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateAdminSecret } from "@/lib/auth/validateAdminSecret";


export async function POST(request: NextRequest) {
  try {
    // Get Cloudflare bindings
    const { env } = getCloudflareContext();

    // Validate admin secret
    const authError = validateAdminSecret(request, env.AUTH_SECRET);
    if (authError) return authError;

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
