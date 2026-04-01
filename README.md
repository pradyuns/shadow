# Shadow

Shadow is a distributed competitor-intelligence platform for monitoring competitor pages, detecting meaningful changes, clustering related alerts, and suppressing recurring noise.

## What It Does

- Monitors competitor URLs on a schedule.
- Captures and diffs page snapshots.
- Filters static and adaptive per-monitor noise.
- Classifies changes and creates alerts.
- Clusters related alerts into higher-level competitive events.
- Delivers notifications via Slack/email (including digest mode).

## Public Demo Surface

- The deployed public app is intentionally limited to:
  - Landing page (`/`)
  - Closed beta signup page (`/closed-beta`)
- In production, set `PUBLIC_LANDING_ONLY_MODE=true` to disable non-public API routes.
- The full backend/workers implementation remains in this repository for code review and portfolio depth.

## Architecture

### Runtime Services

- `frontend`: React + TypeScript + Vite (served by Nginx)
- `api`: FastAPI
- `worker-scraper`: Celery (`scraper` queue)
- `worker-analysis`: Celery (`analysis` queue)
- `worker-default`: Celery (`default` queue)
- `beat`: Celery Beat scheduler
- `postgres`: relational data
- `mongodb`: snapshots/diffs/analyses/learned patterns
- `redis`: broker, result backend, cache
- `flower`: Celery task monitor

### Data Model Split

- PostgreSQL: users, monitors, alerts, clusters, notification settings, beta signups
- MongoDB: snapshots, diffs, analyses, adaptive noise-learning documents

## Closed Beta API

- `POST /api/v1/public/beta-signups`
- Request body:
  - `{ "email": "you@company.com" }`
- Response:
  - `202 Accepted` with `{ "status": "accepted" }`
- Duplicate emails are accepted idempotently and do not create duplicate rows.

## End-to-End Pipeline

1. Scrape URL and store snapshot.
2. Compute diff against previous snapshot.
3. Apply noise filtering (global + monitor + learned patterns).
4. Classify significance/categories.
5. Create alert (if significant) and assign cluster.
6. Send notifications.

## Scrape Cadence And Diff Timing

- Scrape cadence is user-controlled per monitor via `check_interval_hours`.
- Manual `Scrape now` can be used for immediate on-demand checks.
- A diff is generated only after at least two snapshots exist for a monitor.
- There is no hard built-in cap on number of diffs per hour/day.

## Key Features

### Alert Clustering Engine

Implemented in `backend/workers/clustering/alert_clusterer.py`.

- Online single-linkage clustering per competitor.
- Similarity uses weighted blend:
  - Temporal decay with true half-life: `exp(-hours * ln(2) / T)`
  - Category Jaccard overlap
  - Keyword Jaccard overlap
- Merge threshold: `0.45`
- Active window: `48 hours`
- Concurrency-safe with:
  - `pg_advisory_xact_lock` on `(user_id, competitor_name)`
  - `SELECT ... FOR UPDATE` when evaluating candidate clusters

### Adaptive Noise Learning

Implemented in:

- `backend/workers/scraper/adaptive_noise_learning.py`
- `backend/workers/tasks/diffing.py`
- `backend/app/api/v1/noise_learning.py`

Capabilities:

- Learns recurring, monitor-specific noisy line templates.
- Promotes high-confidence patterns to active regex filters.
- Tracks usage and decays stale patterns.
- Uses semantic safeguards (pricing/action/competitor terms) to prevent unsafe auto-promotion.

## Reliability Safeguards

- Diff idempotency (`snapshot_after_id` guard)
- Notification idempotency (`alert.notified_at` guard)
- Retry/backoff policies across Celery tasks
- Auto-pause monitors after repeated scrape failures

## Local Development

### Start Stack

```bash
make up
```

### Run Migrations

```bash
make migrate
```

### Landing-Only API Mode (Production Behavior)

```bash
PUBLIC_LANDING_ONLY_MODE=true
```

This keeps `/api/v1/public/*` and health endpoints available while disabling private product APIs from the public deployment surface.

### Security Config (Required)

- `JWT_SECRET_KEY` must be set to a unique non-default value.
- The API will refuse startup if `JWT_SECRET_KEY` is empty or still set to `change-this-to-a-random-secret-key`.
- Seed credentials are not hardcoded. `backend/scripts/seed_data.py` reads:
  - `SEED_ADMIN_PASSWORD`
  - `SEED_DEMO_PASSWORD`
- If those env vars are not set, the seed script generates random passwords per run and prints them once.

### Firecrawl (Optional)

- Set `FIRECRAWL_API_KEY` in `.env` to enable Firecrawl integration.
- When configured, Firecrawl can be used as:
  - automatic fallback for bot-detection pages
  - primary scraper for monitors with `use_firecrawl=true`
- If `FIRECRAWL_API_KEY` is not set, the app runs normally with httpx/Playwright only.

### Backend Tests

```bash
cd backend
./.venv/bin/pytest -q
```

### Frontend Checks

```bash
cd frontend
npm run lint
npm run build
```

## Health & Observability

- API liveness: `GET /api/v1/health`
- API readiness: `GET /api/v1/health/ready`
- Flower dashboard: `http://localhost:5555`

## Closed Beta Email Retrieval

To list collected signup emails directly from Postgres:

```sql
SELECT email, created_at
FROM beta_signups
ORDER BY created_at DESC;
```

## Smoke Test Note

Scheduled scraping uses idempotency protections to prevent duplicate recent work, while manual `Scrape now` is force-triggered for deterministic testing.
