import createIntlMiddleware from "next-intl/middleware";
import { NextRequest, NextResponse } from "next/server";
import { localePrefixes } from "@vaibhav/localization";
import { routing } from "./i18n/routing";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  clearSessionCookies,
  setSessionCookies,
  type TokenPair,
} from "./lib/session";

const intl = createIntlMiddleware(routing);

/**
 * Locales whose public URL prefix differs from the locale code (e.g. /tanglish -> ta-Latn).
 * next-intl rewrites /tanglish/x to /ta-Latn/x; the standalone server runs the proxy again on
 * that internal path, which must pass through instead of being redirected as unprefixed.
 */
const INTERNAL_LOCALE_PATH = new RegExp(
  `^/(${routing.locales
    .filter((l) => localePrefixes[l] !== `/${l}`)
    .map((l) => l.replace(/[-]/g, "\\-"))
    .join("|")})(/|$)`,
);
const API_URL = process.env.VAIBHAV_API_INTERNAL_URL ?? "http://127.0.0.1:8000";

type RefreshOutcome =
  | { kind: "none" }
  | { kind: "refreshed"; tokens: TokenPair }
  | { kind: "expired" };

/**
 * Concurrent requests from one browser (page + prefetches) share a single refresh call.
 * The API also replays a rotation for ~30s, which covers multiple web instances.
 */
const inFlight = new Map<string, Promise<RefreshOutcome>>();

/** If the short-lived access cookie has lapsed but a refresh cookie exists, rotate tokens. */
function maybeRefresh(req: NextRequest): Promise<RefreshOutcome> {
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  if (!refresh || req.cookies.has(ACCESS_COOKIE)) return Promise.resolve({ kind: "none" });
  let pending = inFlight.get(refresh);
  if (!pending) {
    pending = callRefresh(req, refresh);
    inFlight.set(refresh, pending);
    void pending.finally(() => setTimeout(() => inFlight.delete(refresh), 5_000));
  }
  return pending;
}

async function callRefresh(req: NextRequest, refresh: string): Promise<RefreshOutcome> {
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-forwarded-for": req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown",
      },
      body: JSON.stringify({ refresh_token: refresh }),
      cache: "no-store",
    });
    if (res.ok) return { kind: "refreshed", tokens: (await res.json()) as TokenPair };
    const body = (await res.json().catch(() => null)) as { error?: { code?: string } } | null;
    // Rotated by another request outside the API's replay window: leave cookies alone.
    if (body?.error?.code === "refresh_token_superseded") return { kind: "none" };
    return { kind: "expired" };
  } catch {
    return { kind: "none" }; // API unreachable: don't log the user out
  }
}

function withCookie(req: NextRequest, name: string, value: string | null): NextRequest {
  const jar = new Map(req.cookies.getAll().map((c) => [c.name, c.value]));
  if (value === null) jar.delete(name);
  else jar.set(name, value);
  const headers = new Headers(req.headers);
  headers.set("cookie", [...jar].map(([k, v]) => `${k}=${v}`).join("; "));
  return new NextRequest(req.url, { headers, method: req.method });
}

export default async function proxy(req: NextRequest): Promise<NextResponse> {
  if (INTERNAL_LOCALE_PATH.test(req.nextUrl.pathname)) return NextResponse.next();
  const outcome = await maybeRefresh(req);
  let request = req;
  if (outcome.kind === "refreshed") {
    request = withCookie(req, ACCESS_COOKIE, outcome.tokens.access_token);
  } else if (outcome.kind === "expired") {
    request = withCookie(req, REFRESH_COOKIE, null);
  }

  const isApi = req.nextUrl.pathname.startsWith("/api/");
  const res = isApi
    ? NextResponse.next({ request: { headers: request.headers } })
    : (intl(request) as NextResponse);

  if (outcome.kind === "refreshed") setSessionCookies(res, outcome.tokens);
  if (outcome.kind === "expired") clearSessionCookies(res);
  return res;
}

export const config = {
  // Everything except Next internals and static files.
  matcher: ["/((?!_next|_vercel|.*\\..*).*)"],
};
