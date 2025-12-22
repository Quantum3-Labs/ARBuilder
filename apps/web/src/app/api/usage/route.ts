import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { auth } from "@/auth";
import { getUsageStats } from "@/lib/apiKeys";

export const runtime = "edge";

// GET /api/usage - Get usage statistics
export async function GET(request: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const days = parseInt(searchParams.get("days") || "30", 10);

    const { env } = getCloudflareContext();
    const stats = await getUsageStats(env.DB, session.user.id, days);

    return NextResponse.json(stats);
  } catch (error) {
    console.error("Error getting usage stats:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
