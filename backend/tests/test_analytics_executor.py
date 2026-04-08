"""
Tests for the pipeline executor:
  - _topo_sort (Kahn's algorithm)
  - _find_upstream / _find_all_upstream
  - _merge_datasets
  - execute_pipeline end-to-end (DB mocked, module import patched)
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.analytics import PipelineEdge, PipelineNode
from app.services.analytics_executor import (
    _find_all_upstream,
    _find_upstream,
    _merge_datasets,
    _topo_sort,
    execute_pipeline,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def node(id: str, type: str, config: dict | None = None) -> PipelineNode:
    return PipelineNode(id=id, type=type, data={"config": config or {}})


def edge(source: str, target: str) -> PipelineEdge:
    return PipelineEdge(source=source, target=target)


# ---------------------------------------------------------------------------
# _topo_sort
# ---------------------------------------------------------------------------

def test_topo_sort_single_node():
    assert _topo_sort([node("a", "datasource")], []) == ["a"]


def test_topo_sort_linear_chain():
    nodes = [node("a", "datasource"), node("b", "aggregation"), node("c", "visualization")]
    edges = [edge("a", "b"), edge("b", "c")]
    order = _topo_sort(nodes, edges)
    assert order.index("a") < order.index("b") < order.index("c")


def test_topo_sort_diamond():
    # a -> b, a -> c, b -> d, c -> d
    nodes = [node(n, "datasource") for n in ["a", "b", "c", "d"]]
    edges = [edge("a", "b"), edge("a", "c"), edge("b", "d"), edge("c", "d")]
    order = _topo_sort(nodes, edges)
    assert order.index("a") < order.index("b")
    assert order.index("a") < order.index("c")
    assert order.index("b") < order.index("d")
    assert order.index("c") < order.index("d")


def test_topo_sort_two_independent_roots():
    nodes = [node("a", "datasource"), node("b", "datasource"), node("c", "visualization")]
    edges = [edge("a", "c"), edge("b", "c")]
    order = _topo_sort(nodes, edges)
    assert order.index("a") < order.index("c")
    assert order.index("b") < order.index("c")


# ---------------------------------------------------------------------------
# _find_upstream
# ---------------------------------------------------------------------------

def test_find_upstream_returns_source():
    edges = [edge("a", "b"), edge("b", "c")]
    assert _find_upstream("b", edges) == "a"
    assert _find_upstream("c", edges) == "b"


def test_find_upstream_root_returns_none():
    assert _find_upstream("a", [edge("a", "b")]) is None


def test_find_upstream_no_edges():
    assert _find_upstream("x", []) is None


# ---------------------------------------------------------------------------
# _find_all_upstream
# ---------------------------------------------------------------------------

def test_find_all_upstream_multiple_sources():
    edges = [edge("a", "c"), edge("b", "c"), edge("d", "e")]
    assert set(_find_all_upstream("c", edges)) == {"a", "b"}


def test_find_all_upstream_single():
    assert _find_all_upstream("b", [edge("a", "b")]) == ["a"]


def test_find_all_upstream_none():
    assert _find_all_upstream("a", [edge("a", "b")]) == []


# ---------------------------------------------------------------------------
# _merge_datasets
# ---------------------------------------------------------------------------

def test_merge_datasets_empty():
    assert _merge_datasets([], "hour") == []


def test_merge_datasets_single_source():
    data = [{"hour": 1, "trips": 10}, {"hour": 2, "trips": 20}]
    result = _merge_datasets([data], "hour")
    assert len(result) == 2
    assert result[0]["hour"] == 1
    assert result[0]["trips"] == 10


def test_merge_datasets_joins_on_x_key():
    d1 = [{"hour": 1, "trips": 10}, {"hour": 2, "trips": 20}]
    d2 = [{"hour": 1, "avg_mph": 12.5}, {"hour": 2, "avg_mph": 9.0}]
    result = _merge_datasets([d1, d2], "hour")
    assert len(result) == 2
    assert result[0] == {"hour": 1, "trips": 10, "avg_mph": 12.5}
    assert result[1] == {"hour": 2, "trips": 20, "avg_mph": 9.0}


def test_merge_datasets_partial_overlap():
    d1 = [{"hour": 1, "trips": 5}]
    d2 = [{"hour": 2, "trips": 8}]
    result = _merge_datasets([d1, d2], "hour")
    assert len(result) == 2
    hours = {r["hour"] for r in result}
    assert hours == {1, 2}


# ---------------------------------------------------------------------------
# execute_pipeline — end-to-end with mocked DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_datasource_only():
    """A lone datasource node produces no results entries."""
    nodes = [node("ds", "datasource", {"year": 2024, "month": 1})]
    result = await execute_pipeline(nodes, [], AsyncMock())
    assert result.results == {}


@pytest.mark.asyncio
async def test_pipeline_unknown_analytic_type_returns_empty():
    nodes = [
        node("ds", "datasource", {"year": 2024, "month": 1}),
        node("agg", "aggregation", {"analytic_type": "does_not_exist"}),
    ]
    result = await execute_pipeline(nodes, [edge("ds", "agg")], AsyncMock())
    assert "agg" in result.results
    assert result.results["agg"].data == []


@pytest.mark.asyncio
async def test_pipeline_aggregation_missing_year_returns_empty():
    """If the datasource has no year/month, analytics modules return []."""
    nodes = [
        node("ds", "datasource", {}),  # no year/month
        node("agg", "aggregation", {"analytic_type": "trip_count_by_hour"}),
    ]
    result = await execute_pipeline(nodes, [edge("ds", "agg")], AsyncMock())
    assert result.results["agg"].data == []


@pytest.mark.asyncio
async def test_pipeline_datasource_aggregation_visualization():
    fake_data = [{"hour": h, "trips": h * 100} for h in range(24)]

    nodes = [
        node("ds", "datasource", {"year": 2024, "month": 1}),
        node("agg", "aggregation", {"analytic_type": "trip_count_by_hour"}),
        node("viz", "visualization", {"chart_type": "bar", "x_key": "hour", "y_key": "trips"}),
    ]
    edges = [edge("ds", "agg"), edge("agg", "viz")]

    with patch("app.services.analytics_executor.import_module") as mock_import:
        mock_mod = MagicMock()
        mock_mod.run = AsyncMock(return_value=fake_data)
        mock_import.return_value = mock_mod

        result = await execute_pipeline(nodes, edges, AsyncMock())

    assert result.results["agg"].data == fake_data
    assert result.results["viz"].data == fake_data
    assert result.results["viz"].metadata == {"chart_type": "bar", "x_key": "hour", "y_key": "trips"}


@pytest.mark.asyncio
async def test_pipeline_filter_accumulates_into_params():
    """Filter node should pass filter params downstream to aggregation."""
    called_filters = {}

    async def capture_run(params, filters, db):
        called_filters.update(filters)
        return []

    nodes = [
        node("ds", "datasource", {"year": 2024, "month": 1}),
        node("f", "filter", {"field": "payment_type", "operator": "=", "value": 1}),
        node("agg", "aggregation", {"analytic_type": "tip_rate_by_payment"}),
    ]
    edges = [edge("ds", "f"), edge("f", "agg")]

    with patch("app.services.analytics_executor.import_module") as mock_import:
        mock_mod = MagicMock()
        mock_mod.run = AsyncMock(side_effect=capture_run)
        mock_import.return_value = mock_mod

        await execute_pipeline(nodes, edges, AsyncMock())

    assert "payment_type" in called_filters
    assert called_filters["payment_type"]["value"] == 1


@pytest.mark.asyncio
async def test_pipeline_viz_auto_fills_heatmap_config():
    """Backend must supply chart_type/x_key/y_key even when viz node has the default 'bar' config."""
    fake_data = [
        {"dow": 1, "dow_label": "Mon", "hour": 8, "revenue": 12345.0},
        {"dow": 1, "dow_label": "Mon", "hour": 9, "revenue": 15000.0},
    ]
    nodes = [
        node("ds", "datasource", {"year": 2024, "month": 1}),
        node("agg", "aggregation", {"analytic_type": "dow_revenue_heatmap"}),
        # Viz node in its default unconfigured state: chart_type="bar", x_key="", y_key=""
        node("viz", "visualization", {"chart_type": "bar", "x_key": "", "y_key": ""}),
    ]
    edges = [edge("ds", "agg"), edge("agg", "viz")]

    with patch("app.services.analytics_executor.import_module") as mock_import:
        mock_mod = MagicMock()
        mock_mod.run = AsyncMock(return_value=fake_data)
        mock_import.return_value = mock_mod
        result = await execute_pipeline(nodes, edges, AsyncMock())

    meta = result.results["viz"].metadata
    # Backend should override the default "bar" with "heatmap"
    assert meta["chart_type"] == "heatmap", f"Expected heatmap, got {meta['chart_type']}"
    assert meta["x_key"] == "hour"
    assert meta["y_key"] == "dow_label"


@pytest.mark.asyncio
async def test_pipeline_viz_backend_always_owns_chart_type():
    """Backend chart_type from agg_defaults always wins — user x_key/y_key overrides are respected."""
    fake_data = [{"hour": h, "trips": h * 100} for h in range(24)]
    nodes = [
        node("ds", "datasource", {"year": 2024, "month": 1}),
        node("agg", "aggregation", {"analytic_type": "trip_count_by_hour"}),
        # User set chart_type to "line" — backend must override to "bar" (agg_default)
        # User also set x_key/y_key explicitly — those are respected
        node("viz", "visualization", {"chart_type": "line", "x_key": "hour", "y_key": "trips"}),
    ]
    edges = [edge("ds", "agg"), edge("agg", "viz")]

    with patch("app.services.analytics_executor.import_module") as mock_import:
        mock_mod = MagicMock()
        mock_mod.run = AsyncMock(return_value=fake_data)
        mock_import.return_value = mock_mod
        result = await execute_pipeline(nodes, edges, AsyncMock())

    meta = result.results["viz"].metadata
    assert meta["chart_type"] == "bar"    # backend overrides user's "line"
    assert meta["x_key"] == "hour"        # user's x_key respected
    assert meta["y_key"] == "trips"       # user's y_key respected


@pytest.mark.asyncio
async def test_pipeline_visualization_merges_multiple_aggregations():
    """Two aggregation nodes feeding one visualization should be outer-joined."""
    data_a = [{"hour": 0, "trips": 10}, {"hour": 1, "trips": 20}]
    data_b = [{"hour": 0, "avg_mph": 5.0}, {"hour": 1, "avg_mph": 8.0}]

    nodes = [
        node("ds", "datasource", {"year": 2024, "month": 1}),
        node("agg1", "aggregation", {"analytic_type": "trip_count_by_hour"}),
        node("agg2", "aggregation", {"analytic_type": "avg_speed_by_hour"}),
        node("viz", "visualization", {"chart_type": "line", "x_key": "hour", "y_key": "trips"}),
    ]
    edges = [
        edge("ds", "agg1"), edge("ds", "agg2"),
        edge("agg1", "viz"), edge("agg2", "viz"),
    ]

    side_effects = [data_a, data_b]

    with patch("app.services.analytics_executor.import_module") as mock_import:
        mock_mod = MagicMock()
        mock_mod.run = AsyncMock(side_effect=side_effects)
        mock_import.return_value = mock_mod

        result = await execute_pipeline(nodes, edges, AsyncMock())

    viz_data = result.results["viz"].data
    assert len(viz_data) == 2
    # Both datasets should be merged on "hour"
    row0 = next(r for r in viz_data if r["hour"] == 0)
    assert row0["trips"] == 10
    assert row0["avg_mph"] == 5.0
