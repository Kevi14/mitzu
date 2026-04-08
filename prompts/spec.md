# Mitzu — Technical Specification

## Overview

Mitzu is an NYC Taxi analytics dashboard built on the Yellow Taxi TLC dataset.
The key differentiator is a React Flow canvas where users chain analytics nodes
into sequential pipelines — e.g. DataSource → Filter → Aggregation → Visualization.

Data source: `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{YYYY}-{MM}.parquet`
Zone lookup: `https://d37ci6vzurychx.cloudfront.net/misc/taxi+_zone_lookup.csv`

---

## Stack

| Layer | Technology |
|---|---|
| Backend language | Python 3.12 (managed with `uv`) |
| API framework | FastAPI + Pydantic |
| Data processing | Pandas + PyArrow |
| Database | PostgreSQL 16 (Docker) |
| ORM / migrations | SQLAlchemy (async) + Alembic |
| Auth | JWT (HS256, python-jose, passlib bcrypt) |
| Frontend | React + TypeScript + Vite |
| Pipeline canvas | @xyflow/react (React Flow) |
| Charts | Recharts (bar/scatter/line) + @nivo/heatmap |
| State management | Zustand |
| HTTP client | fetch |
| Server state | @tanstack/react-query |
| Styling | Tailwind CSS |
| Local infra | Docker Compose |
| Cloud infra | Terraform (AWS) |
| Self-hosted | Helm chart (K3s) |

---

## Project Structure

```
mitzu/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app, lifespan hooks, router registration
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic BaseSettings (env vars)
│   │   │   └── db.py                 # async engine + get_db dependency
│   │   ├── auth/                     # --- AUTH MODULE ---
│   │   │   ├── router.py             # POST /api/auth/login, POST /api/auth/logout
│   │   │   ├── deps.py               # get_current_user FastAPI dependency
│   │   │   ├── jwt.py                # HS256 create/verify token
│   │   │   ├── password.py           # bcrypt hash/verify
│   │   │   ├── models.py             # User ORM model
│   │   │   ├── schemas.py            # LoginRequest, TokenResponse
│   │   │   └── seeder.py             # seed admin user on startup
│   │   ├── ingestion/                # --- INGESTION MODULE ---
│   │   │   ├── router.py             # POST /api/ingest
│   │   │   ├── service.py            # download Parquet → pandas → bulk insert
│   │   │   ├── models.py             # IngestionLog ORM model
│   │   │   └── schemas.py            # IngestRequest, IngestResponse
│   │   ├── analytics/                # --- ANALYTICS MODULE ---
│   │   │   ├── router.py             # POST /api/pipeline/execute
│   │   │   ├── executor.py           # topo-sort (Kahn's) + context resolution
│   │   │   ├── schemas.py            # PipelineRequest, PipelineResponse
│   │   │   └── queries/              # one file per analytic type
│   │   │       ├── trip_count_by_hour.py
│   │   │       ├── fare_vs_distance.py
│   │   │       ├── top_pickup_zones.py
│   │   │       ├── tip_rate_by_payment.py
│   │   │       ├── dow_revenue_heatmap.py
│   │   │       ├── avg_speed_by_hour.py
│   │   │       ├── congestion_trend.py
│   │   │       └── anomaly_flags.py
│   │   ├── zones/                    # --- ZONES MODULE ---
│   │   │   ├── router.py             # GET /api/zones
│   │   │   ├── models.py             # TaxiZone ORM model
│   │   │   ├── schemas.py            # ZoneResponse
│   │   │   └── seeder.py             # one-time zone CSV import on startup
│   │   └── health/                   # --- HEALTH MODULE ---
│   │       └── router.py             # GET /api/health (DB connectivity check)
│   ├── migrations/
│   ├── pyproject.toml
│   └── Dockerfile                    # multi-stage: builds frontend, copies dist/ into /app/static
├── frontend/                         # built separately; dist/ copied into backend image
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts             # fetch wrapper (credentials: include) + 401 redirect
│   │   │   ├── auth.ts
│   │   │   └── analytics.ts
│   │   ├── components/
│   │   │   ├── ui/                   # --- COMPACT SHARED UI PRIMITIVES ---
│   │   │   │   ├── Button.tsx        # size/variant props (sm/md, primary/ghost)
│   │   │   │   ├── Badge.tsx         # status pill (success/error/pending)
│   │   │   │   ├── Card.tsx          # padded surface wrapper
│   │   │   │   ├── Input.tsx         # controlled text input + label
│   │   │   │   ├── Select.tsx        # dropdown with options prop
│   │   │   │   ├── Spinner.tsx       # loading indicator
│   │   │   │   └── EmptyState.tsx    # zero-data placeholder with icon + message
│   │   │   ├── flow/                 # --- PIPELINE CANVAS ---
│   │   │   │   ├── PipelineCanvas.tsx   # React Flow wrapper, edge management
│   │   │   │   ├── NodePalette.tsx      # draggable node type list
│   │   │   │   ├── DataSourceNode.tsx   # year/month pickers
│   │   │   │   ├── FilterNode.tsx       # field/operator/value form
│   │   │   │   ├── AggregationNode.tsx  # analytic type selector
│   │   │   │   └── VisualizationNode.tsx # chart type + key config
│   │   │   ├── charts/               # --- CHART WRAPPERS ---
│   │   │   │   ├── BarChart.tsx
│   │   │   │   ├── ScatterChart.tsx
│   │   │   │   ├── LineChart.tsx
│   │   │   │   └── HeatmapChart.tsx
│   │   │   └── layout/               # --- LAYOUT SHELLS ---
│   │   │       ├── AppShell.tsx      # nav + main content area
│   │   │       └── AuthGuard.tsx     # redirects to /login if no session
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   └── DashboardPage.tsx
│   │   ├── store/pipelineStore.ts    # Zustand
│   │   └── types/pipeline.ts
│   ├── package.json
│   └── vite.config.ts               # no dev proxy needed; same origin in prod
├── infra/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── modules/
│   │       ├── networking/           # VPC, subnets, IGW, NAT
│   │       ├── rds/                  # Postgres 16, t3.medium
│   │       ├── ecs/                  # Fargate + ECR
│   │       ├── alb/                  # ALB + ACM cert
│   │       └── iam/
│   └── helm/mitzu/                   # K3s chart
├── prompts/
├── docs/
├── docker-compose.yml
└── README.md
```

