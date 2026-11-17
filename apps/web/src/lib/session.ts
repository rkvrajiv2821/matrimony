/**
 * Web session = two httpOnly cookies holding the API's bearer tokens.
 * The browser never sees the tokens; Next.js route handlers and the proxy attach them.
 */
import type { NextResponse } from "next/server";

export const ACCESS_COOKIE = "vb_at";
export const REFRESH_COOKIE = "vb_rt";

const secure = process.env.NODE_ENV === "production";

export interface TokenPair {
  access_token: string;
  access_token_expires_in: number;
  refresh_token: string;
  refresh_token_expires_at: string;
}

export function setSessionCookies(res: NextResponse, tokens: TokenPair): void {
  const base = { httpOnly: true, secure, sameSite: "lax" as const, path: "/" };
  res.cookies.set(ACCESS_COOKIE, tokens.access_token, {
    ...base,
    maxAge: tokens.access_token_expires_in,
  });
  res.cookies.set(REFRESH_COOKIE, tokens.refresh_token, {
    ...base,
    expires: new Date(tokens.refresh_token_expires_at),
  });
}

export function clearSessionCookies(res: NextResponse): void {
  res.cookies.delete(ACCESS_COOKIE);
  res.cookies.delete(REFRESH_COOKIE);
}
