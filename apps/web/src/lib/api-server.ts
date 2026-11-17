import "server-only";

import type { ApiErrorBody } from "@vaibhav/api-client";
import { cookies, headers } from "next/headers";
import { ACCESS_COOKIE } from "./session";

/** Base URL of the FastAPI service as seen from the Next.js server (never the browser). */
export const API_URL = process.env.VAIBHAV_API_INTERNAL_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: ApiErrorBody | null,
  ) {
    super(body?.error.message ?? `API error ${status}`);
  }
  get code(): string {
    return this.body?.error.code ?? "generic";
  }
}

/** Client IP forwarded to the API so per-IP rate limits apply to the real visitor. */
export function forwardedFor(h: Headers): string {
  const xff = h.get("x-forwarded-for")?.split(",")[0]?.trim();
  return xff || h.get("x-real-ip") || "unknown";
}

/** Raw call to the API. Used by route handlers that need the full Response. */
export async function callApi(
  path: string,
  init: RequestInit & { token?: string | null; clientIp?: string } = {},
): Promise<Response> {
  const { token, clientIp, headers: extra, ...rest } = init;
  const h = new Headers(extra);
  if (!h.has("content-type") && rest.body) h.set("content-type", "application/json");
  if (token) h.set("authorization", `Bearer ${token}`);
  if (clientIp) h.set("x-forwarded-for", clientIp);
  return fetch(`${API_URL}/api/v1${path}`, { ...rest, headers: h, cache: "no-store" });
}

/** Authenticated GET from a Server Component. Throws ApiError on non-2xx. */
export async function apiGet<T>(path: string): Promise<T> {
  const token = (await cookies()).get(ACCESS_COOKIE)?.value;
  const res = await callApi(path, { token, clientIp: forwardedFor(await headers()) });
  if (!res.ok) {
    throw new ApiError(res.status, (await res.json().catch(() => null)) as ApiErrorBody | null);
  }
  return (await res.json()) as T;
}
