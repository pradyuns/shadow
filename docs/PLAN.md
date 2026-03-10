# Competitor Intelligence Monitor — Complete Implementation Plan

## Context

This plan provides a detailed, step-by-step implementation blueprint for building a distributed competitor monitoring system from scratch. The system continuously monitors competitor URLs (pricing pages, changelogs, homepages, job pages), detects meaningful changes via diffing and AI-powered classification, and delivers alerts to users via Slack and email. The project is greenfield (empty git repo at `/Users/prad/shadow/`).

---

## 1. System Architecture

### High-Level Architecture (Component Diagram)

The system consists of nine distinct runtime components connected through three data stores and two message/event pathways.

**Components:**

1. **React Frontend (SPA)** — Served as static assets by an Nginx container on port 3000. Communicates exclusively with the FastAPI backend over HTTP REST. Renders the dashboard showing monitored URLs, alert feed, historical diffs, and user settings.

2. **FastAPI Backend** — Python ASGI server running under Uvicorn on port 8000. Exposes all REST endpoints. Handles authentication (JWT), CRUD for monitors and users, reads alert history, and dispatches Celery tasks. Connects to PostgreSQL (via SQLAlchemy async engine) and MongoDB (via Motor async driver). Publishes tasks to the Redis broker.

3. **Celery Worker (scraper)** — One or more worker processes consuming tasks from the Redis broker. Runs Playwright browser instances for JS-rendered pages and httpx for static pages. Writes raw HTML snapshots and extracted text to MongoDB. Publishes follow-up diff tasks upon completion.

4. **Celery Worker (analysis)** — Separate worker pool (different queue) that runs diffing, noise filtering, Claude API classification, and notification dispatch. This separation prevents heavy Playwright processes from starving lighter analysis work.

5. **Celery Beat** — Single-instance scheduler that fires the periodic scrape-cycle task every 6 hours. Also fires daily digest aggregation and weekly cleanup tasks.

6. **Redis** — Serves three roles: (a) Celery message broker (db 0), (b) Celery result backend (db 1), (c) application cache for rate-limit counters, deduplication locks, and temporary scrape state (db 2).

7. **PostgreSQL** — Stores all structured relational data: users, monitored URLs, notification preferences, alert metadata, API keys, and audit logs.

8. **MongoDB** — Stores all large unstructured documents: raw HTML snapshots, extracted plain-text versions, computed diff payloads, Claude analysis results, and historical change records.

9. **Flower** — Celery monitoring dashboard on port 5555. Read-only visibility into task queues, worker status, and task history.

### Connection Map

```
React Frontend --(HTTP REST, port 8000)--> FastAPI Backend
FastAPI Backend --(async, SQLAlchemy)--> PostgreSQL (port 5432)
FastAPI Backend --(async, Motor)--> MongoDB (port 27017)
FastAPI Backend --(task dispatch, redis-py)--> Redis (port 6379, db 0)
FastAPI Backend --(cache reads/writes)--> Redis (port 6379, db 2)
Celery Beat --(periodic task messages)--> Redis (port 6379, db 0)
Redis (db 0) --(task delivery)--> Celery Worker (scraper)
Redis (db 0) --(task delivery)--> Celery Worker (analysis)
Celery Worker (scraper) --(sync, SQLAlchemy)--> PostgreSQL
Celery Worker (scraper) --(sync, PyMongo)--> MongoDB
Celery Worker (scraper) --(HTTP, Playwright/httpx)--> External competitor URLs
Celery Worker (scraper) --(publishes follow-up tasks)--> Redis (db 0)
Celery Worker (analysis) --(sync, SQLAlchemy)--> PostgreSQL
Celery Worker (analysis) --(sync, PyMongo)--> MongoDB
Celery Worker (analysis) --(HTTP)--> Claude API (api.anthropic.com)
Celery Worker (analysis) --(HTTP)--> Slack Webhook URL
Celery Worker (analysis) --(HTTP)--> SendGrid API (api.sendgrid.com)
Celery Worker (scraper/analysis) --(result storage)--> Redis (port 6379, db 1)
Flower --(broker inspection)--> Redis (port 6379, db 0)
```

### Request Flows

#### (a) User Creates a Monitor

1. **[Sync]** User fills the "Add Monitor" form in React, submitting URL, page type, scrape frequency override, notification preferences.
2. **[Sync]** React sends `POST /api/v1/monitors` with JWT in the Authorization header.
3. **[Sync]** FastAPI validates the request body via Pydantic (URL format only — no reachability check at creation time; the initial async scrape determines reachability). Checks the user has not exceeded their monitor limit.
4. **[Sync]** FastAPI inserts a row into `monitors` table in PostgreSQL with `status = 'pending'` and computes `next_check_at = NOW()`. Returns the created monitor with its ID and `last_scrape_status = 'pending'`.
5. **[Async]** FastAPI dispatches a Celery task `scrape_single_url` for the newly created monitor so the first snapshot is captured immediately.
6. **[Sync]** React receives the 201 response and shows the new monitor in the list with status indicator reflecting `last_scrape_status` (pending → running → success/failed).

#### (b) Scheduled Scrape Cycle

1. **[Async]** Celery Beat fires `initiate_scrape_cycle` task every 6 hours (configurable).
2. **[Async]** `initiate_scrape_cycle` queries PostgreSQL: `SELECT * FROM monitors WHERE is_active = true AND next_check_at <= NOW()`. Groups results into batches of configurable size (e.g., 20).
3. **[Async]** For each batch, it creates a Celery `group` of `scrape_single_url` tasks. Each group is dispatched to the `scraper` queue. A `chord` is used so that when all scrapes in a batch complete, a `batch_complete_callback` task fires.
4. **[Async]** Each `scrape_single_url` task: (i) fetches the page via httpx or Playwright based on the monitor's `render_js` flag, (ii) stores raw HTML in MongoDB `snapshots` collection, (iii) extracts plain text using BeautifulSoup and stores it in MongoDB, (iv) dispatches `compute_diff` task to the `analysis` queue.

#### (c) Diffing Pipeline

1. **[Async]** `compute_diff` task receives the monitor ID and the new snapshot ID.
2. It retrieves the previous snapshot's extracted text from MongoDB (the most recent prior to this one).
3. If no previous snapshot exists (first scrape), it marks the snapshot as "baseline" and exits.
4. It runs `difflib.unified_diff` on the two text versions, producing a structured diff.
5. It applies the noise filter: removes lines matching regex patterns for timestamps, session tokens, ad IDs, cache-busting parameters, build hashes, and other configured noise patterns (stored per-monitor and globally).
6. If the filtered diff is empty (all changes were noise), it updates the snapshot status to "no_significant_change" in MongoDB and exits.
7. If meaningful diff content remains, it stores the diff payload in MongoDB `diffs` collection and dispatches `classify_significance` to the `analysis` queue.

#### (d) Significance Classification via Claude

1. **[Async]** `classify_significance` receives the diff ID.
2. It loads the diff payload from MongoDB, the monitor metadata from PostgreSQL (competitor name, page type).
3. It constructs a Claude API request with a system prompt explaining the classification task and a user message containing the diff, truncated to a configurable max token budget (e.g., 4000 tokens of diff context).
4. It calls `anthropic.Client().messages.create()` with structured output (Pydantic model) requesting: `significance_level` (enum: critical, high, medium, low, noise), `summary` (string, max 200 words), `categories` (list from predefined set: pricing_change, feature_launch, feature_removal, hiring_signal, messaging_change, partnership, technical_change, other).
5. It stores the Claude response in MongoDB `analyses` collection.
6. It creates an alert record in PostgreSQL `alerts` table with severity, summary, and foreign keys to the monitor and user.
7. If `significance_level` is medium or above (configurable per user), it dispatches `send_notifications` to the `analysis` queue.

#### (e) Alert Delivery

1. **[Async]** `send_notifications` receives the alert ID.
2. It loads the alert from PostgreSQL, the user's notification preferences, and the analysis summary from MongoDB.
3. For each enabled channel:
   - **Slack**: Constructs a Block Kit message with the competitor name, change summary, severity badge, and a link to the dashboard. POSTs to the user's configured Slack webhook URL.
   - **Email**: Constructs an HTML email using a Jinja2 template. Sends via SendGrid API with the user's email as recipient.
4. Updates the alert record in PostgreSQL with `notified_at` timestamp and delivery status per channel.
5. If any delivery fails, retries with exponential backoff (max 3 retries). After final failure, marks the channel delivery as "failed" and logs the error.

### Sync vs Async Summary

