import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import type { NodeData, DataSourceConfig } from "@/types/pipeline";

export default function DataSourceNode({ data: raw, selected }: NodeProps) {
  const data = raw as unknown as NodeData;
  const config = data.config as DataSourceConfig;

  return (
    <div
      className={`rounded-lg border-2 p-3 min-w-[160px] bg-blue-950 ${
        selected ? "border-blue-400" : "border-blue-700"
      }`}
    >
      <div className="text-xs font-semibold text-blue-300 uppercase tracking-wide mb-2">
        Data Source
      </div>
      <div className="text-white text-sm font-medium">
        {config.year}-{String(config.month).padStart(2, "0")}
      </div>
      <div className="text-blue-400 text-xs mt-1">Yellow Taxi</div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
