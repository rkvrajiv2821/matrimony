/**
 * Server Components can't modify cookies. When one finds the session is dead it redirects
 * here; we clear the stale cookies and send the user to the login page of their locale.
 */
import { localePrefixes, isLocale } from "@vaibhav/localization";
import { clearSessionCookies } from "@/lib/session";
import { NextResponse, type NextRequest } from "next/server";

export function GET(req: NextRequest) {
  const locale = req.nextUrl.searchParams.get("locale") ?? "en";
  const prefix = isLocale(locale) ? localePrefixes[locale] : localePrefixes.en;
  const res = NextResponse.redirect(new URL(`${prefix}/login`, req.url));
  clearSessionCookies(res);
  return res;
}
