"""
Pipeline executor — receives a React Flow node/edge graph, resolves it via
topological sort, and returns per-node results.

Node traversal rules:
  DataSource   → stores {year, month} params; no DB call
  Filter       → accumulates WHERE-clause params for downstream aggregations
  Aggregation  → calls the analytics/<type>.py::run() function
  Visualization → passes upstream data through; attaches chart config
"""
from collections import deque
from importlib import import_module

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import PipelineEdge, PipelineNode, PipelineResponse, NodeResult

ANALYTIC_MODULES = {
    "trip_count_by_hour": "app.analytics.trip_count_by_hour",
    "fare_vs_distance": "app.analytics.fare_vs_distance",
    "top_pickup_zones": "app.analytics.top_pickup_zones",
    "tip_rate_by_payment": "app.analytics.tip_rate_by_payment",
    "dow_revenue_heatmap": "app.analytics.dow_revenue_heatmap",
    "avg_speed_by_hour": "app.analytics.avg_speed_by_hour",
    "congestion_trend": "app.analytics.congestion_trend",
    "anomaly_flags": "app.analytics.anomaly_flags",
    "tip_by_zone": "app.analytics.tip_by_zone",
    "demand_anomaly": "app.analytics.demand_anomaly",
    "borough_flow": "app.analytics.borough_flow",
    "zone_efficiency": "app.analytics.zone_efficiency",
    "fare_components": "app.analytics.fare_components",
    "payment_trend": "app.analytics.payment_trend",
}

# Backend owns chart defaults — returned in metadata so the frontend needs zero chart knowledge.
ANALYTIC_CHART_DEFAULTS: dict[str, dict] = {
    "trip_count_by_hour": {"chart_type": "bar",     "x_key": "hour",          "y_key": "trips"},
    "fare_vs_distance":   {"chart_type": "scatter",  "x_key": "trip_distance", "y_key": "fare_amount"},
    "top_pickup_zones":   {"chart_type": "bar",      "x_key": "zone",          "y_key": "trips"},
    "tip_rate_by_payment":{"chart_type": "bar",      "x_key": "label",         "y_key": "avg_tip_pct"},
    "dow_revenue_heatmap":{"chart_type": "heatmap",  "x_key": "hour",          "y_key": "dow_label"},
    "avg_speed_by_hour":  {"chart_type": "line",     "x_key": "hour",          "y_key": "avg_mph"},
    "congestion_trend":   {"chart_type": "line",     "x_key": "data_month",    "y_key": "avg_congestion"},
    "anomaly_flags":      {"chart_type": "bar",      "x_key": "anomaly",       "y_key": "count"},
    "tip_by_zone":        {"chart_type": "bar",      "x_key": "zone",          "y_key": "avg_tip_pct"},
    "demand_anomaly":     {"chart_type": "bar",      "x_key": "hour",          "y_key": "zscore"},
    "borough_flow":       {"chart_type": "heatmap",  "x_key": "to_borough",    "y_key": "from_borough"},
    "zone_efficiency":    {"chart_type": "bar",      "x_key": "zone",          "y_key": "revenue_per_min"},
    "fare_components":    {"chart_type": "bar",      "x_key": "component",     "y_key": "avg_amount"},
    "payment_trend":      {"chart_type": "line",     "x_key": "data_month",    "y_key": "credit_card_pct"},
}


