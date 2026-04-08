import type { Node } from "@xyflow/react";
import type { NodeData, DataSourceConfig, FilterConfig, AggregationConfig, VisualizationConfig, AnalyticType } from "@/types/pipeline";
import { ANALYTIC_LABELS, DEFAULT_CHART } from "@/types/pipeline";
import { usePipelineStore } from "@/store/pipelineStore";

interface Props {
  node: Node<NodeData>;
}

export default function NodeConfigPanel({ node }: Props) {
  const updateNodeData = usePipelineStore((s) => s.updateNodeData);
  const nodes = usePipelineStore((s) => s.nodes);
  const edges = usePipelineStore((s) => s.edges);

  // Walk upstream edges until we find an aggregation node
  const findUpstreamAggType = (): AnalyticType | null => {
    let currentId = node.id;
    for (let i = 0; i < 10; i++) {
      const edge = edges.find((e) => e.target === currentId);
      if (!edge) break;
      const upstream = nodes.find((n) => n.id === edge.source);
      if (!upstream) break;
      if (upstream.data.kind === "aggregation") {
        return (upstream.data.config as AggregationConfig).analytic_type ?? null;
      }
      currentId = upstream.id;
    }
    return null;
  };

  const update = (patch: Partial<NodeData>) => updateNodeData(node.id, patch);
  const updateConfig = (patch: object) =>
    update({ config: { ...node.data.config, ...patch } });

  const kind = node.data.kind;

  return (
    <div className="w-64 bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Configure · {node.data.label}
      </h2>

      {kind === "datasource" && (
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Year</label>
            <input
              type="number"
              min={2019}
              max={2026}
              value={(node.data.config as DataSourceConfig).year}
              onChange={(e) => updateConfig({ year: Number(e.target.value) })}
              className="w-full bg-gray-800 text-white rounded px-2 py-1.5 text-sm border border-gray-700"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Month</label>
            <select
              value={(node.data.config as DataSourceConfig).month}
              onChange={(e) => updateConfig({ month: Number(e.target.value) })}
              className="w-full bg-gray-800 text-white rounded px-2 py-1.5 text-sm border border-gray-700"
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <option key={m} value={m}>
                  {new Date(2024, m - 1).toLocaleString("en", { month: "long" })}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {kind === "filter" && (
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Field</label>
            <select
              value={(node.data.config as FilterConfig).field}
              onChange={(e) => updateConfig({ field: e.target.value })}
              className="w-full bg-gray-800 text-white rounded px-2 py-1.5 text-sm border border-gray-700"
            >
              {["trip_distance", "fare_amount", "passenger_count", "payment_type", "pu_location_id"].map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Operator</label>
            <select
              value={(node.data.config as FilterConfig).operator}
              onChange={(e) => updateConfig({ operator: e.target.value })}
              className="w-full bg-gray-800 text-white rounded px-2 py-1.5 text-sm border border-gray-700"
            >
              {[">", "<", "=", "IN"].map((op) => <option key={op} value={op}>{op}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Value</label>
            <input
              type="text"
              value={String((node.data.config as FilterConfig).value)}
              onChange={(e) => updateConfig({ value: e.target.value })}
              className="w-full bg-gray-800 text-white rounded px-2 py-1.5 text-sm border border-gray-700"
            />
          </div>
        </div>
      )}

      {kind === "aggregation" && (
        <div>
          <label className="block text-xs text-gray-400 mb-1">Analytics Type</label>
          <select
            value={(node.data.config as AggregationConfig).analytic_type}
            onChange={(e) => {
              const type = e.target.value as keyof typeof ANALYTIC_LABELS;
              updateConfig({ analytic_type: type });
            }}
            className="w-full bg-gray-800 text-white rounded px-2 py-1.5 text-sm border border-gray-700"
          >
            {Object.entries(ANALYTIC_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
      )}

      {kind === "visualization" && (() => {
        const aggType = findUpstreamAggType();
        const suggested = aggType ? DEFAULT_CHART[aggType] : null;
        const vizCfg = node.data.config as VisualizationConfig;

        return (
          <div className="space-y-3">
            {suggested && (
              <p className="text-xs text-indigo-400 bg-indigo-950 rounded px-2 py-1.5 leading-snug">
                Upstream: <span className="font-medium">{ANALYTIC_LABELS[aggType!]}</span>
                <br />Suggested: <code className="text-indigo-300">{suggested.x_key}</code> × <code className="text-indigo-300">{suggested.y_key}</code>
              </p>
            )}
            <div>
              <label className="block text-xs text-gray-400 mb-1">Chart Type</label>
              <select
                value={vizCfg.chart_type}
                onChange={(e) => updateConfig({ chart_type: e.target.value })}
                className="w-full bg-gray-800 text-white rounded px-2 py-1.5 text-sm border border-gray-700"
              >
                {["bar", "line", "scatter", "heatmap"].map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                X Key
                {suggested && <span className="ml-1 text-indigo-400">(suggested: {suggested.x_key})</span>}
              </label>
              <input
                list={`x-key-suggestions-${node.id}`}
                type="text"
                value={vizCfg.x_key}
                onChange={(e) => updateConfig({ x_key: e.target.value })}
                className="w-full bg-gray-800 text-white rounded px-2 py-1.5 text-sm border border-gray-700"
                placeholder={suggested?.x_key ?? "e.g. hour"}
              />
              {suggested && (
                <datalist id={`x-key-suggestions-${node.id}`}>
                  <option value={suggested.x_key} />
                </datalist>
              )}
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Y Key
                {suggested && <span className="ml-1 text-indigo-400">(suggested: {suggested.y_key})</span>}
              </label>
              <input
                list={`y-key-suggestions-${node.id}`}
                type="text"
                value={vizCfg.y_key}
                onChange={(e) => updateConfig({ y_key: e.target.value })}
                className="w-full bg-gray-800 text-white rounded px-2 py-1.5 text-sm border border-gray-700"
                placeholder={suggested?.y_key ?? "e.g. trips"}
              />
              {suggested && (
                <datalist id={`y-key-suggestions-${node.id}`}>
                  <option value={suggested.y_key} />
                </datalist>
              )}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
