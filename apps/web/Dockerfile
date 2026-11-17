# syntax=docker/dockerfile:1
# Build context: repository root (the web app depends on workspace packages).
ARG NODE_IMAGE=node:22-alpine
FROM ${NODE_IMAGE} AS base
RUN corepack enable
WORKDIR /repo

FROM base AS build
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/web/package.json apps/web/
COPY packages/localization/package.json packages/localization/
COPY packages/design-system/package.json packages/design-system/
COPY packages/api-client/package.json packages/api-client/
RUN pnpm install --frozen-lockfile --filter @vaibhav/web...
COPY packages packages
COPY apps/web apps/web
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @vaibhav/web build

FROM ${NODE_IMAGE} AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup -S vaibhav && adduser -S -G vaibhav -u 10001 vaibhav
COPY --from=build --chown=vaibhav:vaibhav /repo/apps/web/.next/standalone ./
COPY --from=build --chown=vaibhav:vaibhav /repo/apps/web/.next/static ./apps/web/.next/static
USER vaibhav
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