---

## Database Schema

### `trips`
| Column | Type | Notes |
|---|---|---|
| id | bigserial PK | |
| vendor_id | smallint | nullable |
| pickup_datetime | timestamptz | indexed |
| dropoff_datetime | timestamptz | |
| passenger_count | smallint | nullable |
| trip_distance | numeric(8,2) | |
| rate_code_id | smallint | nullable |
| store_and_fwd_flag | char(1) | nullable |
| pu_location_id | smallint | indexed |
| do_location_id | smallint | |
| payment_type | smallint | |
| fare_amount | numeric(8,2) | |
| extra | numeric(8,2) | |
| mta_tax | numeric(8,2) | |
| tip_amount | numeric(8,2) | nullable (cash trips = null) |
| tolls_amount | numeric(8,2) | |
| improvement_surcharge | numeric(8,2) | |
| total_amount | numeric(8,2) | |
| congestion_surcharge | numeric(8,2) | nullable |
| cbd_congestion_fee | numeric(8,2) | nullable |
| data_month | date | indexed — synthetic partition key |

Indexes: `(pickup_datetime)`, `(data_month)`, `(pu_location_id)`, `(payment_type)`

### `taxi_zones`
`location_id` PK, `borough`, `zone`, `service_zone`

### `ingestion_log`
`id`, `data_month` UNIQUE, `status` (pending/success/error), `row_count`, `error_msg`, `created_at`, `updated_at`

### `users`
`id`, `username` UNIQUE, `hashed_password`, `created_at`

---

## API Contract

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | No | Returns JWT |
| GET | `/api/health` | No | DB connectivity check |
| POST | `/api/ingest` | Bearer | Download + insert a monthly Parquet |
| POST | `/api/pipeline/execute` | Bearer | Execute a node pipeline graph |
| GET | `/api/zones` | Bearer | All taxi zones for dropdowns |

### `POST /api/auth/login`
```json
// Request
{ "username": "admin", "password": "mitzu2024" }

// Response
{ "access_token": "<jwt>", "token_type": "bearer" }
```

### `POST /api/ingest`
```json
// Request
{ "year": 2024, "month": 1 }

// Response
{ "status": "success", "row_count": 2964624, "duration_seconds": 47.2 }
```

### `POST /api/pipeline/execute`
```json
// Request
{
  "nodes": [
    { "id": "n1", "type": "datasource", "data": { "config": { "year": 2024, "month": 1 } } },
    { "id": "n2", "type": "aggregation", "data": { "config": { "analytic_type": "trip_count_by_hour" } } },
    { "id": "n3", "type": "visualization", "data": { "config": { "chart_type": "bar", "x_key": "hour", "y_key": "trips" } } }
  ],
  "edges": [
    { "source": "n1", "target": "n2" },
    { "source": "n2", "target": "n3" }
  ]
}

// Response
{
  "results": {
    "n2": { "data": [{ "hour": 0, "trips": 45231 }, ...], "metadata": { "analytic_type": "trip_count_by_hour" } },
    "n3": { "data": [...], "metadata": { "chart_type": "bar", "x_key": "hour", "y_key": "trips" } }
  }
}
```

---

## React Flow Node Types