| Step | Sync/Async | Why |
|------|-----------|-----|
| REST API request handling | Sync (from user's perspective) | User waits for response |
| Database reads/writes in API | Async (asyncio) | Non-blocking I/O via async drivers |
| Scraping | Async (Celery task) | Long-running, may take 5-30 seconds per page |
| Diffing | Async (Celery task) | CPU-bound work, decoupled from scraping |
| Claude classification | Async (Celery task) | External API call, 2-10 second latency |
| Notification delivery | Async (Celery task) | External API calls, may fail/retry |

### State Machine

Every monitor and scrape run follows explicit status transitions:

**Monitor Status** (`last_scrape_status`):
```
pending → running → success → (next cycle) → running → success/failed
                  → failed → (retry) → running → success/failed
```

**Snapshot Status** (stored in MongoDB `snapshots.status`):
```
pending → fetched → extracted → baseline (first snapshot)
                              → no_change (text_hash matches previous)
                              → diffed → noise_only (all changes filtered)
                                       → changed → classified → notified
                              → error
```

**Alert Status**:
```
created → notified → acknowledged
       → notification_failed → retried → notified
```

These statuses drive the UI, debugging, and retry logic. The frontend reads `last_scrape_status` directly from the monitor record to show real-time state.

### Playwright Browser Lifecycle

The Playwright browser is managed as a module-level singleton in `playwright_scraper.py`:

1. **Initialization**: Browser launched lazily on first `scrape_single_url` task. Stored in module-level `_browser` variable.
2. **Per-task lifecycle**: Each scrape opens a new `page`, navigates, extracts content, then closes the page. The browser persists across tasks.
3. **Restart policy**: `worker_max_tasks_per_child = 100` — worker process recycled after 100 tasks, which kills and re-launches the browser. This prevents memory leaks.
4. **Crash recovery**: If `_browser.is_connected()` returns `False` (browser crashed or was killed), the singleton is re-created on the next task invocation. A `try/except` around every browser operation catches `PlaywrightError` and attempts browser restart before retry.
5. **Graceful shutdown**: Worker `SIGTERM` handler calls `_browser.close()` to clean up Chromium processes.
6. **Resource blocking**: Browser context created with `route("**/*.{png,jpg,gif,svg,css,woff,woff2}", lambda route: route.abort())` to block images, fonts, and CSS for faster scrapes and lower memory.

---

## 2. Full Folder and File Structure

```
/Users/prad/shadow/
|
|-- README.md
|-- .gitignore
|-- .env.example
|-- docker-compose.yml
|-- docker-compose.prod.yml
|-- Makefile
|
|-- .github/
|   |-- workflows/
|   |   |-- ci.yml                         # Main CI pipeline: lint, test, build, push
|   |   |-- deploy.yml                     # CD pipeline: deploy on tag/release
|   |-- CODEOWNERS
|   |-- pull_request_template.md
|
|-- backend/
|   |-- Dockerfile                         # Multi-stage: builder + runtime
|   |-- pyproject.toml                     # Project metadata, dependencies
|   |-- poetry.lock
|   |-- alembic.ini
|   |-- pytest.ini
|   |-- .flake8
|   |-- mypy.ini
|   |
|   |-- alembic/
|   |   |-- env.py                         # Alembic environment setup
|   |   |-- versions/
|   |       |-- 001_initial_schema.py
|   |
|   |-- app/
|   |   |-- __init__.py
|   |   |-- main.py                        # FastAPI app factory, middleware, lifespan events
|   |   |-- config.py                      # Pydantic BaseSettings, reads all env vars
|   |   |
|   |   |-- db/
|   |   |   |-- __init__.py
|   |   |   |-- postgres.py               # Async SQLAlchemy engine, session factory, dependency
|   |   |   |-- postgres_sync.py          # Sync SQLAlchemy engine for Celery workers
|   |   |   |-- mongodb.py                # Motor async client, database/collection accessors
|   |   |   |-- mongodb_sync.py           # PyMongo sync client for Celery workers
|   |   |   |-- redis.py                  # Redis connection pool, cache helper functions
|   |   |
|   |   |-- models/
|   |   |   |-- __init__.py
|   |   |   |-- base.py                   # SQLAlchemy declarative base, common mixins
|   |   |   |-- user.py                   # User ORM model
|   |   |   |-- monitor.py               # Monitor ORM model
|   |   |   |-- alert.py                 # Alert ORM model
|   |   |   |-- notification_setting.py  # NotificationSetting ORM model
|   |   |   |-- api_key.py              # APIKey ORM model
|   |   |
|   |   |-- schemas/
|   |   |   |-- __init__.py
|   |   |   |-- user.py                   # UserCreate, UserRead, UserUpdate
|   |   |   |-- monitor.py               # MonitorCreate, MonitorRead, MonitorUpdate, MonitorList
|   |   |   |-- alert.py                 # AlertRead, AlertList, AlertDetail
|   |   |   |-- notification.py          # NotificationSettingCreate, NotificationSettingUpdate
|   |   |   |-- snapshot.py              # SnapshotRead
|   |   |   |-- diff.py                  # DiffRead, DiffDetail
|   |   |   |-- analysis.py             # AnalysisRead
|   |   |   |-- common.py               # PaginatedResponse, ErrorResponse, HealthResponse
|   |   |   |-- auth.py                 # TokenPair, LoginRequest, RegisterRequest
|   |   |
|   |   |-- api/
|   |   |   |-- __init__.py
|   |   |   |-- deps.py                  # Shared dependencies: get_current_user, get_db
|   |   |   |-- v1/
|   |   |       |-- __init__.py
|   |   |       |-- router.py            # Aggregates all v1 sub-routers
|   |   |       |-- auth.py              # POST /auth/register, /auth/login, /auth/refresh
|   |   |       |-- users.py             # GET/PATCH /users/me
|   |   |       |-- monitors.py          # CRUD for monitors
|   |   |       |-- alerts.py            # GET /alerts, GET /alerts/{id}, PATCH acknowledge
|   |   |       |-- snapshots.py         # GET /monitors/{id}/snapshots, GET /snapshots/{id}
|   |   |       |-- diffs.py             # GET /monitors/{id}/diffs, GET /diffs/{id}
|   |   |       |-- notifications.py     # CRUD for notification settings
|   |   |       |-- admin.py             # Admin: trigger scrape cycle, system stats
|   |   |       |-- health.py            # GET /health, GET /health/ready
|   |   |
|   |   |-- services/
|   |   |   |-- __init__.py
|   |   |   |-- auth_service.py          # JWT creation/validation, password hashing
|   |   |   |-- user_service.py          # User CRUD business logic
|   |   |   |-- monitor_service.py       # Monitor CRUD, validation, limit enforcement
|   |   |   |-- alert_service.py         # Alert queries, acknowledgment, filtering
|   |   |   |-- snapshot_service.py      # MongoDB snapshot queries, pagination
|   |   |   |-- diff_service.py          # MongoDB diff queries
|   |   |   |-- analysis_service.py      # MongoDB analysis queries
|   |   |
|   |   |-- middleware/
|   |   |   |-- __init__.py
|   |   |   |-- cors.py                  # CORS configuration
|   |   |   |-- rate_limit.py            # Rate limiting middleware using Redis
|   |   |   |-- request_logging.py       # Structured request/response logging
|   |   |   |-- error_handler.py         # Global exception handlers
|   |   |
|   |   |-- utils/
|   |       |-- __init__.py
|   |       |-- security.py             # Password hashing, JWT encode/decode helpers
|   |       |-- pagination.py           # Pagination parameter parsing, response building
|   |       |-- validators.py           # URL validation, custom Pydantic validators
|   |       |-- time_utils.py           # UTC now, timezone helpers
|   |
|   |-- workers/
|   |   |-- __init__.py
|   |   |-- celery_app.py               # Celery app factory, broker/backend config
|   |   |-- celery_config.py            # Queues, routes, rate limits, serializer
|   |   |
|   |   |-- tasks/
|   |   |   |-- __init__.py
|   |   |   |-- scraping.py             # initiate_scrape_cycle, scrape_single_url
|   |   |   |-- diffing.py              # compute_diff
|   |   |   |-- analysis.py             # classify_significance
|   |   |   |-- notifications.py        # send_notifications, send_slack, send_email
|   |   |   |-- maintenance.py          # cleanup_old_snapshots, cleanup_deleted_monitors, aggregate_daily_digest
|   |   |
|   |   |-- scraper/
|   |   |   |-- __init__.py
|   |   |   |-- base.py                 # Abstract BaseScraper class
|   |   |   |-- http_scraper.py         # httpx-based scraper for static pages
|   |   |   |-- playwright_scraper.py   # Playwright-based scraper for JS-rendered pages
|   |   |   |-- scraper_factory.py      # Factory returning correct scraper based on config
|   |   |   |-- text_extractor.py       # BeautifulSoup HTML to clean text extraction
|   |   |   |-- noise_filter.py         # Regex-based noise removal
|   |   |
|   |   |-- differ/
|   |   |   |-- __init__.py
|   |   |   |-- text_differ.py          # difflib-based text diffing
|   |   |   |-- diff_formatter.py       # Formats raw diff into structured payload
|   |   |
|   |   |-- classifier/
|   |   |   |-- __init__.py
|   |   |   |-- claude_client.py        # Anthropic SDK wrapper, retry logic, cost tracking
|   |   |   |-- prompts.py              # System and user prompt templates
|   |   |   |-- schemas.py              # Pydantic models for Claude structured output
|   |   |
|   |   |-- notifier/
|   |       |-- __init__.py
|   |       |-- base.py                 # Abstract BaseNotifier
|   |       |-- slack_notifier.py       # Slack webhook message construction and delivery
|   |       |-- email_notifier.py       # SendGrid email construction and delivery
|   |       |-- notifier_factory.py     # Returns correct notifier(s) based on user prefs
|   |       |-- templates/
|   |           |-- alert_email.html    # Jinja2 HTML email template
|   |           |-- alert_email.txt     # Plain text fallback
|   |           |-- digest_email.html   # Daily digest template
|   |
|   |-- tests/
|       |-- __init__.py
|       |-- conftest.py                 # Shared fixtures: test DB, test client, mock factories
|       |-- factories.py               # Factory Boy factories
|       |
|       |-- unit/
|       |   |-- __init__.py
|       |   |-- test_noise_filter.py
|       |   |-- test_text_extractor.py
|       |   |-- test_text_differ.py
|       |   |-- test_diff_formatter.py
|       |   |-- test_claude_client.py
|       |   |-- test_prompts.py
|       |   |-- test_slack_notifier.py
|       |   |-- test_email_notifier.py
|       |   |-- test_auth_service.py
|       |   |-- test_validators.py
|       |   |-- test_schemas.py
|       |
|       |-- integration/
|       |   |-- __init__.py
|       |   |-- test_auth_api.py
|       |   |-- test_monitors_api.py
|       |   |-- test_alerts_api.py
|       |   |-- test_scraping_task.py
|       |   |-- test_diffing_task.py
|       |   |-- test_analysis_task.py
|       |   |-- test_notification_task.py
|       |   |-- test_full_pipeline.py
|       |
|       |-- fixtures/
|           |-- sample_html/
|           |   |-- pricing_page_v1.html
|           |   |-- pricing_page_v2.html     # Same page with price change
|           |   |-- changelog_v1.html
|           |   |-- changelog_v2.html        # Same page with new entry
|           |   |-- noisy_page_v1.html       # Page with timestamps, ads
|           |   |-- noisy_page_v2.html       # Same page, only noise changed
|           |   |-- js_rendered_page.html
|           |-- expected_diffs/
|           |   |-- pricing_diff.json
|           |   |-- changelog_diff.json
|           |-- mock_responses/
|               |-- claude_critical.json
|               |-- claude_low.json
|               |-- claude_noise.json
|
|-- frontend/
|   |-- Dockerfile                         # Multi-stage: Node build + Nginx serve
|   |-- nginx.conf                         # Nginx config for SPA routing, API proxy
|   |-- package.json
|   |-- package-lock.json
|   |-- tsconfig.json
|   |-- tailwind.config.js
|   |-- postcss.config.js
|   |-- vite.config.ts
|   |-- index.html
|   |-- .eslintrc.cjs
|   |-- .prettierrc
|   |
|   |-- public/
|   |   |-- favicon.ico
|   |   |-- logo.svg
|   |
|   |-- src/
|   |   |-- main.tsx                       # React entry point, router setup
|   |   |-- App.tsx                        # Root component, layout wrapper
|   |   |-- index.css                      # Tailwind base imports
|   |   |
|   |   |-- api/
|   |   |   |-- client.ts                  # Axios instance, interceptors, JWT refresh
|   |   |   |-- auth.ts                    # login(), register(), refreshToken()
|   |   |   |-- monitors.ts               # CRUD for monitors
|   |   |   |-- alerts.ts                 # getAlerts(), getAlertDetail(), acknowledgeAlert()
|   |   |   |-- snapshots.ts
|   |   |   |-- diffs.ts
|   |   |   |-- notifications.ts
|   |   |   |-- types.ts                  # TypeScript interfaces matching backend schemas
|   |   |
|   |   |-- hooks/
|   |   |   |-- useAuth.ts
|   |   |   |-- useMonitors.ts
|   |   |   |-- useAlerts.ts
|   |   |   |-- usePagination.ts
|   |   |
|   |   |-- contexts/
|   |   |   |-- AuthContext.tsx
|   |   |
|   |   |-- pages/
|   |   |   |-- LoginPage.tsx
|   |   |   |-- RegisterPage.tsx
|   |   |   |-- DashboardPage.tsx          # Overview: recent alerts, monitor status summary
|   |   |   |-- MonitorsPage.tsx           # List all monitors, add/edit/delete
|   |   |   |-- MonitorDetailPage.tsx      # Single monitor: snapshots, diffs, alerts
|   |   |   |-- AlertsPage.tsx             # Alert feed with filtering
|   |   |   |-- AlertDetailPage.tsx        # Full analysis, diff view
|   |   |   |-- SettingsPage.tsx           # User profile, notification preferences
|   |   |   |-- NotFoundPage.tsx
|   |   |
|   |   |-- components/
|   |   |   |-- layout/
|   |   |   |   |-- Sidebar.tsx
|   |   |   |   |-- Header.tsx
|   |   |   |   |-- MainLayout.tsx
|   |   |   |
|   |   |   |-- monitors/
|   |   |   |   |-- MonitorCard.tsx
|   |   |   |   |-- MonitorForm.tsx
|   |   |   |   |-- MonitorList.tsx
|   |   |   |   |-- MonitorStatusBadge.tsx
|   |   |   |
|   |   |   |-- alerts/
|   |   |   |   |-- AlertCard.tsx
|   |   |   |   |-- AlertFeed.tsx
|   |   |   |   |-- AlertFilters.tsx
|   |   |   |   |-- SeverityBadge.tsx
|   |   |   |
|   |   |   |-- diffs/
|   |   |   |   |-- DiffViewer.tsx         # Side-by-side or unified diff renderer
|   |   |   |   |-- DiffSummary.tsx        # Claude analysis summary display
|   |   |   |
|   |   |   |-- common/
|   |   |       |-- Button.tsx
|   |   |       |-- Input.tsx
|   |   |       |-- Modal.tsx
|   |   |       |-- Pagination.tsx
|   |   |       |-- LoadingSpinner.tsx
|   |   |       |-- EmptyState.tsx
|   |   |       |-- ErrorBoundary.tsx
|   |   |       |-- Toast.tsx
|   |   |
|   |   |-- utils/
|   |       |-- formatDate.ts
|   |       |-- classNames.ts
|   |       |-- constants.ts
|   |
|   |-- tests/
|       |-- setup.ts
|       |-- components/
|       |-- pages/
|       |-- api/
|
|-- scripts/
    |-- init_mongo.js                      # MongoDB initialization: create collections, indexes
    |-- seed_data.py                       # Seed script for development data
    |-- run_migration.sh                   # Wrapper script to run Alembic migrations
    |-- healthcheck.sh                     # Docker health check script
```

---

## 3. Database Design

### PostgreSQL Schema

**Rationale**: Users, monitors, alerts, and notification settings are relational data with foreign key relationships, require ACID transactions (e.g., creating a monitor and its notification settings atomically), benefit from structured queries (filter alerts by severity, date, user), and have fixed schemas.

#### Table: `users`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL | Login identifier |
| `password_hash` | `VARCHAR(255)` | NOT NULL | bcrypt hash |
| `full_name` | `VARCHAR(255)` | NOT NULL | Display name |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | Soft disable |
| `is_admin` | `BOOLEAN` | NOT NULL, DEFAULT FALSE | Admin privileges |
| `max_monitors` | `INTEGER` | NOT NULL, DEFAULT 50 | Per-user monitor limit |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Auto-updated via trigger |

**Indexes**: `idx_users_email` UNIQUE on `email`, `idx_users_is_active` on `is_active`.

#### Table: `monitors`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | |
| `user_id` | `UUID` | FK -> users(id) ON DELETE CASCADE, NOT NULL | Owner |
| `url` | `TEXT` | NOT NULL | Competitor page URL |
| `name` | `VARCHAR(255)` | NOT NULL | Human-friendly label |
| `competitor_name` | `VARCHAR(255)` | NULL | Optional competitor label |
| `page_type` | `VARCHAR(50)` | NOT NULL, CHECK IN ('pricing', 'changelog', 'homepage', 'jobs', 'blog', 'docs', 'other') | |
| `render_js` | `BOOLEAN` | NOT NULL, DEFAULT FALSE | Whether to use Playwright |
| `check_interval_hours` | `INTEGER` | NOT NULL, DEFAULT 6 | Custom scrape frequency |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | Paused monitors skip scraping |
| `next_check_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | When the next scrape should occur. Updated after each scrape to `NOW() + check_interval_hours` |
| `last_checked_at` | `TIMESTAMPTZ` | NULL | Last successful scrape timestamp |
| `last_scrape_status` | `VARCHAR(20)` | NOT NULL, DEFAULT 'pending', CHECK IN ('pending', 'running', 'success', 'failed') | Current/last scrape run status |
| `last_scrape_error` | `TEXT` | NULL | Error message from last failed scrape |
| `last_snapshot_id` | `VARCHAR(24)` | NULL | MongoDB ObjectId of the most recent snapshot |
| `last_change_at` | `TIMESTAMPTZ` | NULL | Last significant change detected |
| `consecutive_failures` | `INTEGER` | NOT NULL, DEFAULT 0 | Error tracking |
| `noise_patterns` | `JSONB` | NOT NULL, DEFAULT '[]' | Custom noise filter regex list |
| `css_selector` | `TEXT` | NULL | Optional: scrape only this CSS selector |
| `deleted_at` | `TIMESTAMPTZ` | NULL | Soft delete timestamp. Non-null means deleted |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | |

**Indexes**: `idx_monitors_user_id` on `user_id`, `idx_monitors_is_active` on `is_active`, `idx_monitors_next_check` on `(is_active, next_check_at)` for scheduling (`WHERE is_active = true AND deleted_at IS NULL AND next_check_at <= NOW()`), `idx_monitors_url` on `url`, `idx_monitors_last_scrape_status` on `last_scrape_status`, `idx_monitors_deleted_at` on `deleted_at` (partial index where `deleted_at IS NOT NULL` for cleanup queries).

**Constraint**: `UNIQUE(user_id, url)` — a user cannot monitor the same URL twice.

#### Table: `alerts`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | |
| `monitor_id` | `UUID` | FK -> monitors(id) ON DELETE CASCADE, NOT NULL | |
| `user_id` | `UUID` | FK -> users(id) ON DELETE CASCADE, NOT NULL | Denormalized for query speed |
| `severity` | `VARCHAR(20)` | NOT NULL, CHECK IN ('critical', 'high', 'medium', 'low') | From Claude classification |
| `summary` | `TEXT` | NOT NULL | Human-readable change summary |
| `categories` | `JSONB` | NOT NULL, DEFAULT '[]' | Change categories from Claude |
| `diff_id` | `VARCHAR(24)` | NOT NULL | MongoDB ObjectId reference to diffs collection |
| `analysis_id` | `VARCHAR(24)` | NOT NULL | MongoDB ObjectId reference to analyses collection |
| `is_acknowledged` | `BOOLEAN` | NOT NULL, DEFAULT FALSE | User dismissed |
| `acknowledged_at` | `TIMESTAMPTZ` | NULL | |
| `notified_via_slack` | `BOOLEAN` | NOT NULL, DEFAULT FALSE | |
| `notified_via_email` | `BOOLEAN` | NOT NULL, DEFAULT FALSE | |
| `notified_at` | `TIMESTAMPTZ` | NULL | |
| `notification_error` | `TEXT` | NULL | Last delivery error message |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | |

**Indexes**: `idx_alerts_user_id_created_at` on `(user_id, created_at DESC)` for feed queries, `idx_alerts_monitor_id` on `monitor_id`, `idx_alerts_severity` on `severity`, `idx_alerts_is_acknowledged` on `(user_id, is_acknowledged)` for filtering unread.

#### Table: `notification_settings`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | |
| `user_id` | `UUID` | FK -> users(id) ON DELETE CASCADE, NOT NULL | |
| `channel` | `VARCHAR(20)` | NOT NULL, CHECK IN ('slack', 'email') | |
| `is_enabled` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | |
| `min_severity` | `VARCHAR(20)` | NOT NULL, DEFAULT 'medium', CHECK IN ('critical', 'high', 'medium', 'low') | Only alert at this level or above |
| `slack_webhook_url` | `TEXT` | NULL | Required when channel = 'slack' |
| `email_address` | `VARCHAR(255)` | NULL | Override email; defaults to user.email |
| `digest_mode` | `BOOLEAN` | NOT NULL, DEFAULT FALSE | Batch alerts into daily digest |
| `digest_hour_utc` | `INTEGER` | NULL, CHECK BETWEEN 0 AND 23 | Hour to send daily digest |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | |

**Indexes**: `idx_notification_settings_user_channel` UNIQUE on `(user_id, channel)`.

#### Table: `api_keys`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | |
| `user_id` | `UUID` | FK -> users(id) ON DELETE CASCADE, NOT NULL | |
| `key_hash` | `VARCHAR(255)` | UNIQUE, NOT NULL | SHA-256 of the API key |
| `key_prefix` | `VARCHAR(8)` | NOT NULL | First 8 chars for identification |
| `name` | `VARCHAR(255)` | NOT NULL | User-given label |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT TRUE | |
| `last_used_at` | `TIMESTAMPTZ` | NULL | |
| `expires_at` | `TIMESTAMPTZ` | NULL | Optional expiration |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | |

**Indexes**: `idx_api_keys_key_hash` UNIQUE on `key_hash`, `idx_api_keys_user_id` on `user_id`.

### MongoDB Collections

**Rationale**: Raw HTML snapshots are large (100KB-2MB each), unstructured, and append-only. Diffs and analysis results are semi-structured JSON documents of varying shape and size. These documents are written once and read occasionally. MongoDB's flexible schema and efficient handling of large documents makes it the right choice. No cross-document transactions or complex joins needed.

#### Collection: `snapshots`

```json
{
  "_id": "ObjectId",
  "monitor_id": "uuid-string",
  "url": "https://competitor.com/pricing",
  "raw_html": "<!DOCTYPE html>...",
  "extracted_text": "Pricing Plans...",
  "text_hash": "sha256-hex-string",
  "http_status": 200,
  "headers": {"content-type": "text/html"},
  "render_method": "playwright | httpx",
  "fetch_duration_ms": 3450,
  "status": "fetched | extracted | baseline | no_change | diffed | changed | classified | notified | error",
  "is_baseline": false,
  "error": "null | error message",
  "created_at": "ISODate"
}
```

**Indexes**:
- `{ monitor_id: 1, created_at: -1 }` — Primary query pattern
- `{ text_hash: 1 }` — Deduplication check
- `{ created_at: 1 }` with TTL of 90 days

#### Collection: `diffs`

```json
{
  "_id": "ObjectId",
  "monitor_id": "uuid-string",
  "snapshot_before_id": "objectid-string",
  "snapshot_after_id": "objectid-string",
  "unified_diff": "--- before\n+++ after\n@@ ...",
  "diff_lines_added": 15,
  "diff_lines_removed": 8,
  "diff_lines_changed": 23,
  "filtered_diff": "...",
  "noise_lines_removed": 42,
  "is_empty_after_filter": false,
  "diff_size_bytes": 2048,
  "created_at": "ISODate"
}
```

**Indexes**:
- `{ monitor_id: 1, created_at: -1 }`
- `{ is_empty_after_filter: 1 }`
- `{ created_at: 1 }` with TTL of 180 days

#### Collection: `analyses`

```json
{
  "_id": "ObjectId",
  "diff_id": "objectid-string",
  "monitor_id": "uuid-string",
  "significance_level": "high",
  "summary": "Competitor raised Enterprise plan price from $99 to $149/mo",
  "categories": ["pricing_change"],
  "claude_model": "claude-sonnet-4-5-20241022",
  "prompt_tokens": 1250,
  "completion_tokens": 180,
  "total_cost_usd": 0.0042,
  "raw_response": {},
  "processing_duration_ms": 2800,
  "needs_review": false,
  "created_at": "ISODate"
}
```

`needs_review` is `true` when Claude output required fallback parsing or defaulted fields. These analyses should surface in an admin queue for manual verification.

**Indexes**:
- `{ monitor_id: 1, created_at: -1 }`
- `{ diff_id: 1 }` unique
- `{ significance_level: 1 }`
- `{ needs_review: 1 }` — for admin review queue
- `{ created_at: 1 }` with TTL of 365 days

#### Collection: `digest_queue`

```json
{
  "_id": "ObjectId",
  "user_id": "uuid-string",
  "alert_ids": ["uuid-1", "uuid-2"],
  "channel": "email",
  "scheduled_for": "ISODate",
  "sent": false,
  "sent_at": null,
  "created_at": "ISODate"
}
```

**Indexes**:
- `{ sent: 1, scheduled_for: 1 }`
- `{ user_id: 1 }`

---

## 4. API Design

### Authentication

JWT-based with access + refresh token pattern. Access tokens expire in 30 minutes, refresh tokens in 7 days. Refresh tokens stored as SHA-256 hash. API keys (hashed, in `api_keys` table) supported for programmatic access via `X-API-Key` header.

### Standardized Error Response

```json
{
  "error": {
    "code": "MONITOR_NOT_FOUND",
    "message": "Monitor with ID abc-123 was not found.",
    "details": null
  }
}
```

HTTP status codes: 400 (validation), 401 (unauthenticated), 403 (forbidden), 404 (not found), 409 (conflict), 422 (unprocessable entity), 429 (rate limited), 500 (internal error).

### Endpoints

#### Auth

**POST /api/v1/auth/register**
- Request: `{ "email": string, "password": string (min 8), "full_name": string }`
- Response 201: `{ "user": { "id", "email", "full_name", "created_at" } }`
- Validation: Email format, password strength, unique email

**POST /api/v1/auth/login**
- Request: `{ "email": string, "password": string }`
- Response 200: `{ "access_token", "refresh_token", "token_type": "bearer", "expires_in": 1800 }`
- Rate limited: 5 attempts/minute per email

**POST /api/v1/auth/refresh**
- Request: `{ "refresh_token": string }`
- Response 200: New token pair

#### Users

**GET /api/v1/users/me** — Current user profile
**PATCH /api/v1/users/me** — Update full_name, password

#### Monitors

**POST /api/v1/monitors**
- Request:
```json
{
  "url": "https://competitor.com/pricing",
  "name": "Competitor X Pricing",
  "competitor_name": "Competitor X",
  "page_type": "pricing",
  "render_js": false,
  "check_interval_hours": 6,
  "css_selector": "#main-content",
  "noise_patterns": ["\\d{10,}"]
}
```
- Response 201: Monitor object + `task_id` for initial scrape
- Validation: Valid URL, user not exceeding max_monitors, unique (user_id, url), valid regex patterns

**GET /api/v1/monitors** — Paginated list with filters: `page`, `per_page`, `is_active`, `page_type`, `search`
**GET /api/v1/monitors/{monitor_id}** — Single monitor
**PATCH /api/v1/monitors/{monitor_id}** — Update any subset of fields
**DELETE /api/v1/monitors/{monitor_id}** — Soft delete (details below)
**POST /api/v1/monitors/{monitor_id}/scrape** — Manually trigger scrape, returns 202 with task_id

**Delete Flow (Soft Delete)**:
- `DELETE` sets `is_active = false` and `deleted_at = NOW()` on the monitor (soft delete). The monitor is excluded from all queries, scrape cycles, and the UI.
- Historical alerts remain in PostgreSQL and are still visible in the alert feed (labeled as "monitor deleted") for audit purposes.
- MongoDB snapshots, diffs, and analyses are NOT immediately deleted. They are preserved for audit and can be referenced by existing alerts.
- A background cleanup task (`cleanup_deleted_monitors`) runs weekly: for monitors where `deleted_at` is older than 30 days, it permanently removes the PostgreSQL row (hard delete with CASCADE) and dispatches an async task to delete all related MongoDB documents.
- A `POST /api/v1/monitors/{monitor_id}/restore` endpoint (within 30 days) allows un-deleting by clearing `deleted_at` and re-activating.

#### Alerts

**GET /api/v1/alerts** — Paginated with filters: `severity`, `monitor_id`, `is_acknowledged`, `since`, `until`
**GET /api/v1/alerts/{alert_id}** — Detail with summary, categories, severity, links to diff/analysis
**PATCH /api/v1/alerts/{alert_id}/acknowledge** — Mark as acknowledged

#### Snapshots

**GET /api/v1/monitors/{monitor_id}/snapshots** — Paginated list (metadata only, no raw HTML)
**GET /api/v1/snapshots/{snapshot_id}** — Full snapshot (raw HTML via `include_html=true` query param)

#### Diffs

**GET /api/v1/monitors/{monitor_id}/diffs** — Paginated with `has_changes` filter
**GET /api/v1/diffs/{diff_id}** — Full diff document

#### Notification Settings

**GET /api/v1/notifications/settings** — All settings for current user
**PUT /api/v1/notifications/settings/{channel}** — Create/update settings for a channel
**POST /api/v1/notifications/test/{channel}** — Send test notification

#### Admin

**POST /api/v1/admin/scrape-cycle** — Manually trigger full scrape cycle (admin only)
**GET /api/v1/admin/stats** — System statistics (admin only)

#### Health

**GET /api/v1/health** — Liveness probe (no auth)
**GET /api/v1/health/ready** — Readiness probe checking Postgres, MongoDB, Redis (no auth)

---

## 5. Celery Design

### Configuration

- Broker: `redis://<REDIS_HOST>:6379/0`
- Result backend: `redis://<REDIS_HOST>:6379/1`
- Serializer: `json`
- `task_acks_late = True` (acknowledge after execution to prevent task loss on crash)
- `worker_prefetch_multiplier = 1` (fair scheduling)

### Queues

1. `default` — Orchestration tasks, maintenance
2. `scraper` — Scraping tasks (heavy, Playwright)
3. `analysis` — Diffing, Claude classification, notifications (lighter, I/O-bound)

Route configuration:
```
workers.tasks.scraping.*  -> scraper queue
workers.tasks.diffing.*   -> analysis queue
workers.tasks.analysis.*  -> analysis queue
workers.tasks.notifications.* -> analysis queue
workers.tasks.maintenance.*   -> default queue
```

### Task Definitions

#### `initiate_scrape_cycle`
- **Does**: Queries active monitors past their check interval. Batches them. Dispatches `chord(group(scrape_single_url tasks), batch_complete_callback)` per batch.
- **Queue**: `default`
- **Retry**: None (Beat will re-fire)
- **Idempotency**: Redis lock `scrape_cycle_lock` with 30-min TTL prevents overlapping cycles

#### `scrape_single_url`
- **Does**: Fetches a single URL, stores snapshot in MongoDB, updates PostgreSQL state, dispatches `compute_diff`
- **State transitions**: Sets monitor `last_scrape_status = 'running'` at task start. On success: sets `last_scrape_status = 'success'`, `last_checked_at = NOW()`, `next_check_at = NOW() + check_interval_hours`, `consecutive_failures = 0`, `last_snapshot_id = <new snapshot>`. On failure: sets `last_scrape_status = 'failed'`, `last_scrape_error = <error message>`, increments `consecutive_failures`. Snapshot `status` progresses through `fetched → extracted`.
- **Queue**: `scraper`
- **Retry**: Max 3, exponential backoff (10s, 30s, 90s). Retry on TimeoutError, ConnectionError, PlaywrightError. No retry on InvalidURLError
- **Rate limit**: `10/m` per worker
- **Idempotency**: Skip if snapshot exists for this monitor within last 30 minutes
- **Timeout**: soft=60s, hard=90s

#### `compute_diff`
- **Does**: Loads latest two snapshots, runs difflib, applies noise filter, stores diff, dispatches `classify_significance` if changes remain
- **Queue**: `analysis`
- **Retry**: Max 2, 5s backoff (DB errors only)
- **Idempotency**: Skip if diff already exists for this `snapshot_after_id`

#### `classify_significance`
- **Does**: Loads diff + monitor metadata, constructs Claude prompt, calls API with structured output, stores analysis, creates alert, dispatches notifications
- **Queue**: `analysis`
- **Retry**: Max 3, exponential backoff (5s, 15s, 45s). Retry on APIConnectionError, RateLimitError, InternalServerError. No retry on AuthenticationError, BadRequestError
- **Rate limit**: `20/m` (Claude API cost control)
- **Idempotency**: Skip if analysis already exists for this `diff_id`

#### `send_notifications`
- **Does**: Loads alert + user preferences. Sends to each enabled channel meeting min_severity. Updates delivery status
- **Queue**: `analysis`
- **Retry**: Max 3, 10s backoff
- **Idempotency**: Skip if `notified_at` already set on alert

#### `send_daily_digest`
- **Does**: Queries pending digests past their scheduled_for time, aggregates alerts, sends consolidated message
- **Queue**: `analysis`
- **Retry**: Max 2, 30s backoff

#### `cleanup_old_snapshots`
- **Does**: Deletes snapshots older than 90 days, orphaned diffs/analyses
- **Queue**: `default`
- **Retry**: None

#### `cleanup_deleted_monitors`
- **Does**: Finds monitors where `deleted_at` is older than 30 days. For each: deletes all related MongoDB documents (snapshots, diffs, analyses by `monitor_id`), then hard-deletes the PostgreSQL row (CASCADE removes alerts, notification_settings).
- **Queue**: `default`
- **Retry**: Max 1 (safe to re-run due to idempotent deletes)

### Celery Beat Schedule

```python
beat_schedule = {
    "scrape-cycle-every-6-hours": {
        "task": "workers.tasks.scraping.initiate_scrape_cycle",
        "schedule": crontab(minute=0, hour="*/6"),  # 00:00, 06:00, 12:00, 18:00 UTC
    },
    "daily-digest": {
        "task": "workers.tasks.notifications.send_daily_digest",
        "schedule": crontab(minute=5, hour="*"),  # Every hour at :05
    },
    "cleanup-old-snapshots-weekly": {
        "task": "workers.tasks.maintenance.cleanup_old_snapshots",
        "schedule": crontab(minute=0, hour=3, day_of_week=0),  # Sundays 03:00 UTC
    },
    "cleanup-deleted-monitors-weekly": {
        "task": "workers.tasks.maintenance.cleanup_deleted_monitors",
        "schedule": crontab(minute=0, hour=4, day_of_week=0),  # Sundays 04:00 UTC
    },
}
```

### Task Composition

```
initiate_scrape_cycle
  └── group(scrape_single_url * N)  [chord with batch_complete_callback]
        └── scrape_single_url
              └── compute_diff  [dispatched via .delay(), NOT chained]
                    └── (if changes) classify_significance
                          └── (if severity meets threshold) send_notifications
```

Tasks are dispatched as independent follow-ups (`.delay()`) rather than Celery chains. This is intentional: if `compute_diff` fails, it should not block or retry `scrape_single_url`. Each task is independently retriable and idempotent.

### Failed Task Handling

1. After all retries exhausted, task marked FAILED in Redis result backend
2. Custom `task_failure` signal handler logs failure with full context
3. For `scrape_single_url` failures: monitor's `consecutive_failures` incremented. After 5 consecutive failures, monitor is auto-paused + admin alert generated
4. Flower dashboard for visibility. Admins can manually retry via Flower or admin API
5. Failed tasks remain in result backend for 7 days (`result_expires = 604800`) for debugging

---

## 6. Scraping and Diff Pipeline

### Decision Logic: HTTP vs Playwright

The `render_js` boolean on each monitor controls the method. Default is `False` (use httpx).

**Auto-detection**: On first scrape, if httpx returns HTML with `<noscript>` tags or very little text content (<100 chars), auto-upgrade to Playwright and set `render_js = True`.

**httpx scraper** (`http_scraper.py`):
- `httpx.AsyncClient` with 30s timeout
- Realistic User-Agent header
- Follows redirects (max 5)

**Playwright scraper** (`playwright_scraper.py`):
- `playwright.sync_api` (Celery workers are sync)
- Headless Chromium, one browser per worker (module-level singleton, reused)
- Navigates with 30s timeout, waits for `networkidle`
- If `css_selector` configured, waits for selector visibility, extracts that element's innerHTML
- Closes page (not browser) after each scrape

### Text Extraction

**Base extraction** (all page types):
1. Parse with BeautifulSoup4 (`html.parser`)
2. Remove `<script>`, `<style>`, `<noscript>`, `<iframe>`, `<svg>` tags
3. Apply `css_selector` if configured
4. `soup.get_text(separator="\n", strip=True)`
5. Normalize whitespace

**Page-type-aware extraction** (future enhancement, architecture prepared):
The `text_extractor.py` module uses a strategy pattern. The base extractor handles all page types initially. Page-type-specific extractors can be registered to produce structured output:

- **Pricing pages** → extract plan names, prices, billing terms, feature lists into structured JSON alongside plain text
- **Jobs pages** → extract job titles, counts per department, locations into structured JSON
- **Changelogs/blogs** → extract new entries only (detect entry boundaries, diff only new entries vs. all-content diff)
- **Homepage** → extract hero copy, CTA text, navigation items

The classifier receives both the plain-text diff AND any structured extraction data, allowing more precise significance assessment. For MVP, all page types use the base extractor; page-type extractors are added incrementally.

### Diff Algorithm

`difflib.unified_diff` on extracted text lines. Chosen because we care about textual content changes, not markup changes. Output structured into a `DiffResult` dataclass with `unified_diff`, `lines_added`, `lines_removed`, `changed_hunks`.

### Noise Filtering

**Global patterns** (applied to all monitors):
- Timestamps: `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}`, epoch timestamps `\d{10,13}`
- Cache-busting hashes: `[a-f0-9]{8,32}` in asset URLs
- Session/CSRF tokens: `csrf[_-]?token`, `session[_-]?id`
- Tracking: `utm_`, `fbclid`, `gclid`
- Ads: `ad-slot`, `google_ad`, `doubleclick`
- Build IDs: `bundle\.[a-f0-9]+\.js`, `chunk-[a-f0-9]+`
- Copyright year: `©\s*\d{4}`, `Copyright\s+\d{4}`
- Cookie banner/consent manager IDs

**Per-monitor custom patterns**: Stored in `monitors.noise_patterns` JSONB column.

**Filter process**:
1. Parse unified diff into hunks
2. For each changed line, check if the ONLY difference from its counterpart is noise
3. Remove hunks where ALL changed lines are noise
4. Reassemble filtered diff
5. Record `noise_lines_removed` count

### Claude Payload Construction (Cost Control)

1. **Truncation**: Filtered diff truncated to 4000 tokens (~16,000 chars). Truncated diffs get a prepended note
2. **Context enrichment**: Include `competitor_name`, `page_type`, `url`
3. **Structured output**: Pydantic model via Anthropic SDK guarantees response shape
4. **Model selection**: Use cost-effective model (Sonnet) for classification
5. **Rate limit**: 20 calls/minute globally

### Claude Prompt Design

**System prompt**: Instructs Claude to act as competitive intelligence analyst. Defines significance levels (critical/high/medium/low/noise) with examples. Defines change categories. Requests concise summary (max 200 words).

**User prompt**: Contains competitor_name, page_type, URL, timestamp, and filtered diff in fenced code block.

**Response model** (Pydantic):
- `significance_level`: enum (critical, high, medium, low, noise)
- `summary`: string (max 1000 chars)
- `categories`: list of enum values (min 1)

### Claude Output Resilience

The Anthropic SDK's structured output (tool use) mode significantly reduces parsing failures, but the `claude_client.py` must handle edge cases:

1. **Malformed output**: If the SDK raises a `ValidationError` parsing the response into the Pydantic model, retry once with a modified prompt appending "Please respond using the exact JSON schema provided."
2. **Missing fields**: The Pydantic model uses defaults where safe (`categories` defaults to `["other"]`, `summary` defaults to "Classification failed — manual review required"). If `significance_level` is missing after retry, default to `"medium"` and flag the analysis as `needs_review = True`.
3. **Schema mismatch retry**: If the response contains unrecognized enum values (e.g., significance level not in the defined set), map to the closest known value or default to `"medium"`.
4. **Fallback parsing**: If structured output fails entirely after retries, attempt regex-based extraction from the raw text response (look for keywords like "critical", "pricing_change", etc.).
5. **Circuit breaker**: If 5 consecutive Claude calls fail with non-retryable errors (AuthenticationError, persistent schema mismatches), pause classification globally and log an admin alert. Diffs queue up for manual review.

---

## 7. Notification Pipeline

### Slack Webhook

1. Construct Block Kit message: header (competitor + severity emoji), section (summary), fields (page type, categories, time), actions ("View Details" button)
2. POST to user's webhook URL
3. Validate: Slack returns "ok" with 200 on success
4. Timeout: 10 seconds

### SendGrid Email

1. Load Jinja2 HTML template with: competitor name, severity, summary, categories, dashboard link, unsubscribe link
2. Render plain-text fallback
3. Send via SendGrid API (`sendgrid` Python library)
4. From: `SENDGRID_FROM_EMAIL` env var
5. Subject: `[{SEVERITY}] Change detected on {competitor_name} - {page_type}`
6. Timeout: 10 seconds

### Alert Deduplication and Suppression

**Deduplication** (prevent duplicate alerts):
1. **Same-content dedup**: If new snapshot `text_hash` matches previous, no diff generated
2. **Same-alert dedup**: Check if alert already exists for this `diff_id` before creation
3. **Notification dedup**: `notified_at` field acts as sent-flag; checked before sending
4. **Digest dedup**: `digest_queue` tracks queued alert IDs; upsert by `user_id` + `scheduled_for`

**Suppression** (prevent alert spam from oscillating pages or similar changes):
5. **Same-summary suppression**: Before creating an alert, check if an alert exists for the same `monitor_id` with a similar normalized summary (lowercase, stripped of numbers/dates) within the last 24 hours. If so, suppress the new alert (store the analysis but skip alert creation).
6. **Severity-based suppression**: Only notify when the new alert's severity exceeds the highest severity of alerts for this monitor in the last 24 hours. E.g., if a "medium" alert was already sent, a new "medium" doesn't trigger notification, but a "high" does.
7. **Oscillation detection**: Track the last N text_hashes per monitor. If the page oscillates between two states (hash A → B → A → B), mark the monitor as `oscillating` and suppress alerts until the pattern breaks. Alert the user once about the oscillation.

### Severity Levels and Preferences

```
severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
```

Alert sent to a channel only if `alert.severity >= setting.min_severity`. `noise`-level changes never generate alerts.

### Digest Mode

When `digest_mode = True`:
1. `send_notifications` adds alert ID to `digest_queue` instead of sending immediately
2. `send_daily_digest` (hourly Beat task) checks for pending digests past `scheduled_for`
3. Aggregates alert summaries, groups by monitor, sends one consolidated message
4. Marks digest as sent

---

## 8. Docker Compose Plan

### Services

| # | Service | Image | Purpose | Ports | Depends On |
|---|---------|-------|---------|-------|------------|
| 1 | `api` | `backend/Dockerfile` | FastAPI server | 8000 | postgres, mongodb, redis |
| 2 | `worker-scraper` | Same as api | Celery scraper workers | — | redis, postgres, mongodb |
| 3 | `worker-analysis` | Same as api | Celery analysis workers | — | redis, postgres, mongodb |
| 4 | `worker-default` | Same as api | Celery orchestration workers | — | redis, postgres, mongodb |
| 5 | `beat` | Same as api | Celery Beat scheduler | — | redis |
| 6 | `flower` | `mher/flower:2.0` | Celery monitoring | 5555 | redis |
| 7 | `frontend` | `frontend/Dockerfile` | React SPA via Nginx | 3000 | — |
| 8 | `postgres` | `postgres:16-alpine` | Relational DB | 5432 | — |
| 9 | `mongodb` | `mongo:7` | Document store | 27017 | — |
| 10 | `redis` | `redis:7-alpine` | Broker/cache | 6379 | — |
| 11 | `migrate` | Same as api | Run Alembic migrations | — | postgres |

### Commands

- `api`: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`
- `worker-scraper`: `celery -A workers.celery_app worker --queues=scraper --concurrency=4 --loglevel=info -n scraper@%h`
- `worker-analysis`: `celery -A workers.celery_app worker --queues=analysis --concurrency=8 --loglevel=info -n analysis@%h`
- `worker-default`: `celery -A workers.celery_app worker --queues=default --concurrency=2 --loglevel=info -n default@%h`
- `beat`: `celery -A workers.celery_app beat --loglevel=info`
- `redis`: `redis-server --appendonly yes`
- `migrate`: `alembic upgrade head` (runs once, restart: no)

### Networks
- `app-network`: Bridge network connecting all services

### Volumes
- `postgres-data` — Persistent PostgreSQL data
- `mongo-data` — Persistent MongoDB data
- `redis-data` — Persistent Redis AOF
- `playwright-browsers` — Cached Playwright browser binaries

### Startup Order
1. `redis`, `postgres`, `mongodb` start first
2. `migrate` after `postgres` healthy (runs and exits)
3. `api`, all workers, `beat` after all datastores healthy
4. `flower` after `redis` healthy
5. `frontend` has no backend dependency

### Local Dev vs Production

**Local** (`docker-compose.yml`): All ports exposed, source code volume mounts with `--reload`, debug log level, single worker per queue, no SSL.

**Production** (`docker-compose.prod.yml`): No DB port exposure, no volume mounts, multiple worker replicas, `LOG_LEVEL=warning`, Gunicorn+Uvicorn, resource limits.

---

## 9. CI/CD Plan

### GitHub Actions: `ci.yml`

Triggers: Push to `main`, `develop`, `feature/*`. PRs to `main`, `develop`.

**Job 1: `lint`**
1. Checkout, set up Python 3.12
2. `pip install -e ".[dev]"`
3. Run flake8, mypy, black --check, isort --check-only on `backend/`
4. Set up Node.js 20, `npm ci` in frontend
5. Run eslint, prettier --check on `frontend/src/`

**Job 2: `test-backend`**
- Sidecar services: postgres:16-alpine, mongo:7, redis:7-alpine
1. Checkout, set up Python 3.12, install deps
2. Install Playwright: `playwright install chromium --with-deps`
3. Set env vars (dummy API keys for all external services)
4. Run Alembic migrations against test DB
5. `pytest --cov=app --cov=workers --cov-report=xml -v`
6. Upload coverage report

**Job 3: `test-frontend`**
1. Checkout, Node.js 20, `npm ci`
2. `npm test -- --coverage --watchAll=false`
3. Upload coverage

**Job 4: `build`** (depends on lint + test-backend + test-frontend)
1. Set up Docker Buildx
2. Log in to ghcr.io
3. Build backend + frontend images
4. Tag: `sha`, `latest` (on main), `develop` (on develop)
5. Push to ghcr.io

### GitHub Actions: `deploy.yml`

Triggers: Tags matching `v*`. Build and push images tagged with version number.

### Secrets
- `GITHUB_TOKEN` (auto-provided for GHCR)
- `ANTHROPIC_API_KEY`, `SENDGRID_API_KEY` (deploy only; tests use mocks with dummy values)

### Branch Strategy
- `main`: Production-ready. Protected. Requires PR + passing CI + review
- `develop`: Integration branch
- `feature/<name>`: Feature branches from develop
- `v*.*.*` tags: Cut from main for releases (semver)

---

## 10. Testing Strategy

### Unit Tests

| Module | Tests |
|--------|-------|
| `noise_filter.py` | Each global pattern filters noise. Custom patterns work. Non-noise preserved. Edge cases: empty input, all-noise, no matches |
| `text_extractor.py` | Strips script/style. Handles malformed HTML. CSS selector extraction. Empty page. Unicode |
| `text_differ.py` | Identical texts → empty diff. Added/removed counts correct. Hunk structure. Very large diffs |
| `diff_formatter.py` | Unified diff parsed into structured output. Line counts accurate |
| `claude_client.py` | Mocked Anthropic client: success parsed, rate limit retry, auth error immediate, timeout, token counting, cost calculation |
| `prompts.py` | Templates render with all variables. Missing variables raise errors. Truncation works |
| `slack_notifier.py` | Block Kit message correct for each severity. Webhook called with right payload. HTTP errors raise |
| `email_notifier.py` | HTML template renders. SendGrid payload correct. Both HTML + text parts |
| `auth_service.py` | Password hash/verify. JWT creation with correct claims. JWT decode + expiration. Refresh rotation |
| `validators.py` | URL validation (HTTP/HTTPS only). Invalid URLs rejected. Edge cases: very long, unicode |
| `schemas.py` | Pydantic validation for each schema. Required fields. Type coercion. Enum validation |

### Integration Tests

| Test File | Coverage |
|-----------|----------|
| `test_auth_api.py` | Register → login → access protected endpoint → refresh token against real test PG |
| `test_monitors_api.py` | CRUD lifecycle, monitor limit enforcement, duplicate URL rejection |
| `test_alerts_api.py` | Listing with pagination, severity/date filters, acknowledgment |
| `test_scraping_task.py` | `scrape_single_url` with mocked httpx returning sample HTML. Snapshot in MongoDB. compute_diff dispatched |
| `test_diffing_task.py` | `compute_diff` with pre-loaded snapshots. Diff output verified. Noise filtering. Baseline detection |
| `test_analysis_task.py` | `classify_significance` with mocked Claude. Analysis in MongoDB, alert in PG, notifications dispatched |
| `test_notification_task.py` | `send_notifications` with mocked Slack/SendGrid. Correct payloads. Dedup verified |
| `test_full_pipeline.py` | End-to-end: create monitor → scrape twice → diff → classify → notify (all external services mocked) |

### Mocking Strategy

| External Service | Approach |
|-----------------|----------|
| Claude API | `unittest.mock.patch` on `anthropic.Client.messages.create`. Canned responses from fixture files |
| Slack | `unittest.mock.patch` on `httpx.Client.post`. Assert webhook URL + Block Kit payload |
| SendGrid | `unittest.mock.patch` on `sendgrid.SendGridAPIClient.send`. Assert Mail object |
| Redis | Real Redis (Docker sidecar in CI). Mock for unit tests not needing Redis |
| PostgreSQL | Real test DB (Docker sidecar). Fresh per session via Alembic. Transaction rollback per test |
| MongoDB | Real test DB (Docker sidecar). Drop + recreate per session |
| Playwright | `unittest.mock.patch` on `playwright.sync_api.sync_playwright`. Canned HTML from fixtures |
| httpx | `pytest-httpx` or `respx` library |

### Fixture Strategy

- **Factory Boy** (`factories.py`): Factories for User, Monitor, Alert, NotificationSetting
- **HTML fixtures** (`tests/fixtures/sample_html/`): Pairs of v1/v2 pages for diff testing
- **Expected outputs** (`tests/fixtures/expected_diffs/`): Pre-computed expected diffs for regression
- **Mock responses** (`tests/fixtures/mock_responses/`): Claude API responses at different severity levels
- **conftest.py**: `db_session`, `mongo_db`, `test_client`, `auth_headers`, `sample_monitor`

### Edge Cases to Test

1. Scraper task exceeds soft_time_limit → graceful handling, error logged, consecutive_failures incremented
2. Same page content scraped twice → text_hash dedup prevents unnecessary diffing
3. Transient network error on first attempt, success on second → retry works
4. Page returns 200 but empty body → extracted text empty, meaningful diff against previous
5. Playwright times out → error handling and fallback
6. Claude API returns 429 → exponential backoff retry
7. Broken/malformed HTML → BeautifulSoup handles gracefully
8. DNS resolution failure, connection refused → proper error classification
9. Two scrape cycles fire simultaneously → Redis lock prevents duplicate work
10. Page completely rewritten → Claude prompt truncation respects token limits
11. Slack returns 403 (invalid webhook) → retry then failure recorded, email sent independently
12. User deletion → cascade cleanup in PG + async MongoDB cleanup task

---

## 11. Build Order

### Milestone 1: Foundation (Days 1-3)

**Deliverable**: Empty scaffold compiles, Docker Compose starts all infra, health check responds.

1. Initialize git repo with `.gitignore`, `.env.example`
2. Create `backend/` with `pyproject.toml` listing all Python dependencies
3. Create `backend/app/config.py` with Pydantic BaseSettings
4. Create `backend/app/main.py` with minimal FastAPI (health endpoints only)
5. Create `backend/Dockerfile` (multi-stage + Playwright deps)
6. Scaffold `frontend/` with Vite + React + TypeScript + Tailwind
7. Create `frontend/Dockerfile` (multi-stage: Node build + Nginx)
8. Create `docker-compose.yml` with all 11 services
9. Create `Makefile` with targets: up, down, build, logs, migrate, test, lint
10. Verify `docker compose up` starts everything and `GET /api/v1/health` returns 200

### Milestone 2: Core Backend (Days 4-8)

**Deliverable**: All DB schemas migrated, all REST endpoints functional, JWT auth working.

1. Create all DB connection modules (`postgres.py`, `postgres_sync.py`, `mongodb.py`, `mongodb_sync.py`, `redis.py`)
2. Create all SQLAlchemy models
3. Set up Alembic, generate initial migration
4. Create all Pydantic schemas
5. Create auth_service.py (JWT, bcrypt)
6. Create API dependencies (get_current_user, get_db)
7. Create all API route files one by one
8. Create middleware (CORS, rate limiting, request logging, error handler)
9. Create service layer modules
10. Wire routers into main.py
11. Create `scripts/init_mongo.js`
12. Test all endpoints via Swagger UI

### Milestone 3: Worker System (Days 9-14)

**Deliverable**: Full pipeline works e2e: scheduled scrape → diff → classify → notify.

1. Create Celery app + config
2. Create scraper modules (base, http, playwright, factory, text_extractor, noise_filter)
3. Create differ modules (text_differ, diff_formatter)
4. Create classifier modules (claude_client, prompts, schemas)
5. Create notifier modules (base, slack, email, factory, templates)
6. Create all Celery task modules
7. Configure Beat schedule
8. Manual e2e test: create monitor → trigger scrape → verify full pipeline

### Milestone 4: Frontend (Days 15-20)

**Deliverable**: Functional React dashboard with auth, monitors, alerts, diffs.

**Landing page approach**: Before building the full dashboard, generate a directory of 3-4 distinct landing page design options using the `frontend-design` skill. Present them for user selection, then build the chosen design as the entry point. The selected design language (colors, typography, spacing, component style) carries through to the dashboard pages.

1. Set up Vite + React + TypeScript + Tailwind
2. Generate landing page design candidates (using `frontend-design` skill), present for selection
3. Build selected landing page design
4. Create API client with Axios + JWT interceptor
5. Create auth context and hooks
6. Create all API modules and TypeScript types
7. Create layout components (matching selected design language)
8. Create common components
9. Create all pages (Login, Register, Dashboard, Monitors, MonitorDetail, Alerts, AlertDetail, Settings)
10. Set up React Router with protected routes
11. Create nginx.conf for SPA routing + API proxy

### Milestone 5: Infrastructure (Days 21-24)

**Deliverable**: CI passes, Docker images build and push, production compose works.

1. Create `.github/workflows/ci.yml` and `deploy.yml`
2. Create linting configs (.flake8, mypy.ini, .eslintrc.cjs, .prettierrc)
3. Create `docker-compose.prod.yml`
4. Create healthcheck scripts
5. Push to GitHub, verify CI

### Milestone 6: Testing & Hardening (Days 25-30)

**Deliverable**: >80% coverage, all edge cases covered, system stable.

1. Create conftest.py + factories.py
2. Write all unit tests
3. Write all integration tests
4. Create HTML fixtures, expected diffs, mock responses
5. Full test suite passing
6. Add structured logging (structlog with JSON)
7. Add metrics tracking
8. Security hardening review
9. Performance test: 500 monitors simulation
10. Create seed_data.py

---

## 12. Operational Concerns

### Logging
- **Library**: `structlog` for structured JSON logging
- **Levels**: ERROR (unrecoverable), WARNING (recoverable/retries), INFO (normal ops), DEBUG (internals)
- **What to log**: Task start/end with duration, API requests, external API calls with timing, scrapes with URL/method/status, all errors with traceback
- **Correlation**: `request_id` propagated through task chains for tracing
- **Output**: JSON to stdout, Docker handles collection

### Metrics / Observability
- Health endpoints: `/api/v1/health` (liveness), `/api/v1/health/ready` (readiness)
- Key metrics: `scrape_duration_seconds`, `scrape_success/failure_total`, `diff_computed_total`, `claude_api_duration_seconds`, `claude_api_tokens_total`, `claude_api_cost_usd_total`, `notification_sent_total`, `api_request_duration_seconds`, `active_monitors_gauge`, `pending_tasks_gauge`
- Flower for Celery monitoring
- For production: Prometheus client + `/metrics` endpoint

### Security
1. **Input validation**: Pydantic schemas. URLs validated against SSRF (reject private IPs: 10.x, 172.16-31.x, 192.168.x, 127.x, ::1, localhost). Reject non-HTTP(S) schemes
2. **Rate limiting**: Redis sliding window. 100 req/min per user, 5 login attempts/min per IP
3. **CORS**: Strict origin whitelist in production
4. **Secrets**: All via env vars, never committed. `.env.example` has placeholders only
5. **SQL injection**: Prevented by SQLAlchemy parameterized queries
6. **XSS**: React escapes output. DiffViewer sanitizes HTML diff content
7. **Auth**: bcrypt (cost 12), HS256 JWTs, refresh token rotation
8. **Regex DoS**: Validate user-provided noise patterns against catastrophic backtracking

### Cost Control

**Playwright**:
- Reuse browser instances across scrapes (per worker singleton)
- 4 concurrent pages per worker (controls memory: ~200-500MB per instance)
- Block unnecessary resources (images, fonts, CSS, media) during scraping
- `worker_max_tasks_per_child = 100` to periodically restart and free leaked memory

**Claude API**:
- Noise filter removes 60-80% of changes before Claude sees them
- Diff truncation to 4000 tokens caps per-request cost
- Use Sonnet (cost-effective) instead of Opus for classification
- Rate limit: 20 calls/minute globally
- Track cost per analysis in MongoDB
- Monthly budget alert: pause classification if exceeded, queue for manual review

### Backup Strategy
- **PostgreSQL**: Daily `pg_dump`, WAL archiving for PITR, monthly restore test
- **MongoDB**: Daily `mongodump`. Lower priority (snapshots reproducible via re-scrape, but analyses should be backed up)
- **Redis**: AOF persistence. Data is ephemeral; loss means in-flight tasks re-dispatched

### Scaling
- **Workers**: `docker compose up --scale worker-scraper=3`
- **Playwright memory**: ~200-500MB per instance × 4 pages × N workers
- **DB pooling**: SQLAlchemy pool per service type. Consider PgBouncer at scale
- **MongoDB sharding**: Not needed <1M docs. Shard on `monitor_id` if needed
- **API**: Uvicorn 4 workers handles hundreds of concurrent requests. Scale with replicas + load balancer
- **Per-domain rate limiting**: Max 1 req/sec per target domain to avoid getting blocked

---

## Critical Files (Implementation Priority)

1. `backend/app/config.py` — Every module depends on this for DB URLs, API keys, feature flags
2. `docker-compose.yml` — Defines entire runtime topology
3. `backend/workers/tasks/scraping.py` — Entry point of the entire pipeline
4. `backend/workers/scraper/noise_filter.py` — Most critical quality gate; determines alert quality and Claude costs
5. `backend/workers/classifier/claude_client.py` — Most complex integration point (structured output, retry, cost tracking)

## Verification

To verify the implementation end-to-end:

1. `docker compose up` — all services start healthy
2. `GET /api/v1/health/ready` returns all dependencies "ok"
3. Register a user, log in, create a monitor for a known URL
4. Trigger manual scrape via `POST /api/v1/monitors/{id}/scrape`
5. Check MongoDB for snapshot, then diff, then analysis
6. Check PostgreSQL for alert record
7. Verify Slack/email notification received
8. Modify the target page, re-scrape, verify diff detected and classified
9. Run `pytest` — all tests pass with >80% coverage
10. Run `docker compose -f docker-compose.prod.yml up` — production config works
