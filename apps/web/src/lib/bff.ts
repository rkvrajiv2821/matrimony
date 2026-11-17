import "server-only";

import { NextResponse, type NextRequest } from "next/server";

/**
 * CSRF defence for cookie-authenticated mutations: the request must come from our own origin.
 * (SameSite=Lax cookies already block most cross-site POSTs; this closes the remaining gaps.)
 */
export function sameOrigin(req: NextRequest): boolean {
  const origin = req.headers.get("origin");
  if (!origin) return false;
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

export function forbiddenOrigin(): NextResponse {
  return NextResponse.json(
    { error: { code: "bad_origin", message: "Cross-origin request refused.", details: null } },
    { status: 403 },
  );
}

/** Relay an API response (status + JSON body) to the browser. */
export async function relay(res: Response): Promise<NextResponse> {
  if (res.status === 204) return new NextResponse(null, { status: 204 });
  const body = await res.text();
  const out = new NextResponse(body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
  const retry = res.headers.get("retry-after");
  if (retry) out.headers.set("retry-after", retry);
  return out;
}
