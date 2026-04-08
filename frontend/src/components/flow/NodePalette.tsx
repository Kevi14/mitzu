import type { DragEvent } from "react";
import type { NodeKind, AnalyticType } from "@/types/pipeline";
import { ANALYTIC_LABELS } from "@/types/pipeline";

interface PaletteItem {
  kind: NodeKind;
  label: string;
  description: string;
  color: string;
  defaultConfig: object;
}

const PALETTE_ITEMS: PaletteItem[] = [
  {
    kind: "datasource",
    label: "Data Source",
    description: "Select month",
    color: "border-blue-700 bg-blue-950 text-blue-300",
    defaultConfig: { year: 2024, month: 1 },
  },
  {
    kind: "filter",
    label: "Filter",
    description: "Filter rows",
    color: "border-yellow-700 bg-yellow-950 text-yellow-300",
    defaultConfig: { field: "trip_distance", operator: ">", value: 0 },
  },
  ...(Object.keys(ANALYTIC_LABELS) as AnalyticType[]).map((type) => ({
    kind: "aggregation" as NodeKind,
    label: ANALYTIC_LABELS[type],
    description: "Analytics",
    color: "border-green-700 bg-green-950 text-green-300",
    defaultConfig: { analytic_type: type },
  })),
];

export default function NodePalette() {
  const onDragStart = (event: DragEvent<HTMLDivElement>, item: PaletteItem) => {
    console.log("dragStart", item.kind, item.label);
    const dragData = { kind: item.kind, label: item.label, config: item.defaultConfig };
    event.dataTransfer.setData("application/json", JSON.stringify(dragData));
    event.dataTransfer.effectAllowed = "copy";
  };

  return (
    <div className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col overflow-y-auto">
      <div className="p-3 border-b border-gray-800">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Nodes</h2>
        <p className="text-xs text-gray-600 mt-1">Drag onto canvas</p>
      </div>
      <div className="flex-1 p-2 space-y-1">
        {PALETTE_ITEMS.map((item, i) => (
          <div
            key={`${item.kind}-${i}`}
            draggable
            onDragStart={(e) => onDragStart(e, item)}
            className={`rounded-md border px-3 py-2 cursor-grab active:cursor-grabbing ${item.color} select-none`}
          >
            <div className="text-xs font-medium">{item.label}</div>
            {item.kind !== "aggregation" && (
              <div className="text-xs opacity-60 mt-0.5">{item.description}</div>
            )}
          </div>
        ))}

        {/* Visualization node */}
          <div
            draggable
            onDragStart={(e) => {
              const dragData = {
                kind: "visualization" as NodeKind,
                label: "Visualization",
                config: { chart_type: "bar", x_key: "", y_key: "" },
              };
              e.dataTransfer.setData("application/json", JSON.stringify(dragData));
              e.dataTransfer.effectAllowed = "copy";
            }}
          className="rounded-md border border-purple-700 bg-purple-950 text-purple-300 px-3 py-2 cursor-grab active:cursor-grabbing select-none"
        >
          <div className="text-xs font-medium">Visualization</div>
          <div className="text-xs opacity-60 mt-0.5">Chart output</div>
        </div>
      </div>
    </div>
  );
}
