import { useCallback, useRef, type DragEvent } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  type Node,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { usePipelineStore } from "@/store/pipelineStore";
import type { NodeData, NodeKind } from "@/types/pipeline";
import DataSourceNode from "./DataSourceNode";
import FilterNode from "./FilterNode";
import AggregationNode from "./AggregationNode";
import VisualizationNode from "./VisualizationNode";

// Cast required: XyFlow's NodeTypes index signature is stricter than needed
// for generic custom node data. This is the standard community pattern.
const nodeTypes = {
  datasource: DataSourceNode,
  filter: FilterNode,
  aggregation: AggregationNode,
  visualization: VisualizationNode,
} as unknown as NodeTypes;

let idCounter = 0;
const newId = () => `node-${++idCounter}`;

interface Props {
  onNodeSelect: (id: string | null) => void;
}

export default function PipelineCanvas({ onNodeSelect }: Props) {
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode, isExecuting, execute, error, clearError } =
    usePipelineStore();

  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      console.log("drop event", event);
      const raw = event.dataTransfer.getData("application/json");
      console.log("drop raw:", raw);
      if (!raw) return;

      const { kind, label, config } = JSON.parse(raw) as {
        kind: NodeKind;
        label: string;
        config: object;
      };

      const bounds = reactFlowWrapper.current?.getBoundingClientRect();
      const position = bounds
        ? { x: event.clientX - bounds.left - 80, y: event.clientY - bounds.top - 30 }
        : { x: 100, y: 100 };

      const newNode: Node<NodeData> = {
        id: newId(),
        type: kind,
        position,
        data: { kind, label, config } as NodeData,
      };
      addNode(newNode);
    },
    [addNode],
  );

  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }, []);

  return (
    <div className="w-full h-full" ref={reactFlowWrapper} onDrop={onDrop} onDragOver={onDragOver}>
      {/* Toolbar */}
      <div className="absolute top-3 right-3 z-10 flex items-center gap-2">
        {error && (
          <div className="bg-red-900 text-red-200 text-xs px-3 py-1.5 rounded-lg flex items-center gap-2">
            {error}
            <button onClick={clearError} className="hover:text-white">×</button>
          </div>
        )}
        <button
          onClick={execute}
          disabled={isExecuting || nodes.length === 0}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:text-indigo-400 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors"
        >
          {isExecuting ? "Running…" : "▶ Execute Pipeline"}
        </button>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        onNodeClick={(_e, node) => onNodeSelect(node.id)}
        onPaneClick={() => onNodeSelect(null)}
        fitView
        className="bg-gray-950"
      >
        <Background variant={BackgroundVariant.Dots} color="#1e293b" gap={20} size={1} />
        <Controls className="!bg-gray-900 !border-gray-700" />
        <MiniMap
          className="!bg-gray-900 !border-gray-700"
          nodeColor={(n) => {
            const kind = (n as Node<NodeData>).data?.kind;
            return kind === "datasource" ? "#1e40af"
              : kind === "filter" ? "#713f12"
              : kind === "aggregation" ? "#14532d"
              : "#581c87";
          }}
        />
      </ReactFlow>
    </div>
  );
}
