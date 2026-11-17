import { callApi, forwardedFor } from "@/lib/api-server";
import { forbiddenOrigin, relay, sameOrigin } from "@/lib/bff";
import { setSessionCookies, type TokenPair } from "@/lib/session";
import { NextResponse, type NextRequest } from "next/server";

interface AuthResult extends TokenPair {
  is_new_user: boolean;
  user: { preferred_language: string };
}

export async function POST(req: NextRequest) {
  if (!sameOrigin(req)) return forbiddenOrigin();
  const res = await callApi("/auth/otp/verify", {
    method: "POST",
    body: await req.text(),
    clientIp: forwardedFor(req.headers),
    headers: { "user-agent": req.headers.get("user-agent") ?? "" },
  });
  if (!res.ok) return relay(res);

  const result = (await res.json()) as AuthResult;
  // Tokens go into httpOnly cookies only; the browser receives non-sensitive fields.
  const out = NextResponse.json({
    is_new_user: result.is_new_user,
    preferred_language: result.user.preferred_language,
  });
  setSessionCookies(out, result);
  return out;
}
