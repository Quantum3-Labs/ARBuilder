import { NextRequest, NextResponse } from "next/server";
import { getCloudflareContext } from "@opennextjs/cloudflare";
import { auth } from "@/auth";
import { revokeApiKey } from "@/lib/apiKeys";
import { validateOriginList } from "@/lib/cors";


// DELETE /api/keys/[id] - Revoke an API key
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;
    const { env } = getCloudflareContext();

    const revoked = await revokeApiKey(env.DB, id, session.user.id);

    if (!revoked) {
      return NextResponse.json(
        { error: "API key not found or already revoked" },
        { status: 404 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error revoking API key:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/keys/[id] — owner can update mutable fields on their key.
 * Body: { name?: string | null, allowedOrigins?: string[] | null }
 *   - allowedOrigins:
 *       null   → unrestricted (server-to-server)
 *       []     → locked (no browser may use this key)
 *       [...]  → only listed origins may use this key from a browser
 *       ["*"]  → any browser origin
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const { id } = await params;
    const { env } = getCloudflareContext();

    const body = (await request.json().catch(() => ({}))) as {
      name?: string | null;
      allowedOrigins?: string[] | null;
    };

    const owns = await env.DB
      .prepare(`SELECT id FROM api_keys WHERE id = ? AND user_id = ? AND revoked_at IS NULL`)
      .bind(id, session.user.id)
      .first();
    if (!owns) {
      return NextResponse.json({ error: "API key not found" }, { status: 404 });
    }

    const updates: string[] = [];
    const values: unknown[] = [];
    if (body.name !== undefined) {
      updates.push("name = ?");
      values.push(body.name === null ? null : String(body.name).trim() || null);
    }
    if (body.allowedOrigins !== undefined) {
      let serialised: string | null;
      if (body.allowedOrigins === null) {
        serialised = null;
      } else {
        try {
          serialised = JSON.stringify(validateOriginList(body.allowedOrigins));
        } catch (e) {
          return NextResponse.json({ error: (e as Error).message }, { status: 400 });
        }
      }
      updates.push("allowed_origins = ?");
      values.push(serialised);
    }
    if (updates.length === 0) {
      return NextResponse.json({ error: "No fields to update" }, { status: 400 });
    }

    values.push(id);
    await env.DB
      .prepare(`UPDATE api_keys SET ${updates.join(", ")} WHERE id = ?`)
      .bind(...values)
      .run();

    return NextResponse.json({ ok: true });
  } catch (e) {
    console.error("PATCH /api/keys/[id] failed:", e);
    return NextResponse.json({ error: (e as Error).message || String(e) }, { status: 500 });
  }
}
