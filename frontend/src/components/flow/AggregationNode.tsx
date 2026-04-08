import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import type { NodeData, AggregationConfig } from "@/types/pipeline";
import { ANALYTIC_LABELS } from "@/types/pipeline";

export default function AggregationNode({ data: raw, selected }: NodeProps) {
  const data = raw as unknown as NodeData;
  const config = data.config as AggregationConfig;

  return (
    <div
      className={`rounded-lg border-2 p-3 min-w-[180px] bg-green-950 ${
        selected ? "border-green-400" : "border-green-700"
      }`}
    >
      <div className="text-xs font-semibold text-green-300 uppercase tracking-wide mb-2">
        Aggregation
      </div>
      <div className="text-white text-sm font-medium">
        {ANALYTIC_LABELS[config.analytic_type] ?? config.analytic_type}
      </div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
