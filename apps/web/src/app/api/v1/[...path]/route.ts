/**
 * Authenticated pass-through for browser calls: /api/v1/<path> -> FastAPI /api/v1/<path>,
 * with the bearer token taken from the httpOnly cookie.
 *
 * Auth endpoints are excluded: they must go through /api/auth/* so tokens never reach JS.
 */
import { callApi, forwardedFor } from "@/lib/api-server";
import { forbiddenOrigin, relay, sameOrigin } from "@/lib/bff";
import { ACCESS_COOKIE } from "@/lib/session";
import { NextResponse, type NextRequest } from "next/server";

type Ctx = { params: Promise<{ path: string[] }> };

const BLOCKED_PREFIXES = ["auth/register", "auth/otp", "auth/refresh", "admin"];

async function handle(req: NextRequest, { params }: Ctx): Promise<NextResponse> {
  const { path } = await params;
  if (path.some((seg) => seg === "." || seg === ".." || seg === "")) {
    return NextResponse.json(
      { error: { code: "not_found", message: "Not found.", details: null } },
      { status: 404 },
    );
  }
  const joined = path.map(encodeURIComponent).join("/");
  if (BLOCKED_PREFIXES.some((p) => joined === p || joined.startsWith(`${p}/`))) {
    return NextResponse.json(
      { error: { code: "not_found", message: "Not found.", details: null } },
      { status: 404 },
    );
  }
  if (req.method !== "GET" && !sameOrigin(req)) return forbiddenOrigin();

  const token = req.cookies.get(ACCESS_COOKIE)?.value;
  if (!token) {
    return NextResponse.json(
      { error: { code: "not_authenticated", message: "Please log in.", details: null } },
      { status: 401 },
    );
  }
  const res = await callApi(`/${joined}${req.nextUrl.search}`, {
    method: req.method,
    body: ["GET", "HEAD"].includes(req.method) ? undefined : await req.text(),
    token,
    clientIp: forwardedFor(req.headers),
  });
  return relay(res);
}

export { handle as DELETE, handle as GET, handle as PATCH, handle as POST, handle as PUT };
