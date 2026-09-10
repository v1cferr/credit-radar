# CreditRadar frontend.
#
# Uses Next.js standalone output so the runtime image holds only the server
# and the files it actually needs, rather than the full node_modules tree.

FROM node:22-alpine AS deps

RUN corepack enable

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

# --ignore-scripts blocks every dependency install script from executing
# while building an image that will serve credit data. Nothing needed to
# compile the app relies on one: the only package that asks is a native
# resolver used by ESLint, which falls back to its prebuilt binary and is
# not run during the build anyway.
RUN --mount=type=cache,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store \
    && pnpm install --frozen-lockfile --ignore-scripts


FROM node:22-alpine AS builder

RUN corepack enable

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# No NEXT_PUBLIC_* value is needed or accepted: browser calls are
# same-origin and the reverse proxy routes /api to the backend, so the
# client bundle never learns the API's address. Anything inlined here would
# be readable by whoever loads the page.
ENV NEXT_TELEMETRY_DISABLED=1


# Invoked directly rather than through `pnpm build`: pnpm re-verifies the
# dependency tree before running a script, decides the --ignore-scripts
# install does not match the lockfile state, and tries to reinstall, which
# cannot prompt without a TTY. The command is the same one the script runs.
RUN node_modules/.bin/next build


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
