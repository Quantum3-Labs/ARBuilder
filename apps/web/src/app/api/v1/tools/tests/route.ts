import { NextRequest, NextResponse } from "next/server";
import { generateTests, type GenerateTestsInput } from "@/lib/tools/generateTests";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateAdminSecret } from "@/lib/auth/validateAdminSecret";


export async function POST(request: NextRequest) {
  try {
    // Get Cloudflare bindings
    const { env } = getCloudflareContext();

    // Validate admin secret
    const authError = validateAdminSecret(request, env.AUTH_SECRET);
    if (authError) return authError;

    // Check for OpenRouter API key
    if (!env.OPENROUTER_API_KEY) {
      return NextResponse.json(
        { error: "OpenRouter API key not configured" },
        { status: 500 }
      );
    }

    // Parse request body
    const body = (await request.json()) as GenerateTestsInput;

    if (!body.contractCode) {
      return NextResponse.json(
        { error: "Missing required field: contractCode" },
        { status: 400 }
      );
    }

    // Call tool
    const result = await generateTests(env.OPENROUTER_API_KEY, {
      contractCode: body.contractCode,
      testFramework: body.testFramework ?? "rust_native",
      testTypes: body.testTypes ?? ["unit"],
      coverageFocus: body.coverageFocus,
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error in generateTests:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
