import { Handle, Position } from "@xyflow/react";
import type { NodeProps } from "@xyflow/react";
import type { NodeData, FilterConfig } from "@/types/pipeline";

export default function FilterNode({ data: raw, selected }: NodeProps) {
  const data = raw as unknown as NodeData;
  const config = data.config as FilterConfig;

  return (
    <div
      className={`rounded-lg border-2 p-3 min-w-[160px] bg-yellow-950 ${
        selected ? "border-yellow-400" : "border-yellow-700"
      }`}
    >
      <div className="text-xs font-semibold text-yellow-300 uppercase tracking-wide mb-2">
        Filter
      </div>
      <div className="text-white text-sm font-mono">
        {config.field} {config.operator} {String(config.value)}
      </div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
