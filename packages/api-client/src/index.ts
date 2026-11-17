import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type { components, paths };
export type Schemas = components["schemas"];

/** Machine-readable error envelope returned by every API error. */
export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> | null };
}

export function createApiClient(baseUrl: string, init?: { headers?: Record<string, string> }) {
  return createClient<paths>({ baseUrl, headers: init?.headers });
}
