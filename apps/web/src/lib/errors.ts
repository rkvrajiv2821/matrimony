/** Map an API error code to a localized message key under `errors.*`. */
const KNOWN = new Set([
  "invalid_phone",
  "otp_cooldown",
  "rate_limited",
  "otp_invalid",
  "otp_expired",
  "otp_too_many_attempts",
  "consent_required",
  "account_inactive",
  "validation_error",
  "network",
]);

export function errorKey(code: string | undefined): string {
  if (code && KNOWN.has(code)) return code;
  if (code === "not_authenticated" || code === "session_revoked" || code === "token_expired") {
    return "session_expired";
  }
  return "generic";
}

export interface ApiErrorJson {
  error?: { code?: string; message?: string; details?: Record<string, unknown> | null };
}

export async function postJson<T>(
  url: string,
  body: unknown,
  method: "POST" | "PATCH" | "DELETE" = "POST",
): Promise<{ ok: true; data: T } | { ok: false; status: number; error: ApiErrorJson["error"] }> {
  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers: { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
    });
  } catch {
    return { ok: false, status: 0, error: { code: "network" } };
  }
  if (res.status === 204) return { ok: true, data: undefined as T };
  const json = (await res.json().catch(() => ({}))) as T & ApiErrorJson;
  if (!res.ok) return { ok: false, status: res.status, error: json.error ?? { code: "generic" } };
  return { ok: true, data: json };
}
