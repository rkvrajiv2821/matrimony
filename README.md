# VAIBHAV

Free, marriage-focused Tamil matrimony platform for Tamil Nadu: web + Android + iOS, in Tamil, English and Tanglish.

- Product requirements: [`docs/prd/`](docs/prd) (v1.0 baseline + v1.1 update)
- Development plan and phase status: [`docs/PLAN.md`](docs/PLAN.md)
- Architecture decisions: [`docs/decisions/`](docs/decisions)

## Repository layout

```
apps/web/              Next.js 16 — public site + member web app (BFF for the API)
services/api/          FastAPI modular monolith (Python 3.13, SQLAlchemy 2, Alembic, MySQL 8, Redis)
packages/localization/ en / ta / ta-Latn (Tanglish) message catalogues + parity tests
packages/design-system/ Design tokens (provisional maroon / ivory / muted gold)
packages/api-client/   OpenAPI schema + generated TypeScript types
docs/                  PRDs, plan, decisions
```

## Run it locally

### Option A — Docker Compose (everything)

```bash
docker compose up --build
```

Web: http://localhost:3000 · API docs: http://localhost:8000/docs · Mail catcher: http://localhost:8025

### Option B — native (faster inner loop)

Prerequisites: Python 3.13 + [uv](https://docs.astral.sh/uv/), Node 22 + pnpm 10, MySQL 8 and Redis (e.g. `docker compose up mysql redis`).

```bash
pnpm install
```

```bash
cd services/api && cp .env.example .env && uv sync && uv run alembic upgrade head
```

```bash
cd services/api && uv run uvicorn app.main:app --reload --port 8000
```

```bash
pnpm --filter @vaibhav/web dev
```

In local mode the OTP is shown on the login screen ("Development code") instead of being sent by SMS.
This is controlled by `VAIBHAV_OTP_DEBUG_ECHO` and the API refuses to start with it enabled in staging/production.

### Make yourself an admin

Register through the web app first, then:

```bash
cd services/api && uv run python -m app.cli grant-role +919876543210 super_admin
```

## Tests

```bash
cd services/api && uv run pytest
```

API tests need MySQL (database `vaibhav_test`, user `vaibhav`) and Redis; they run the real migrations down and up first.

```bash
pnpm --filter @vaibhav/localization test
```

End-to-end (needs the API on :8000 with `VAIBHAV_OTP_DEBUG_ECHO=true` and the web app on :3000):

```bash
pnpm --filter @vaibhav/web test:e2e
```

## After changing an API schema

```bash
pnpm api:openapi
```

This regenerates `packages/api-client` (CI fails if it is stale).
