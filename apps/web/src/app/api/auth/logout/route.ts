import { callApi, forwardedFor } from "@/lib/api-server";
import { forbiddenOrigin, sameOrigin } from "@/lib/bff";
import { ACCESS_COOKIE, clearSessionCookies } from "@/lib/session";
import { NextResponse, type NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  if (!sameOrigin(req)) return forbiddenOrigin();
  const token = req.cookies.get(ACCESS_COOKIE)?.value;
  if (token) {
    // Best effort: cookies are cleared even if the API is unreachable.
    await callApi("/auth/logout", {
      method: "POST",
      body: await req.text(),
      token,
      clientIp: forwardedFor(req.headers),
    }).catch(() => undefined);
  }
  const out = new NextResponse(null, { status: 204 });
  clearSessionCookies(out);
  return out;
}
