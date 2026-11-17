# VAIBHAV — Development Plan

Source documents: [`prd/PRD_v1.0_Complete.pdf`](prd/PRD_v1.0_Complete.pdf) (baseline) and
[`prd/PRD_v1.1_Update.pdf`](prd/PRD_v1.1_Update.pdf) (name + dormant monetization; overrides v1.0 where they conflict).

Status: **Phase 1 (Foundation) complete** — running on the §9 defaults. Next: Phase 2 (Profiles).

### Phase 1 delivered
- API: OTP auth (Redis challenges, hashed codes, cooldown / hourly / attempt limits, single use, no account enumeration),
  sessions with refresh rotation + reuse detection, consent capture & history, roles, immutable audit log,
  feature flags (`monetization_enabled=false`), entitlements service with the seeded `free` plan, health checks.
- Web: en / ta / Tanglish (`/en`, `/ta`, `/tanglish`), public site shell, login (phone → OTP), dashboard, settings
  (display language, logged-in devices, log out everywhere). Tokens live only in httpOnly cookies (ADR 0001).
- Quality: 46 API tests (real MySQL, migrations down/up), i18n parity tests, 28 Playwright E2E tests
  (desktop + mobile, all three languages), strict mypy, ruff, ESLint, CI workflow, Dockerfiles, docker-compose.
- Deferred by design: admin MFA (Phase 5), nonce-based CSP (Phase 7), real SMS provider (needs decision §9.3),
  email verification (needs email provider).

---

## 1. Product in one paragraph

