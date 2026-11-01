[![tests](https://github.com/zirkusmond/zirkusmond/actions/workflows/tests.yml/badge.svg)](https://github.com/zirkusmond/zirkusmond/actions/workflows/tests.yml)
[![staging](https://github.com/zirkusmond/zirkusmond/actions/workflows/staging.yml/badge.svg)](https://github.com/zirkusmond/zirkusmond/actions/workflows/staging.yml)
[![prod](https://github.com/zirkusmond/zirkusmond/actions/workflows/prod.yml/badge.svg)](https://github.com/zirkusmond/zirkusmond/actions/workflows/prod.yml)

# Zirkusmond

Website and booking platform for the touring circus show Zirkusmond.

The app covers show listings, ticket reservations, Stripe payments, QR-code ticket scanning,
newsletter signup, and rental information.

## Current architecture

This repository is a two-part application:

- **`backend/`** — Django 5 app, managed with [uv](https://docs.astral.sh/uv/)
- **`frontend/`** — TanStack Start + React 19 app, managed with `pnpm`

The frontend is the user-facing website. It fetches data from Django and proxies browser API
requests through TanStack Start to avoid CORS issues in development.

### Backend apps

Key Django apps:

- **`events`** — dated performances for a show
- **`shows`** — show data, descriptions, pricing, images
- **`reservations`** — reservations, guests, tickets, QR scanning
- **`reservations/payments`** — Stripe payment flows
- **`newsletter`** — newsletter signup and sending
- **`rentals`** — rental information
- **`stats`** — admin-facing reporting
- **`homepage_elements`** — homepage content blocks managed in Django

Django settings live in `backend/config/settings/` and are split by environment (`local`, `test`,
`staging`, `production`).

### Frontend

- File-based routing with TanStack Router in `frontend/src/routes/`
- React Query for data fetching and caching
- i18next for translations (`frontend/messages/`)
- Tailwind CSS 4 for styling
- Server-side rendering via TanStack Start

## Repository layout

```text
backend/        Django project and apps
frontend/       TanStack Start app
deploy/         Docker and nginx deployment files
docs/           Project documentation
.github/        CI/CD workflows
```

## Getting started

### Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js
- `pnpm`
- optionally `direnv` for loading `.envrc`

Environment variables are loaded via `.envrc`/direnv. Do not commit real secrets.

### Backend

```bash
cd backend
uv sync
uv run manage.py migrate
uv run manage.py runserver
```

### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

The frontend dev server runs on port `3000`.

### Run both

From the repository root:

```bash
make dev
```

## Common commands

### Backend

```bash
cd backend
uv run pytest
uv run pytest -k test_name
uv run ruff check --fix
uv run ruff format
```

### Frontend

```bash
cd frontend
pnpm test
pnpm run lint
pnpm run format
pnpm run check
pnpm exec tsc --noEmit
pnpm run build
```

## Payments

All active payments run through Stripe directly inside `backend/reservations/payments/`.

The current flow is:

1. the backend creates a `Reservation`
2. `CreatePaymentIntentView` creates a local `Payment` record and a Stripe `PaymentIntent`
3. the frontend confirms the payment with Stripe Elements
4. `StripeWebhookView` updates the payment to `completed`, `failed`, or `refunded`
5. signals/tasks send confirmation or refund emails and cleanup stale pending payments

See `docs/stripe-payment-system.md` for the full payment-flow documentation.

## Testing and CI

CI runs on every push and pull request:

- **Backend:** `uv run pytest`
- **Frontend:** `pnpm exec tsc --noEmit`

Pre-commit hooks handle backend Ruff checks plus general whitespace/YAML/JSON safety checks.

## Deployment

- Work from **`main`**
- **`staging`** and **`prod`** are deployment branches
- Deployment is Dockerized and configured in `deploy/`
- GitHub Actions in `.github/workflows/` drive CI and deploys

## Contributing

- Keep changes focused
- Add or update tests when changing backend behavior
- Run the relevant lint/test commands before opening a PR
- Open pull requests against `main`
