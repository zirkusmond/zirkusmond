# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Zirkusmond: website and booking platform for a touring circus show — show listings, ticket
reservations, QR-code ticket scanning, and a newsletter. Django backend (`backend/`) with a
TanStack Start (React) frontend (`frontend/`).

## Commands

### Backend (`backend/`, managed with [uv](https://docs.astral.sh/uv/), Python 3.12)

```bash
uv sync                                    # install deps
uv run manage.py migrate
uv run manage.py runserver
uv run pytest                              # all tests
uv run pytest reservations/payments/tests.py::StripeWebhookViewTest  # single test class
uv run pytest -k test_name                 # single test by name
uv run ruff check --fix                    # lint
uv run ruff format                         # format
```

Line length is 100 (`backend/pyproject.toml`). Tests use `config.settings.test` and live in each
app's `tests.py`.

### Frontend (`frontend/`, pnpm)

```bash
pnpm install
pnpm run dev          # dev server, port 3000
pnpm run tailwind     # (from root context) watch & rebuild Tailwind into backend/static/css
pnpm run build
pnpm test             # vitest run
pnpm run lint         # eslint
pnpm run format       # prettier --write . && eslint --fix
pnpm run check        # prettier --check .
pnpm exec tsc --noEmit  # typecheck (what CI runs)
```

### Run both at once

`make dev` from the repo root runs the Django dev server and the frontend dev server together.

### CI

GitHub Actions (`.github/workflows/tests.yml`) runs `uv run pytest` on the backend and
`tsc --noEmit` on the frontend for every push/PR (except to `staging`/`prod`). Pre-commit hooks
(`pre-commit install`) run `ruff --fix` + `ruff format` on the backend and basic
whitespace/YAML/JSON/merge-conflict checks on every commit.

## Branching / deploys

- Work off `main`. `staging` and `prod` are deploy branches driven by their own GitHub Actions
  workflows (`staging.yml`, `prod.yml`) — never commit to them directly.
- Deployment is Dockerized; see `deploy/` (per-environment `docker-compose.yml`, nginx config,
  `start-server.sh`) and `.github/workflows/`.
- Required env vars (Django secret key, DB, email, Stripe keys, etc.) are loaded via
  `.envrc`/direnv. Never commit real secret values.

## Architecture

### Backend: Django apps

- **`events`** — an `Event` is one dated performance (date/time, admission time, reservation
  capacity, `open_for_reservation` flag) belonging to a `Show`. `reservation_count()` /
  `reservation_open()` query confirmed `Payment`s (`status=COMPLETED`) to compute capacity.
- **`shows`** — a `Show` is the production itself (title, description, images, ticket pricing).
  Ticket pricing is a sliding scale: `base_ticket_price` plus optional `min_ticket_price` /
  `max_ticket_price` bounds (defaulting to ±10 from base). `UpcomingShow`/`PastShow`/
  `UnscheduledShow` and `UpcomingEvent`/`PastEvent` are proxy models with custom managers used to
  organize the Django admin.
- **`reservations`** — a `Reservation` (one purchaser, keyed by UUID) belongs to an `Event` and has
  many `Guest`s (each with their own `ticket_id` UUID used for QR check-in). Two sub-packages:
  - `reservations/payments/` — payment processing (see below).
  - `reservations/qr_scanner/` — endpoints backing the staff-facing QR ticket scanner.
- **`stats`**, **`newsletter`**, **`rentals`** — smaller supporting apps (admin-facing stats,
  newsletter signup/sending, equipment/venue rental info).
- Settings are split under `backend/config/settings/`: `base.py` plus `local.py` / `staging.py` /
  `production.py` / `test.py`. Most config is env-var driven (see `.envrc`).
- Django admin is customized with `django-unfold` and mounted at `/mondmin/` (not `/admin/`).

### Payment system — Stripe-only flow

All active payments run through Stripe directly via the custom `Payment` model in
`reservations/payments/`:

- **`Payment`** — the canonical payment record. It stores the reservation link, selected sliding-
  scale `custom_ticket_price`, Stripe PaymentIntent ID, detected payment method, and lifecycle
  status (`PENDING`/`COMPLETED`/`FAILED`/`REFUNDED`/`ABANDONED`).
- **`CreatePaymentIntentView`** — creates a local `Payment`, validates the custom ticket price
  against the show's allowed range, creates a Stripe `PaymentIntent`, stores its ID, and returns
  the client secret to the frontend.
- **`stripe_return`** — handles Stripe's return redirect, refreshes payment-method details from the
  PaymentIntent's latest charge when available, and redirects the customer to the frontend success
  or failure page.
- **`StripeWebhookView`** — the source of truth for final payment state. It marks payments as
  `COMPLETED`, `FAILED`, or `REFUNDED` from Stripe webhook events.
