# ADR 0001 — Web authentication via a Next.js backend-for-frontend

**Status:** Accepted (Phase 1) · **Date:** 2026-11-17

## Context

The API must serve web, Android and iOS (PRD §8). Mobile apps hold tokens in secure OS storage.
For the web, PRD §10.1 requires secure cookies, CSRF protection and refresh-token rotation, and
tokens must not be readable by page JavaScript (XSS blast radius).

## Decision

1. **The API is bearer-token only.** `POST /auth/otp/verify` returns a 15-minute JWT access token and
   a 30-day opaque refresh token. Only a keyed hash of the refresh token is stored (`user_sessions`).
   Every request re-checks the session row, so logout / revoke is immediate.
2. **The web app is a BFF.** The browser talks only to Next.js:
   - `/api/auth/request-otp|resend-otp|verify-otp|logout` wrap the auth endpoints and move tokens into
     `httpOnly`, `SameSite=Lax`, `Secure` (prod) cookies — the browser never sees a token.
   - `/api/v1/*` forwards other calls with the bearer token from the cookie (auth/admin paths blocked).
   - Mutations require a same-origin `Origin` header (CSRF), on top of SameSite.
   - `src/proxy.ts` refreshes the access cookie when it lapses, before pages render.
3. **Refresh rotation with reuse detection.** Each refresh issues a new refresh token and keeps the
   previous hash. Presenting a rotated-out token **after** a 30-second grace window revokes the
   session (theft signal, audited). Inside the window — the normal case of a page and its prefetches
   refreshing at once — the API replays the same rotation (sealed in Redis for 30 s) so parallel
   requests don't log the member out. The web proxy also de-duplicates in-flight refreshes.
4. **Client IP.** The BFF forwards the visitor IP in `X-Forwarded-For`; the API trusts exactly
   `VAIBHAV_TRUSTED_PROXY_COUNT` hops. Per-IP OTP limits therefore apply to visitors, not to the BFF.

## Consequences

- Mobile apps call the API directly with the same endpoints.
- If the API is ever exposed publicly *and* behind the BFF, the trusted-proxy count must match the
  real hop count at each entry point, or per-IP limits can be spoofed. Revisit with the production
  topology (Phase 7).
- A strict nonce-based CSP is deferred to Phase 7; the baseline CSP blocks framing, third-party
  scripts and cross-origin connections.
- Admin MFA is not implemented yet (Phase 5). Until then admin endpoints are reachable only by roles
  granted through the server-side CLI.
