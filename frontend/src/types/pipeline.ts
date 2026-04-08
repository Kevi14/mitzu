export type AnalyticType =
  | "trip_count_by_hour"
  | "fare_vs_distance"
  | "top_pickup_zones"
  | "tip_rate_by_payment"
  | "dow_revenue_heatmap"
  | "avg_speed_by_hour"
  | "congestion_trend"
  | "anomaly_flags"
  | "tip_by_zone"
  | "demand_anomaly"
  | "borough_flow"
  | "zone_efficiency"
  | "fare_components"
  | "payment_trend";

export type ChartType = "bar" | "scatter" | "line" | "heatmap";
export type NodeKind = "datasource" | "filter" | "aggregation" | "visualization";
export type FilterOperator = ">" | "<" | "=" | "IN";

export interface DataSourceConfig {
  year: number;
  month: number;
}

export interface FilterConfig {
  field: string;
  operator: FilterOperator;
  value: string | number;
}

export interface AggregationConfig {
  analytic_type: AnalyticType;
}

export interface VisualizationConfig {
  chart_type: ChartType;
  x_key: string;
  y_key: string;
}

export type NodeConfig = DataSourceConfig | FilterConfig | AggregationConfig | VisualizationConfig;

export interface NodeData extends Record<string, unknown> {
  kind: NodeKind;
  label: string;
  config: NodeConfig;
  result?: Record<string, unknown>[];
  isExecuting?: boolean;
}

export interface PipelineEdge {
  source: string;
  target: string;
}

export interface NodeResult {
  data: Record<string, unknown>[];
  metadata: Record<string, unknown>;
}

export interface PipelineResponse {
  results: Record<string, NodeResult>;
}

export const ANALYTIC_LABELS: Record<AnalyticType, string> = {
  trip_count_by_hour: "Trips by Hour",
  fare_vs_distance: "Fare vs Distance",
  top_pickup_zones: "Top Pickup Zones",
  tip_rate_by_payment: "Tip Rate by Payment",
  dow_revenue_heatmap: "Revenue Heatmap",
  avg_speed_by_hour: "Avg Speed by Hour",
  congestion_trend: "Congestion Trend",
  anomaly_flags: "Anomaly Flags",
  tip_by_zone: "Tip % by Zone",
  demand_anomaly: "Demand Anomaly",
  borough_flow: "Borough Flow",
  zone_efficiency: "Zone Efficiency",
  fare_components: "Fare Breakdown",
  payment_trend: "Payment Trend",
};

export const DEFAULT_CHART: Record<AnalyticType, { chart_type: ChartType; x_key: string; y_key: string }> = {
  trip_count_by_hour: { chart_type: "bar", x_key: "hour", y_key: "trips" },
  fare_vs_distance: { chart_type: "scatter", x_key: "trip_distance", y_key: "fare_amount" },
  top_pickup_zones: { chart_type: "bar", x_key: "zone", y_key: "trips" },
  tip_rate_by_payment: { chart_type: "bar", x_key: "label", y_key: "avg_tip_pct" },
  dow_revenue_heatmap: { chart_type: "heatmap", x_key: "hour", y_key: "dow_label" },
  avg_speed_by_hour: { chart_type: "line", x_key: "hour", y_key: "avg_mph" },
  congestion_trend: { chart_type: "line", x_key: "data_month", y_key: "avg_congestion" },
  anomaly_flags: { chart_type: "bar", x_key: "anomaly", y_key: "count" },
  tip_by_zone: { chart_type: "bar", x_key: "zone", y_key: "avg_tip_pct" },
  demand_anomaly: { chart_type: "bar", x_key: "hour", y_key: "zscore" },
  borough_flow: { chart_type: "heatmap", x_key: "to_borough", y_key: "from_borough" },
  zone_efficiency: { chart_type: "bar", x_key: "zone", y_key: "revenue_per_min" },
  fare_components: { chart_type: "bar", x_key: "component", y_key: "avg_amount" },
  payment_trend: { chart_type: "line", x_key: "data_month", y_key: "credit_card_pct" },
};
