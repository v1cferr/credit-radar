# CreditRadar frontend.
#
# Uses Next.js standalone output so the runtime image holds only the server
# and the files it actually needs, rather than the full node_modules tree.

FROM node:22-alpine AS deps

RUN corepack enable

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store && pnpm install --frozen-lockfile


FROM node:22-alpine AS builder

RUN corepack enable

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* values are inlined into the client bundle at build time, so
# only genuinely public configuration may be passed here. Provider
# credentials and session state belong exclusively to the backend.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8007
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm build


FROM node:22-alpine AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Runs unprivileged.
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 --ingroup nodejs nextjs

WORKDIR /app

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
