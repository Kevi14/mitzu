# Initial Prompt

## Context

This project was kicked off as an engineering assignment: build a small NYC Taxi data dashboard
that demonstrates interesting data exploration over real TLC trip-record data.

## The Prompt

> I want to build a data exploration dashboard on NYC Yellow Taxi trip data.
>
> **Backend** (Python, FastAPI, `uv` for package management):
> - Pull Yellow Taxi Parquet files from the TLC public CloudFront URL for a given year/month.
> - Transform and bulk-load them into PostgreSQL (Docker Compose locally). Streaming download
>   to temp file → batch insert via pandas `to_sql` to cap memory usage.
> - Expose an authenticated REST API. Auth via HTTP-only JWT cookie (no OAuth, no session store).
>   Single admin user seeded on startup.
> - Idempotent ingestion: track status in an `ingestion_log` table; skip months already loaded.
> - The core feature is a **pipeline execution endpoint** (`POST /api/pipeline/execute`):
>   the client sends a React Flow node/edge graph and the server resolves it via topological sort
>   (Kahn's algorithm, no external deps), then executes each node in order:
>     - `datasource` node → holds `{ year, month }` params; no DB call.
>     - `filter` node → accumulates WHERE-clause parameters into a context dict that flows
>       downstream (pushed into SQL, not applied in pandas).
>     - `aggregation` node → dynamically imports and calls `analytics/<type>.py::run(params, filters, db)`.
>     - `visualization` node → outer-joins multiple upstream datasets on a shared x-axis key,
>       attaches chart config metadata.
> - Analytics modules to implement (derive exact SQL from the real parquet schema):
>     1. Trip count by hour of day
>     2. Fare amount vs. trip distance (scatter, IQR outlier flagging)
>     3. Top 20 pickup zones (join to `taxi_zones` reference table)
>     4. Tip rate by payment type (credit card vs. cash comparison)
>     5. Day-of-week × hour revenue heatmap
>     6. Average speed by hour (mph, computed from distance / elapsed time)
>     7. Congestion surcharge trend across all ingested months
>     8. Anomaly flag summary (zero distance, negative fare, sub-1-min trips, extreme values)
>
> **Frontend** (React + Vite):
> - React Flow canvas as the primary UI — users drag `datasource`, `filter`, `aggregation`,
>   and `visualization` nodes, wire them together, and hit "Run Pipeline".
> - Recharts for rendering. Chart type driven by the visualization node's config.
> - JWT session stored in HTTP-only cookie; login page guards all routes.
> - Sidebar for triggering data ingestion (year/month picker + status polling).
>
> **Infra**:
> - Docker Compose for local dev (backend + postgres).
> - Terraform for AWS (document architecture, no actual deployment required).
> - README must cover clone → run in under 5 minutes.
>
> Before writing any code: inspect a real Yellow Taxi Parquet file from the TLC URL, identify
> the actual column names and types, and derive the SQL schema and analytics queries from the
> real data — not assumed column names.

## How It Was Framed

The prompt was specific about architecture decisions but left SQL query design and data schema
to be derived empirically from the actual Parquet files. This forced the AI to read the real
data before writing a single line of SQL, catching column-name differences (e.g. `Airport_fee`
vs `cbd_congestion_fee` across schema versions) before they became bugs.

## What Was Decided by the Human

| Decision | Choice | Rationale |
|---|---|---|
| Python framework | FastAPI | Async-native, automatic OpenAPI docs |
| Package management | `uv` | Assignment constraint |
| Database | PostgreSQL | Row-oriented analytics at ~10M rows/month; known operationally |
| Auth | HTTP-only JWT cookie | No OAuth complexity; CSRF-safe for same-site SPA |
| Pipeline UX | React Flow | Nodes/edges map directly to the DAG execution model |
| Insert strategy | pandas `to_sql` in batches | Balances throughput and memory; no COPY dependency |
| Ingestion model | Single monthly Parquet file | Matches TLC's own publication cadence |
| Infra | Docker Compose + Terraform (AWS) | Local simplicity; documented cloud path |

## What the AI Was Asked to Figure Out

- Exact column names and types present in Yellow Taxi Parquet (schema changed in 2022 and 2024)
- Which 8 analytics queries are most insightful given the real schema
- How to model filter push-down through the DAG (context dict accumulation vs. post-hoc pandas filter)
- DB schema that supports time-scoped analytics via a `data_month DATE` partition key
- Kahn's algorithm for topological sort without adding a graph library dependency
- How chained aggregations share data (first agg output becomes second agg's pandas input)
