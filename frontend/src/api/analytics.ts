import { api } from "./client";
import type { PipelineResponse } from "@/types/pipeline";
import type { Node, Edge } from "@xyflow/react";
import type { NodeData } from "@/types/pipeline";

export interface Zone {
  location_id: number;
  borough: string;
  zone: string;
}

export interface IngestStatusResponse {
  status: string;
  row_count?: number;
  error_msg?: string;
  data_month?: string;
}

export const analyticsApi = {
  getZones: () => api.get<Zone[]>("/zones"),

  ingest: (year: number, month: number) =>
    api.post<IngestStatusResponse>("/ingest", { year, month }),

  ingestStatus: (year: number, month: number) =>
    api.get<IngestStatusResponse>(`/ingest/status/${year}/${month}`),

  executePipeline: (nodes: Node<NodeData>[], edges: Edge[]) =>
    api.post<PipelineResponse>("/pipeline/execute", {
      nodes: nodes.map((n) => ({ id: n.id, type: n.data.kind, data: { config: n.data.config } })),
      edges: edges.map((e) => ({ source: e.source, target: e.target })),
    }),
};
