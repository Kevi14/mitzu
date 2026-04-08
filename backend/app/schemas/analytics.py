from typing import Any, Literal

from pydantic import BaseModel

AnalyticType = Literal[
    "trip_count_by_hour",
    "fare_vs_distance",
    "top_pickup_zones",
    "tip_rate_by_payment",
    "dow_revenue_heatmap",
    "avg_speed_by_hour",
    "congestion_trend",
    "anomaly_flags",
    "tip_by_zone",
    "demand_anomaly",
    "borough_flow",
    "zone_efficiency",
    "fare_components",
    "payment_trend",
]

ChartType = Literal["bar", "scatter", "line", "heatmap"]
NodeType = Literal["datasource", "filter", "aggregation", "visualization"]
FilterOperator = Literal[">", "<", "=", "IN"]


class DataSourceConfig(BaseModel):
    year: int
    month: int


class FilterConfig(BaseModel):
    field: str
    operator: FilterOperator
    value: Any


class AggregationConfig(BaseModel):
    analytic_type: AnalyticType


class VisualizationConfig(BaseModel):
    chart_type: ChartType
    x_key: str
    y_key: str


class PipelineNode(BaseModel):
    id: str
    type: NodeType
    data: dict[str, Any]


class PipelineEdge(BaseModel):
    source: str
    target: str


class PipelineRequest(BaseModel):
    nodes: list[PipelineNode]
    edges: list[PipelineEdge]


class NodeResult(BaseModel):
    data: list[dict[str, Any]]
    metadata: dict[str, Any]


class PipelineResponse(BaseModel):
    results: dict[str, NodeResult]
