/**
 * Photo upload relay: browser -> Next.js -> presigned POST to private storage -> API confirm.
 * Storage is never exposed to the browser (private network only), so CSP stays 'self'.
 */
import { callApi, forwardedFor } from "@/lib/api-server";
import { forbiddenOrigin, relay, sameOrigin } from "@/lib/bff";
import { ACCESS_COOKIE } from "@/lib/session";
import { NextResponse, type NextRequest } from "next/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const VISIBILITY = new Set(["members", "connections", "hidden"]);

function fail(code: string, status = 422) {
  return NextResponse.json({ error: { code, message: code, details: null } }, { status });
}

export async function POST(req: NextRequest) {
  if (!sameOrigin(req)) return forbiddenOrigin();
  const token = req.cookies.get(ACCESS_COOKIE)?.value;
  if (!token) return fail("not_authenticated", 401);

  const profileId = req.nextUrl.searchParams.get("profile") ?? "";
  if (!UUID.test(profileId)) return fail("not_found", 404);

  const form = await req.formData().catch(() => null);
  const file = form?.get("file");
  if (!(file instanceof Blob) || file.size === 0) return fail("invalid_image");
  const visibilityRaw = String(form?.get("visibility") ?? "members");
  const visibility = VISIBILITY.has(visibilityRaw) ? visibilityRaw : "members";
  const clientIp = forwardedFor(req.headers);

  const presign = await callApi(`/profiles/${profileId}/photos/upload-url`, {
    method: "POST",
    token,
    clientIp,
    body: JSON.stringify({ content_type: file.type, size_bytes: file.size }),
  });
  if (!presign.ok) return relay(presign);
  const up = (await presign.json()) as {
    upload_id: string;
    url: string;
    fields: Record<string, string>;
  };

  const s3Form = new FormData();
  for (const [k, v] of Object.entries(up.fields)) s3Form.append(k, v);
  s3Form.append("file", file, "photo");
  const stored = await fetch(up.url, { method: "POST", body: s3Form });
  if (!stored.ok) return fail(stored.status === 400 ? "image_too_large" : "upload_missing");

  const confirmed = await callApi(`/profiles/${profileId}/photos`, {
    method: "POST",
    token,
    clientIp,
    body: JSON.stringify({ upload_id: up.upload_id, visibility }),
  });
  return relay(confirmed);
}
