import { NextRequest, NextResponse } from "next/server";
import { generateMessagingCode } from "@/lib/tools/generateMessagingCode";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

    const body = (await request.json()) as {
      messageType?: string;
      includeExample?: boolean;
    };

    if (!body.messageType) {
      return NextResponse.json(
        { error: "Missing required field: messageType" },
        { status: 400 }
      );
    }

    const result = generateMessagingCode({
      messageType: body.messageType as Parameters<typeof generateMessagingCode>[0]["messageType"],
      includeExample: body.includeExample,
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error in generateMessagingCode:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
