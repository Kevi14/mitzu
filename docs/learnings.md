# Learnings

## Tradeoffs & Decisions

### fetch over axios

**Decision:** Native `fetch` instead of axios for all HTTP calls in the frontend.

**Why (my call):** A recent axios vulnerability and the preference for a lighter bundle footprint.
`fetch` is now first-class in all modern browsers and Node 18+, covers everything needed here
(JSON bodies, auth headers, response interceptors via a thin wrapper), and removes a dependency
entirely. Axios adds ~14KB gzipped for no real gain at this project's scope.

**How it affects the code:** `frontend/src/api/client.ts` wraps native `fetch` with a small
helper that uses `credentials: 'include'` so the httpOnly session cookie is sent automatically —
no manual header needed — and redirects to `/login` on 401. No third-party interceptor abstraction
needed.

---

### FastAPI `StaticFiles` for frontend (vs. S3 + CloudFront)

**Decision:** React is built in a multi-stage Docker build, and `dist/` is copied into the backend image. FastAPI serves it via `StaticFiles` at `/`. Single container, single ECS task.

**Why (my call):** S3 + CloudFront is a full extra Terraform module — S3 bucket, bucket policy, OAC, CloudFront distribution, cache behaviors, ACM cert, CNAME — for the sole job of serving static files. For a project at this scale it's unnecessary overhead. `StaticFiles` handles SPA routing with `html=True` (serves `index.html` for unmatched paths). The only tradeoff is that the backend container is slightly larger and a frontend-only deploy requires rebuilding the full image; at this scale that's a non-issue.

**How it affects the architecture:**
- `backend/Dockerfile` becomes a two-stage build (node → python)
- `docker-compose.yml` drops the separate frontend service; one container serves everything on port 8000
- Terraform `modules/cdn/` is removed entirely
- ALB has a single target group pointing at the backend ECS service

---

### Server-side pipeline graph resolution (vs. client orchestration)

**Decision:** The backend receives the full React Flow node/edge graph and resolves it via topological sort.

**Why:** Keeps analytics logic server-side. The alternative — each frontend node calling its own API endpoint in sequence — would leak business logic to the browser, make filters hard to push down into SQL, and require N round trips per pipeline execution.

---

### Single `trips` table with `data_month` index (vs. Postgres partitioning)

**Decision:** One table with a synthetic `data_month DATE` column and a B-tree index.

**Why:** Table partitioning adds DDL complexity that isn't justified at demo scale (~10–15M rows
per ingested month). The schema is designed so that a partition-per-month migration is
non-breaking if throughput demands it later.

---

### httpOnly cookie for JWT (vs. localStorage)

**Decision:** JWT stored in an `httpOnly`, `SameSite=Strict` session cookie — not localStorage.

**Why (my call):** localStorage is XSS-vulnerable; if any injected script runs in the page,
it can read the token directly. An `httpOnly` cookie is invisible to JavaScript entirely, which
eliminates that surface. `SameSite=Strict` handles CSRF without needing a separate token for
same-origin use.

**How it affects the code:**
- Backend `POST /auth/login` sets `Set-Cookie: mitzu_session=<jwt>; HttpOnly; SameSite=Strict; Path=/`
- Frontend uses `credentials: 'include'` on every `fetch` call — no manual header attachment needed
- Logout clears the cookie server-side (`Set-Cookie` with `Max-Age=0`)
- CORS config must include `allow_credentials=True` and explicit `allow_origins` (not `*`)

---

### Pandas `read_parquet` (full load) + chunked `to_sql` (vs. PyArrow streaming)

**Decision:** Load the full monthly Parquet into a DataFrame, then insert in 10k-row chunks.

**Why:** Simpler code path. January 2024 is ~60MB compressed / ~500MB in memory — well within a
1GB Docker container. PyArrow `iter_batches` would reduce peak memory but adds complexity that
isn't necessary at demo scale.

---

### Recharts + Nivo heatmap (vs. all-one-library)

**Decision:** Recharts for bar/scatter/line, `@nivo/heatmap` for the day-of-week revenue grid.

**Why:** Recharts has a simpler API and smaller bundle for standard chart types. Nivo's heatmap
component is genuinely better — proper color scales, tooltip handling, and responsiveness — and
worth the extra dependency for that one chart type.

---

### Terraform without remote state backend

**Decision:** Local state only — no S3 + DynamoDB backend configured.

**Why:** Remote state requires a pre-existing S3 bucket and DynamoDB table, which would need to
be bootstrapped outside of Terraform (chicken-and-egg). Since no actual deployment is required
by the assignment, the README notes the step to add a backend block before real use.

---

### Backend owns `chart_type` (vs. user config)

**Decision:** `ANALYTIC_CHART_DEFAULTS` in `analytics_executor.py` always wins for `chart_type`. Users can override `x_key`/`y_key` but not chart type.

**Why (my call):** When chart type was user-configurable end-to-end, the executor would echo the user's value back in metadata — defeating its own defaults silently. Centralising the decision in the backend eliminated a whole class of rendering bugs and is consistent with the principle that the frontend is purely a renderer; all analytical decisions live server-side.

---

### `buildNivoData` extracted as a pure function for testability

**Decision:** Heatmap transformation logic lives in a named exported function (`buildNivoData`) rather than inline in the component. Returns a discriminated union `BuildResult` (`ok: true | false`).

**Why:** Inline component logic is untestable without a full DOM render and SVG renderer. Extraction cost is zero (same file, no new module) but enables fast unit tests and documents failure modes explicitly. The `ok: false` path surfaces a human-readable `reason` string directly in the chart — turns a silent "No data" into an actionable message.

---

### Vitest over Jest for frontend tests

**Decision:** Vitest + `@testing-library/react` + jsdom. Nivo mocked at the module boundary.

**Why:** Vitest shares the Vite config — no separate Babel transform, no `moduleNameMapper` for path aliases, native ESM. `@testing-library/react` tests the real component code; mocking `@nivo/heatmap` avoids SVG renderer issues in jsdom while still exercising the full data-transformation and conditional-render logic.

---

## Decision Log

| Decision | Notes |
|---|---|
| FastAPI over Flask/Django | Explicit requirement |
| React Flow for pipeline UX | Explicit requirement |
| JWT auth | Explicit requirement |
| PostgreSQL over DuckDB/SQLite | Explicit requirement |
| `uv` for Python packaging | Global project constraint |
| fetch over axios | Recent axios vuln + lighter bundle |
| httpOnly cookie over localStorage | XSS risk with localStorage; cookies are JS-invisible |
| FastAPI StaticFiles over S3+CloudFront | Eliminates CDN Terraform module; single container is simpler |
| Topological sort for pipeline executor | Clean model for graph resolution; no cyclic dependencies possible |
| `data_month` synthetic column | Partition-ready schema without DDL complexity at demo scale |
| Recharts + Nivo split | Right tool per chart type; Nivo heatmap is genuinely better for 2D grids |
| Chunked `to_sql` ingestion | Avoids OOM on large Parquet files without PyArrow complexity |
| Terraform module structure | Mirrors ECS deployment topology; each service is an independent module |

---

## What I'd Do Differently at Production Scale

1. **Task queue for ingestion** — Celery + Redis so ingestion doesn't block a web worker
2. **Postgres table partitioning** — partition `trips` by month from day one
3. **PyArrow streaming ingestion** — avoid loading 500MB DataFrames; process in 100k-row batches
4. **S3 remote Terraform state** — required for any real team workflow
