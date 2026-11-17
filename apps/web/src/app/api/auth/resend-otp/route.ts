import { callApi, forwardedFor } from "@/lib/api-server";
import { forbiddenOrigin, relay, sameOrigin } from "@/lib/bff";
import type { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  if (!sameOrigin(req)) return forbiddenOrigin();
  const res = await callApi("/auth/otp/resend", {
    method: "POST",
    body: await req.text(),
    clientIp: forwardedFor(req.headers),
  });
  return relay(res);
}
