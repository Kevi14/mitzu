import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import type { NodeData, VisualizationConfig } from "@/types/pipeline";
import BarChart from "@/components/charts/BarChart";
import ScatterChart from "@/components/charts/ScatterChart";
import LineChart from "@/components/charts/LineChart";
import HeatmapChart from "@/components/charts/HeatmapChart";

export default function VisualizationNode({ data: raw, selected }: NodeProps) {
  const data = raw as unknown as NodeData;
  const config = data.config as VisualizationConfig;
  const result = (data.result as Record<string, unknown>[]) ?? [];

  const renderChart = () => {
    if (result.length === 0) {
      return (
        <div className="flex items-center justify-center h-32 text-gray-500 text-xs">
          No data — run pipeline
        </div>
      );
    }
    switch (config.chart_type) {
      case "bar":
        return <BarChart data={result} xKey={config.x_key} yKey={config.y_key} />;
      case "scatter":
        return <ScatterChart data={result} xKey={config.x_key} yKey={config.y_key} />;
      case "line":
        return <LineChart data={result} xKey={config.x_key} yKey={config.y_key} />;
      case "heatmap":
        return <HeatmapChart data={result} xKey={config.x_key} yKey={config.y_key} />;
    }
  };

  return (
    <div
      className={`rounded-lg border-2 p-3 bg-purple-950 ${
        selected ? "border-purple-400" : "border-purple-700"
      }`}
      style={{ minWidth: 340, minHeight: 200 }}
    >
      <div className="text-xs font-semibold text-purple-300 uppercase tracking-wide mb-2">
        Visualization · {config.chart_type}
      </div>
      {renderChart()}
      <Handle type="target" position={Position.Left} />
    </div>
  );
}
