import { NextRequest, NextResponse } from "next/server";
import { getWorkflow, type GetWorkflowInput } from "@/lib/tools/getWorkflow";
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
    const body = (await request.json()) as GetWorkflowInput;

    if (!body.workflowType) {
      return NextResponse.json(
        { error: "Missing required field: workflowType" },
        { status: 400 }
      );
    }

    if (!["build", "deploy", "test"].includes(body.workflowType)) {
      return NextResponse.json(
        { error: "Invalid workflowType. Must be: build, deploy, or test" },
        { status: 400 }
      );
    }

    // Call tool
    const result = getWorkflow({
      workflowType: body.workflowType,
      network: body.network ?? "arbitrum_sepolia",
      includeTroubleshooting: body.includeTroubleshooting ?? true,
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error in getWorkflow:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