- **Signals/tasks** — `post_save` on `Payment` queues confirmation emails for completed payments and
  refund emails for refunded payments; a Celery task marks stale `PENDING` payments as
  `ABANDONED`.

`docs/stripe-payment-system.md` documents the current Stripe PaymentIntent flow.

### Frontend: TanStack Start + React 19

- File-based routing under `frontend/src/routes/` (TanStack Router; `routeTree.gen.ts` is
  generated — don't hand-edit).

#### Route file structure

Every file in `src/routes/` follows the same shape — match it for new routes:

1. Imports: router/query imports first, then local components/lib via the `#/` alias.
2. A `const RouteComponent = () => { ... }` (or a descriptively-named component for the home page)
   containing only wiring — param/search access (`Route.useParams()`/`Route.useSearch()`) and data
   hooks. Actual page content/logic is delegated to components in
   `src/components/zirkusmond/...`; route files stay thin.
3. `export const Route = createFileRoute("/path")({ ... })` at the bottom, referencing
   `RouteComponent` declared above it (safe due to hoisting) with whichever of these keys apply:
   - `loader` — prefetches via `queryClient.query({ ...someQueryOptions(...), staleTime: "static" })`
     (the non-deprecated replacement for `ensureQueryData`, which returns cached data without
     refetching when `staleTime` is `"static"`); a 404 from the API (`ApiError` with
     `status === 404`) is converted to `throw notFound()`.
   - `component` — always present.
   - `notFoundComponent` — paired with a loader that can throw `notFound()`.
   - `head` — returns `{ meta: [...] }` for SEO: `title`, and usually `description`/`keywords` in
     German. Use `({ loaderData }) => ...` when the title needs loader data.
   - `validateSearch` — for routes reading query-string state (e.g. `payment.success.tsx`'s
     `reservationId`); pair with a typed `interface` and a `validate<Name>Search` function.
4. Inside the component, read loader-prefetched data with `useSuspenseQuery(sameQueryOptions(...))`
   (same query key as the loader — reads the cache instead of refetching); use plain `useQuery` for
   data with no loader prefetch (e.g. `qr-scanner.tsx`, `payment.success.tsx`).
5. Page content is composed from shared layout primitives in
   `src/components/zirkusmond/general/`: `PageContainer` (outer wrapper, on almost every route),
   `PageHeader` (title), `ContentSection`/`SectionCard`/`SectionCardSkeleton` (content blocks,
   support an `isLoading`/`skeleton` pair), and `SectionDivider` (decorative divider, `type`
   `"flower"` | `"kite"`).
6. All user-facing copy goes through `useTranslation()`/`t("key")` (keys follow a
   `page_<route>_<part>` convention), not hardcoded strings — copy is German-first.

Data fetching uses TanStack Query `queryOptions` factories in `frontend/src/lib/api.ts`, shared
  between route `loader`s (`queryClient.query`) and components (`useSuspenseQuery`) so both hit the
  same cache entry — see `router.tsx` for the SSR/query hydration wiring.
- **API access is dual-mode** (`frontend/src/lib/api.ts`): on the server (SSR loaders), requests go
  straight to Django at `API_URL`; in the browser, requests go through the `/api/$` catch-all route
  (`routes/api.$.tsx`), which proxies to Django server-side — this avoids CORS since Django doesn't
  send CORS headers. Always fetch through `apiUrl()`/`fetchJson()`/`postJson()`, not raw `fetch`.
- **Django uses snake_case, the frontend uses camelCase.** `keysToCamelCase`/`keysToSnakeCase`
  (`frontend/src/lib/utils.ts`) convert automatically inside `fetchJson`/`postJson` — write
  frontend types/props in camelCase and let this conversion handle the boundary.
  `/media` (image uploads) is proxied straight to Django in dev (`vite.config.ts`); nginx serves it
  directly from disk in staging/prod.
- UI components: `src/components/ui/` is vendored shadcn/ui — regenerate via
  `pnpm dlx shadcn@latest add <component>` rather than hand-editing (eslint ignores this dir
  entirely, and Prettier/format scripts do too — check `.prettierignore`). App-specific components
  live in `src/components/zirkusmond/`, grouped by feature (`event/`, `form/`, `general/`,
  `home/`, `qr-scanner/`, `reserve/`, `show/`).
- i18n is `i18next`/`react-i18next` (`src/i18n.ts`), with translations in `frontend/messages/{en,de}.json`.
  German (`de`) is the default/fallback locale. (Note: the generic frontend `README.md` mentions
  Paraglide i18n from the original scaffold — that's stale; the project uses i18next.)
- Path alias `#/*` maps to `frontend/src/*` (see `imports` in `package.json`).
