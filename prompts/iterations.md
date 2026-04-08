# Key Iterations

## 1. Frontend serving: S3 + CloudFront → FastAPI StaticFiles

**Initial plan:** Separate S3 bucket + CloudFront distribution serving the React build.
This was the default "AWS way" and was in the first version of the Terraform plan.

**Course correction:** S3 + CloudFront is a full extra Terraform module
(bucket, policy, OAC, distribution, cache behaviors, ACM cert, CNAME) just to serve static files.
At demo scale it's unnecessary overhead.

**Resolution:** Multi-stage Dockerfile — Node builds `dist/`, Python image copies it to `static/`,
FastAPI mounts via `StaticFiles`. One container, one ECS task. `modules/cdn/` removed from Terraform.

---

## 2. JWT: localStorage → httpOnly cookie

**Initial plan:** JWT stored in `localStorage["mitzu_token"]`, attached to requests via a fetch
interceptor setting `Authorization: Bearer`.

**Course correction:** Cookies are safer — localStorage is XSS-vulnerable; an httpOnly cookie is
invisible to JavaScript entirely.

**Resolution:** Login sets `Set-Cookie: mitzu_session=<jwt>; HttpOnly; SameSite=Strict`.
All `fetch` calls use `credentials: 'include'`. No JS can read the token.
Backend reads `request.cookies["mitzu_session"]` via `get_current_user` dependency.

---

## 3. HTTP client: Axios → native fetch

**Initial plan:** Axios as the HTTP client (standard React ecosystem choice).

**Course correction:** Recent axios security vulnerability + bundle size preference.

**Resolution:** Thin `request()` wrapper around native `fetch` in `src/api/client.ts`.
Handles JSON bodies, `credentials: 'include'`, and 401 redirects without any library.

---

## 4. React version: 19 → 18

**Issue (discovered during implementation):** `@nivo/heatmap@0.88.0` has `peerDependencies`
of `react ">= 16.14.0 < 19.0.0"`. npm refused to install with React 19.

**Options considered:**
- `--legacy-peer-deps` (rejected — masks real compatibility issues)
- Build custom SVG heatmap with no dependency (valid, ~10 lines)
- Downgrade to React 18 (LTS, fully supported)

**Resolution:** Downgraded to React 18.3.1. React 18 is the current LTS; the only user-visible
difference is that `createRoot` hydration behavior changed slightly in 19, which doesn't affect
this project.

---

## 5. TypeScript: XyFlow NodeData type constraint

**Issue (discovered during implementation):** `@xyflow/react` requires custom node data to
satisfy `Record<string, unknown>`. Our `NodeData` interface had named properties but no index
signature, causing ~30 type errors across node components and the store.

**Fix:** Added `extends Record<string, unknown>` to the `NodeData` interface. Node components
use unparameterized `NodeProps` and cast `data as unknown as NodeData` inside — the standard
XyFlow community pattern. `nodeTypes` map cast as `unknown as NodeTypes` to bypass the
incompatible index signature.

---

## 6. Analytics executor: client-side vs server-side

**Decision:** Server-side graph resolution wins:
- Filters get pushed into SQL WHERE clauses (not applied in JS after fetch)
- Single round trip instead of N
- Analytics logic stays out of the browser
- Consistent with keeping "business logic" server-side

The `analytics_executor.py` uses Kahn's topological sort (no dependencies, ~20 lines) and
propagates a `context` dict from DataSource → Filter → Aggregation → Visualization.

---

## 7. Ruff + ESLint/Prettier (added mid-build)

Added linting/formatting configuration:
- `backend/ruff.toml` — target Python 3.12, `select = ["E","F","W","I","UP","B","SIM"]`,
  `B008` ignored (FastAPI Depends), `format.quote-style = "double"`
- `frontend/eslint.config.js` — typescript-eslint + react-hooks + react-refresh + prettier
- `frontend/.prettierrc` — double quotes, 2-space indent, 100-char lines, trailing commas

---

## 8. Feature expansion: 6 new analytics modules

Added `tip_by_zone`, `demand_anomaly`, `borough_flow`, `zone_efficiency`, `fare_components`,
`payment_trend` — each a self-contained SQL query module following the existing `run(params, filters, db)` pattern.

Key architectural decision made here: chart config (`chart_type`, `x_key`, `y_key`) moved into
`ANALYTIC_CHART_DEFAULTS` in the executor. Backend owns these decisions; frontend is a pure renderer.
`HeatmapChart` refactored from a hardcoded DOW-only component to a generic xKey/yKey-driven one.

---

## 9. Heatmap "No data" — multi-round debugging

The most instructive debugging chain in the project. Each round required writing a failing test
before the fix was trusted.

**Round 1 — wrong value key:** Generic HeatmapChart picked `dow` (0–6) as the cell value instead
of `revenue` (thousands). Fixed by selecting the numeric key with the highest mean across all rows.

**Round 2 — chart_type never updated:** Store back-filled `x_key` from metadata but never
`chart_type` or `y_key`. Viz node stayed `chart_type: "bar"` — heatmap never rendered.

**Round 3 — executor echoed user's value back:** Even after fixing the store, the executor's
`user_configured` branch returned the user's `chart_type` in metadata. Store applied it and
nothing changed. Root cause: backend was symmetric — it preserved whatever the user had set
rather than enforcing the canonical type.

**Resolution:** Backend always returns `chart_type` from `ANALYTIC_CHART_DEFAULTS`, regardless
of user config. Store always applies `meta.chart_type`. Three separate tests — one per round —
confirmed each fix before moving on.

---

## 10. Frontend test infrastructure

No test runner existed. Added Vitest + React Testing Library.

Key decision: extracted `buildNivoData` as a named exported pure function rather than leaving
it inline in the component. Inline logic requires a full DOM render to test; the extracted function
runs in isolation in 27ms and caught the value-key selection bug (Round 1 above) before the
browser was opened.

Render tests mock `@nivo/heatmap` at the module boundary — tests the real component code and
conditional render logic without needing a working SVG renderer in jsdom.

---

## 11. Heatmap error messaging (UX fix)

User set `yKey="trips"` on `trip_count_by_hour` data (`{hour, trips}` — only 2 columns).
Both numeric columns claimed as axes; zero left for cell values → all cells = 0 → silent "No data".

Changed `buildNivoData` to return a discriminated union `BuildResult`. When no value column
exists, returns `{ ok: false, reason: "Heatmap needs a 3rd numeric column..." }`. The component
renders the reason string directly in the chart area instead of a generic "No data".