```typescript
type AnalyticType =
  | 'trip_count_by_hour'
  | 'fare_vs_distance'
  | 'top_pickup_zones'
  | 'tip_rate_by_payment'
  | 'dow_revenue_heatmap'
  | 'avg_speed_by_hour'
  | 'congestion_trend'
  | 'anomaly_flags'

type ChartType = 'bar' | 'scatter' | 'line' | 'heatmap'

interface DataSourceConfig { year: number; month: number }
interface FilterConfig { field: string; operator: '>' | '<' | '=' | 'IN'; value: any }
interface AggregationConfig { analytic_type: AnalyticType }
interface VisualizationConfig { chart_type: ChartType; x_key: string; y_key: string }
```

Node color coding: DataSource=blue, Filter=yellow, Aggregation=green, Visualization=purple.

---

## Analytics Pipeline Execution (Server-Side)

`analytics_executor.py` resolves the graph top-to-bottom:

1. **Topological sort** via Kahn's algorithm (no external deps)
2. Traverse sorted nodes, maintain `context: dict[node_id, list[dict]]`:
   - **DataSource** → stores `{ year, month }` params, no DB call
   - **Filter** → appends WHERE clause params to upstream context (pushed into SQL)
   - **Aggregation** → calls `analytics/<type>.py::run(params, filters, db)` → stores result
   - **Visualization** → passes upstream data through + attaches chart config metadata
3. All analytics functions receive the DataSource params + accumulated filter params + db session
4. Chained aggregations: second aggregation receives first's output as a list and applies pandas groupby (post-aggregation data is always small)

---

## JWT Flow

1. Startup lifespan seeds `admin / mitzu2024` (bcrypt) if no users exist; also seeds zones CSV
2. `POST /auth/login` → bcrypt verify → issue HS256 JWT (60 min TTL, `SECRET_KEY` env var)
3. Backend sets `Set-Cookie: mitzu_session=<jwt>; HttpOnly; SameSite=Strict; Path=/`
4. All subsequent `fetch` calls use `credentials: 'include'` — no manual header attachment needed
5. On 401 response → frontend redirects to `/login`; logout hits `POST /auth/logout` which clears the cookie server-side (`Max-Age=0`)
6. Backend `get_current_user` FastAPI dep: reads cookie via `Request.cookies["mitzu_session"]` → `verify_token()` → 401 if expired/invalid
7. CORS config: `allow_credentials=True`, explicit `allow_origins` (not `*`)

---

## Analytics Queries

| Type | Approach |
|---|---|
| `trip_count_by_hour` | `GROUP BY EXTRACT(hour FROM pickup_datetime)` |
| `fare_vs_distance` | Sample ≤5000 rows; IQR outlier flag (Python-side) |
| `top_pickup_zones` | JOIN `taxi_zones`, `GROUP BY zone`, TOP 20 |
| `tip_rate_by_payment` | `AVG(tip_amount / NULLIF(fare_amount,0)) GROUP BY payment_type` |
| `dow_revenue_heatmap` | `GROUP BY EXTRACT(dow ...), EXTRACT(hour ...)`, `SUM(total_amount)` |
| `avg_speed_by_hour` | `AVG(distance / NULLIF(duration_hours,0)) GROUP BY hour` |
| `congestion_trend` | `GROUP BY data_month`, `AVG(congestion_surcharge)` |
| `anomaly_flags` | `COUNT FILTER` for zero-distance, negative fare, sub-1min trips |

---

## Key Tradeoffs

| Decision | Choice | Why |
|---|---|---|
| Ingestion blocking | `run_in_executor` threadpool | Celery is overkill for demo |
| DB partitioning | Single table + `data_month` index | Schema is partition-ready; ~10M rows per month is fine unpartitioned |
| JWT storage | httpOnly cookie (`SameSite=Strict`) | XSS-safe; JS cannot read the token |
| Frontend serving | FastAPI `StaticFiles` (React `dist/` in backend image) | Eliminates S3 + CloudFront; single container, single ECS task |
| Pipeline execution | Server-side graph resolution | Keeps logic server-side, avoids N frontend round trips |
| Charts | Recharts + Nivo heatmap | Best-of-breed per type |
| Parquet loading | Full `read_parquet` + chunked `to_sql` | Streaming (PyArrow batches) is the production follow-up |
| Terraform state | Local only | Requires pre-existing S3 bucket; out of scope for demo |

---

## Local Run

```bash
git clone <repo> && cd mitzu
docker compose up --build
# App (frontend + API): http://localhost:8000
# API docs:            http://localhost:8000/docs
# Postgres:            localhost:5432

# Ingest a month (cookie auth — use browser or curl with --cookie-jar)
curl -c cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"mitzu2024"}'

curl -b cookies.txt -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"year":2024,"month":1}'
```

### How Static Serving Works

`backend/Dockerfile` is a multi-stage build:
```dockerfile
# Stage 1 — build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/ .
RUN npm ci && npm run build

# Stage 2 — backend + static files
FROM python:3.12-slim
WORKDIR /app
COPY --from=frontend-builder /app/dist /app/static
...
```

`backend/app/main.py` mounts the built assets last (after all API routes):
```python
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

ALB routes: all traffic → single ECS task → FastAPI handles `/api/*` + serves `index.html` for everything else.
