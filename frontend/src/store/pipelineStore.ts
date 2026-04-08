import { create } from "zustand";
import type { Node, Edge, NodeChange, EdgeChange, Connection } from "@xyflow/react";
import { applyNodeChanges, applyEdgeChanges, addEdge } from "@xyflow/react";
import type { NodeData, PipelineResponse } from "@/types/pipeline";
import { analyticsApi } from "@/api/analytics";

interface PipelineState {
  nodes: Node<NodeData>[];
  edges: Edge[];
  isExecuting: boolean;
  lastResults: PipelineResponse | null;
  error: string | null;

  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (node: Node<NodeData>) => void;
  updateNodeData: (id: string, data: Partial<NodeData>) => void;
  execute: () => Promise<void>;
  clearError: () => void;
}

export const usePipelineStore = create<PipelineState>((set, get) => ({
  nodes: [],
  edges: [],
  isExecuting: false,
  lastResults: null,
  error: null,

  onNodesChange: (changes) =>
    set((s) => ({ nodes: applyNodeChanges(changes, s.nodes) as Node<NodeData>[] })),

  onEdgesChange: (changes) =>
    set((s) => ({ edges: applyEdgeChanges(changes, s.edges) })),

  onConnect: (connection) =>
    set((s) => ({ edges: addEdge(connection, s.edges) })),

  addNode: (node) =>
    set((s) => ({ nodes: [...s.nodes, node] })),

  updateNodeData: (id, data) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...data } } : n)),
    })),

  execute: async () => {
    const { nodes, edges } = get();
    set({ isExecuting: true, error: null });
    try {
      const response = await analyticsApi.executePipeline(nodes, edges);
      // Attach results to visualization nodes; back-fill chart config from backend metadata
      set((s) => ({
        nodes: s.nodes.map((n) => {
          if (n.data.kind === "visualization" && response.results[n.id]) {
            const nodeResult = response.results[n.id];
            const meta = nodeResult.metadata as Record<string, string>;
            const vizConfig = n.data.config as unknown as { x_key?: string; y_key?: string; chart_type?: string; [k: string]: unknown };
            // BE owns chart_type — always apply it.
            // x_key/y_key are only auto-filled when blank (user can override them).
            const keysNotConfigured = !vizConfig.x_key;
            const patchedConfig = {
              ...vizConfig,
              ...(meta.chart_type ? { chart_type: meta.chart_type } : {}),
              ...(keysNotConfigured && meta.x_key ? { x_key: meta.x_key } : {}),
              ...(keysNotConfigured && meta.y_key ? { y_key: meta.y_key } : {}),
            };
            return { ...n, data: { ...n.data, config: patchedConfig as unknown as NodeData["config"], result: nodeResult.data } };
          }
          return n;
        }) as Node<NodeData>[],
        lastResults: response,
        isExecuting: false,
      }));
    } catch (err) {
      set({ isExecuting: false, error: err instanceof Error ? err.message : "Execution failed" });
    }
  },

  clearError: () => set({ error: null }),
}));
