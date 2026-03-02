import { NextRequest, NextResponse } from "next/server";
import { generateValidatorSetup } from "@/lib/tools/generateValidatorSetup";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { validateRequest } from "@/lib/auth/validateRequest";

export async function POST(request: NextRequest) {
  try {
    const { env } = getCloudflareContext();
    const auth = await validateRequest(request, env.DB, env.AUTH_SECRET);
    if (!auth.success) return auth.response;

    const body = (await request.json()) as {
      prompt?: string;
      action?: string;
      target?: string;
      addresses?: string[];
      rollupAddress?: string;
      sequencerInbox?: string;
      parentChain?: string;
    };

    if (!body.prompt) {
      return NextResponse.json(
        { error: "Missing required field: prompt" },
        { status: 400 }
      );
    }

    const result = generateValidatorSetup({
      prompt: body.prompt,
      action: body.action as Parameters<typeof generateValidatorSetup>[0]["action"],
      target: body.target as Parameters<typeof generateValidatorSetup>[0]["target"],
      addresses: body.addresses,
      rollupAddress: body.rollupAddress,
      sequencerInbox: body.sequencerInbox,
      parentChain: body.parentChain as Parameters<typeof generateValidatorSetup>[0]["parentChain"],
    });

    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("Error in generateValidatorSetup:", message, error);
    return NextResponse.json(
      { error: `Tool error: ${message}` },
      { status: 500 }
    );
  }
}