VAIBHAV is a free, marriage-oriented matchmaking platform for one configurable Tamil Nadu community, in Tamil,
English and Tanglish, on web + Android + iOS. Members register by mobile OTP (optionally on behalf of an adult
family member, with that adult's consent), build a moderated profile, set must-have / preferred partner
preferences, discover profiles via explainable (non-predictive) match scores, exchange interests, and chat only
after mutual acceptance. Operations staff moderate profiles, verify members, handle reports and support through
a separate admin portal with MFA and full audit logging. Payments are built but switched off.

## 2. v1.0 → v1.1 reconciliation

| Topic | v1.0 | v1.1 (wins) |
|---|---|---|
| Name | "Tamil Matrimony Platform" | **VAIBHAV** everywhere (UI, emails, admin, docs) |
| Payments | "No payment gateway required for MVP" | Build monetization module + 11 tables + 8 endpoints, **flag off** (`monetization_enabled=false`) |
| Free model | No paid tiers | Unchanged at launch; all members get the Free entitlement set |
| Ranking | No pay-to-win | Reinforced: payment state must never reach search/matching |

## 3. Architecture

```
vaibhav/
├── apps/
│   ├── web/            Next.js 15 (App Router, TS) — public site + member app
│   ├── admin/          Next.js — admin portal (separate auth boundary + deploy)
│   └── mobile/         React Native / Expo — Phase 6
├── services/api/       FastAPI modular monolith
│   └── app/
│       ├── common/ database/ security/          # shared kernel
│       ├── auth/ users/ consent/ delegation/
│       ├── profiles/ media/ community/ locations/
│       ├── preferences/ discovery/ matching/
│       ├── interests/ messaging/ safety/
│       ├── verification/ horoscope/ notifications/
│       ├── support/ privacy/ cms/ admin/ audit/
│       ├── flags/ entitlements/                  # v1.1, active from day one
│       └── monetization/                         # v1.1, dormant
├── packages/
│   ├── api-client/     generated from OpenAPI (openapi-typescript)
│   ├── design-system/  tokens (maroon / ivory / muted gold — provisional) + shared components
│   └── localization/   en, ta, ta-Latn (Tanglish) message catalogues
├── infra/              docker/ ci/ deploy/ monitoring/ backups/
└── docs/               prd/ api/ runbooks/ security/ decisions/
```

### Stack choices

| Concern | Choice | Why |
|---|---|---|
| JS monorepo | pnpm workspaces + Turborepo | web/admin/mobile share packages |
| Python tooling | uv, ruff, mypy, pytest | fast, typed |
| API | FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic | PRD stack; OpenAPI generated |
| DB | MySQL 8, InnoDB, utf8mb4, strict mode | PRD §7 |
| IDs | BIGINT internal PK + UUIDv7 `public_id` exposed in APIs | PRD §7; no enumerable IDs |
| Cache / limits / jobs | Redis; **arq** workers (async, Redis-backed) | OTP throttles, notifications, scans, recommendation refresh |
| Realtime chat | FastAPI WebSocket + Redis pub/sub fan-out | stateless API instances |
| Files | S3-compatible private buckets (MinIO locally), presigned upload URLs, ClamAV scan in worker | PRD §8.1, §10.2 |
| Search | MySQL indexed queries (MVP); Meilisearch/OpenSearch later | PRD §15.1 |
| i18n (web) | next-intl with locales `en`, `ta`, `ta-Latn` | Tanglish as a selectable display mode |
| Auth tokens | 15-min access JWT + rotating refresh token (hashed in `user_sessions`); web uses httpOnly cookies + CSRF; mobile uses secure OS storage | PRD §4.1, §10.1 |
| Message bodies | App-level AES-GCM (envelope key from secret store) → `body_encrypted` | PRD §7 |
| Tests | pytest + testcontainers (real MySQL), Schemathesis contract tests, Playwright E2E | PRD §14 |
| Observability | structlog JSON logs, OpenTelemetry, Sentry | PRD §11 |

### Cross-cutting rules baked into the code

1. **Entitlements gate everything.** Feature checks call `entitlements.require(user, "messaging.send")`;
   the seeded `free` plan grants all core keys. Turning on monetization later = new plan rows, not code changes.
2. **Safety is never gated.** Block, report, privacy, deletion and support endpoints do not consult entitlements (enforced by test).
3. **Ranking can't see money.** `import-linter` contract: `discovery`, `matching` must not import `monetization` / `entitlements`.
4. **Monetization off = invisible.** Routers for `/plans`, `/orders`, `/payments/*`, `/refunds`, `/invoices` return 404 while the flag is off; web/admin hide those routes at build/runtime.
5. **Deny-by-default authz** at both user and profile scope; every admin mutation writes `audit_logs` (before/after JSON).
6. **Privacy in serializers.** Separate response schemas per audience (owner / connected member / any member / admin role) — DOB → age, contact hidden, horoscope/photos by visibility setting.
7. **UTC storage, Asia/Kolkata display.** Server-side 18+ check.

## 4. Data model

All v1.0 §7 tables (≈45) plus v1.1 §4.2 tables (11). Grouped migration order:

1. Identity: `users, user_sessions, otp_challenges*, roles, user_roles, consents, delegated_access`
2. Reference: `locations, community_taxonomy, system_settings, feature_flags, content_pages, notification_templates`
3. Profile: `profiles, profile_personal_details, profile_community, profile_family_details, profile_education, profile_employment, profile_photos, profile_documents, profile_status_history, horoscope_details, horoscope_files`
4. Discovery: `partner_preferences, preference_community_values, saved_searches, profile_views, shortlists, hidden_profiles, match_recommendations`
5. Connections: `interests, conversations, conversation_members, messages, message_attachments, blocks`
6. Trust & ops: `reports, moderation_actions, support_tickets, verification_requests, admin_assignments, audit_logs, notifications, notification_preferences, notification_deliveries, privacy_requests*`
7. Monetization (dormant): `plans, plan_versions, plan_entitlements, user_entitlements, orders, payment_attempts, payment_webhook_events, refunds, invoices, gateway_reconciliation`

`*` = small additions not named in the PRD but implied (OTP challenge store if not purely Redis; tracking export/delete requests to completion per §13).
Indexes and unique constraints exactly as PRD §7.1 (active-interest pair, normalized conversation pair, etc.).

## 5. API

Base `/api/v1`, all endpoints in PRD §8 + v1.1 §4.3. Standards: machine-readable error codes, cursor
pagination for feeds, bounded page size for search, `Idempotency-Key` on retry-prone POSTs, per-endpoint
rate limits (OTP, search, interest, message, report), short-lived WS tokens with membership re-check per event.

## 6. Delivery phases (web + backend first, mobile after)

| Phase | Scope | Exit gate |
|---|---|---|
| **0. Policy** (owner) | Community name/taxonomy, required fields, moderation policy, providers, hosting, brand | Answers to §9 |
| **1. Foundation** | Monorepo, Docker Compose (MySQL/Redis/MinIO/Mailpit), CI (lint, types, tests, secret scan), Alembic base, OTP auth + sessions, roles, audit log, feature flags, entitlements (free plan), i18n scaffolding, design tokens, public site shell | Register → OTP → logged in, in en/ta/Tanglish; CI green |
| **2. Profiles** | Consent capture, account type, family delegation invite flow, multi-step wizard with save/resume + completion meter, photos (presign → scan → moderate), community taxonomy, preferences, profile status machine, owner preview | Profile created, submitted, approved by admin |
| **3. Discovery** | Eligibility/visibility/block filters, must-have filters, weighted soft scoring (versioned weights), mutuality labels, match explanation, search + saved searches, shortlist/hide/viewed | Search & matching acceptance tests |
| **4. Connections** | Interest state machine, conversations, WS chat (delivery/read/typing), notifications (in-app; email/SMS/push providers), block/report/mute | E2E connection + safety tests |
| **5. Admin & trust** | Admin app with MFA; dashboard, member mgmt, profile moderation, verification desk, report triage, support tickets, CMS, templates, taxonomy editor, roles, audit viewer; privacy export/delete; horoscope details (manual) | Ops walkthrough; audit checks |
| **5b. Monetization (dormant)** | v1.1 tables, plan versioning, server-side pricing, orders, Razorpay sandbox adapter, signed+deduped webhooks, refunds, invoices, reconciliation, admin views | v1.1 §7 acceptance tests pass with flag **off** and in sandbox with flag on |
| **6. Mobile** | Expo app on the same API + api-client + localization | Closed beta Android/iOS |
| **7. Hardening** | Security review (IDOR/XSS/CSRF/upload abuse), load tests (search P95 < 1.5 s, reads < 500 ms), WCAG 2.2 AA, backup restore drill, legal pages | Go-live checklist |

PRD estimate: 20–28 weeks for a small team end-to-end.

## 7. MVP vs post-MVP (PRD Appendix A)

Post-MVP: Google sign-in, video intros, voice/video calls, assisted matchmaking, automated Porutham engine,
advanced personalization, external verification integrations, incognito mode. Monetization activation (v1.1 §6 stages) is post-launch.

## 8. Risks to watch

Community fairness/legal review of community filters · family-account abuse (delegation must require adult's OTP consent) ·
fake profiles · SMS cost on a free product · Tanglish spelling consistency (keep a glossary) · moderation capacity.

## 9. Open decisions (needed from product owner)

| # | Decision | Blocks | Default if unanswered |
|---|---|---|---|
| 1 | Exact launch community + sub-community taxonomy + eligibility rules | Phase 2 seed data | Configurable placeholder taxonomy |
| 2 | Required vs optional profile fields | Phase 2 wizard | Basic + Community + Education + Career + 1 photo required; rest optional |
| 3 | SMS/OTP provider (e.g. MSG91, 2Factor, Twilio) and email provider | Phase 1 go-live (dev uses console OTP) | Pluggable adapter; console provider in dev |
| 4 | Hosting provider/region | Phase 1 deploy | AWS ap-south-1 (Mumbai) |
| 5 | Verification provider for selfie/ID | Phase 5 | Manual review queue only |
| 6 | Brand assets (logo, fonts, tagline) | UI polish | Maroon/ivory/gold tokens, Noto Sans Tamil + Inter |
| 7 | Horoscope at launch | Phase 5 | Manual details + display only (no Porutham) |
| 8 | Moderation staffing / SLA / appeal policy | Phase 5 config | Configurable SLAs |