def _topo_sort(nodes: list[PipelineNode], edges: list[PipelineEdge]) -> list[str]:
    """Kahn's algorithm — returns node IDs in topological order."""
    adj: dict[str, list[str]] = {n.id: [] for n in nodes}
    in_degree: dict[str, int] = {n.id: 0 for n in nodes}

    for edge in edges:
        adj[edge.source].append(edge.target)
        in_degree[edge.target] += 1

    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    order: list[str] = []
    while queue:
        nid = queue.popleft()
        order.append(nid)
        for neighbor in adj[nid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


def _find_upstream(node_id: str, edges: list[PipelineEdge]) -> str | None:
    for edge in edges:
        if edge.target == node_id:
            return edge.source
    return None


def _find_all_upstream(node_id: str, edges: list[PipelineEdge]) -> list[str]:
    return [edge.source for edge in edges if edge.target == node_id]


def _infer_x_key(datasets: list[list[dict]]) -> str:
    """Find a key present in all non-empty datasets — prefer known time keys."""
    TIME_KEYS = ["hour", "dow", "data_month", "date"]
    candidate_sets = [set(row.keys()) for ds in datasets for row in ds[:1] if ds]
    if not candidate_sets:
        return ""
    common = candidate_sets[0].intersection(*candidate_sets[1:])
    for k in TIME_KEYS:
        if k in common:
            return k
    return next(iter(common), "")


def _merge_datasets(datasets: list[list[dict]], x_key: str) -> list[dict]:
    """Outer-join multiple datasets on x_key, merging all fields."""
    if not x_key:
        x_key = _infer_x_key(datasets)
    if not x_key:
        # No common key — just concatenate
        return [row for ds in datasets for row in ds]
    merged: dict = {}
    for dataset in datasets:
        for row in dataset:
            key = row.get(x_key)
            if key not in merged:
                merged[key] = {x_key: key}
            merged[key].update(row)
    try:
        return sorted(merged.values(), key=lambda r: r.get(x_key) or 0)
    except TypeError:
        return list(merged.values())


async def execute_pipeline(
    nodes: list[PipelineNode],
    edges: list[PipelineEdge],
    db: AsyncSession,
) -> PipelineResponse:
    node_map = {n.id: n for n in nodes}
    order = _topo_sort(nodes, edges)

    # context[node_id] = resolved result data
    context: dict[str, list[dict]] = {}
    # params[node_id] = {year, month, filters}
    params_ctx: dict[str, dict] = {}

    results: dict[str, NodeResult] = {}

    for node_id in order:
        node = node_map[node_id]
        upstream_id = _find_upstream(node_id, edges)

        if node.type == "datasource":
            cfg = node.data.get("config", {})
            params_ctx[node_id] = {"year": cfg.get("year"), "month": cfg.get("month"), "filters": {}}
            context[node_id] = []

        elif node.type == "filter":
            upstream_params = params_ctx.get(upstream_id or "", {}).copy() if upstream_id else {}
            cfg = node.data.get("config", {})
            upstream_params.setdefault("filters", {})[cfg.get("field", "")] = {
                "operator": cfg.get("operator", "="),
                "value": cfg.get("value"),
            }
            params_ctx[node_id] = upstream_params
            context[node_id] = context.get(upstream_id or "", [])

        elif node.type == "aggregation":
            upstream_params = params_ctx.get(upstream_id or "", {}) if upstream_id else {}
            analytic_type = node.data.get("config", {}).get("analytic_type")
            module_path = ANALYTIC_MODULES.get(analytic_type or "")
            if module_path is None:
                data: list[dict] = []
            else:
                mod = import_module(module_path)
                data = await mod.run(upstream_params, upstream_params.get("filters", {}), db)

            chart_defaults = ANALYTIC_CHART_DEFAULTS.get(analytic_type or "")
            params_ctx[node_id] = upstream_params
            context[node_id] = data
            results[node_id] = NodeResult(
                data=data,
                metadata={"analytic_type": analytic_type, **(chart_defaults or {})},
            )

        elif node.type == "visualization":
            cfg = node.data.get("config", {})
            all_upstream_ids = _find_all_upstream(node_id, edges)

            # Pull chart defaults from the nearest upstream aggregation node
            agg_defaults: dict = {}
            for uid in all_upstream_ids:
                up = node_map.get(uid)
                if up and up.type == "aggregation":
                    agg_type = up.data.get("config", {}).get("analytic_type", "")
                    agg_defaults = ANALYTIC_CHART_DEFAULTS.get(agg_type, {})
                    break

            # Backend always owns chart_type — the analytic determines the right chart.
            # x_key/y_key can be user-overridden (empty = use backend defaults).
            chart_type = agg_defaults.get("chart_type", "bar")
            x_key = cfg.get("x_key") or agg_defaults.get("x_key", "")
            y_key = cfg.get("y_key") or agg_defaults.get("y_key", "")

            datasets = [context.get(uid, []) for uid in all_upstream_ids if uid in context]
            if len(datasets) == 0:
                upstream_data = []
            elif len(datasets) == 1:
                upstream_data = datasets[0]
                if not x_key:
                    x_key = _infer_x_key(datasets)
            else:
                if not x_key:
                    x_key = _infer_x_key(datasets)
                upstream_data = _merge_datasets(datasets, x_key)

            context[node_id] = upstream_data
            results[node_id] = NodeResult(
                data=upstream_data,
                metadata={
                    "chart_type": chart_type,
                    "x_key": x_key,
                    "y_key": y_key,
                },
            )

    return PipelineResponse(results=results)
