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

const RELAYED_HEADERS = ["content-type", "retry-after", "cache-control", "content-disposition"];

/** Relay an API response to the browser byte-for-byte (JSON or binary, e.g. photos). */
export async function relay(res: Response): Promise<NextResponse> {
  if (res.status === 204) return new NextResponse(null, { status: 204 });
  const out = new NextResponse(res.body, { status: res.status });
  for (const name of RELAYED_HEADERS) {
    const value = res.headers.get(name);
    if (value) out.headers.set(name, value);
  }
  if (!out.headers.has("content-type")) out.headers.set("content-type", "application/json");
  return out;
}
