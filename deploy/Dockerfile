# ── Stage 1: Frontend build ───────────────────────────────────────────────────
FROM node:24-slim AS frontend-builder

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /build/frontend

# Copy package files
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source files
COPY frontend ./

ARG VITE_STRIPE_PUBLISHABLE_KEY
ARG VITE_API_URL
ARG VITE_SENTRY_DSN
ENV VITE_STRIPE_PUBLISHABLE_KEY=$VITE_STRIPE_PUBLISHABLE_KEY
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN

# Used only by the Sentry Vite plugin during `pnpm build` to upload source maps.
# Kept as ARGs (not ENV) so the auth token isn't persisted in the image.
ARG SENTRY_ORG
ARG SENTRY_PROJECT
ARG SENTRY_AUTH_TOKEN

# Build TanStack Start app
RUN pnpm build

# ── Stage 2: Python venv ──────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS python-builder

ENV UV_PROJECT_ENVIRONMENT=/usr/src/backend/.venv

COPY backend/pyproject.toml backend/uv.lock /build/
RUN uv sync --frozen --no-dev --project /build

# ── Stage 3: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log

WORKDIR /usr/src

COPY deploy/start-server.sh .
RUN chmod +x start-server.sh

# Copy Python backend
COPY --from=python-builder /usr/src/backend/.venv ./backend/.venv
COPY backend ./backend

# Copy built TanStack Start app
COPY --from=frontend-builder /build/frontend/.output ./frontend/.output

COPY deploy/nginx.default /etc/nginx/sites-available/default
RUN mkdir -p /srv/data/static /srv/data/media

ENV PATH="/usr/src/backend/.venv/bin:$PATH"
ENV NODE_ENV=production

EXPOSE 8000

CMD ["/usr/src/start-server.sh"]
