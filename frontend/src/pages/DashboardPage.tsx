import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import type { Node } from "@xyflow/react";
import { authApi } from "@/api/auth";
import { analyticsApi } from "@/api/analytics";
import NodePalette from "@/components/flow/NodePalette";
import PipelineCanvas from "@/components/flow/PipelineCanvas";
import NodeConfigPanel from "@/components/flow/NodeConfigPanel";
import { usePipelineStore } from "@/store/pipelineStore";
import type { NodeData, VisualizationConfig } from "@/types/pipeline";
import BarChart from "@/components/charts/BarChart";
import ScatterChart from "@/components/charts/ScatterChart";
import LineChart from "@/components/charts/LineChart";
import HeatmapChart from "@/components/charts/HeatmapChart";

export default function DashboardPage() {
  const navigate = useNavigate();
  const nodes = usePipelineStore((s) => s.nodes);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const [ingestYear, setIngestYear] = useState(2024);
  const [ingestMonth, setIngestMonth] = useState(1);

  const [ingestStatus, setIngestStatus] = useState<{ status: string; row_count?: number; error_msg?: string } | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  useEffect(() => () => stopPolling(), []);

  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => navigate("/login"),
  });

  const ingestMutation = useMutation({
    mutationFn: () => analyticsApi.ingest(ingestYear, ingestMonth),
    onSuccess: (data) => {
      setIngestStatus(data);
      if (data.status === "started" || data.status === "pending") {
        pollRef.current = setInterval(async () => {
          const s = await analyticsApi.ingestStatus(ingestYear, ingestMonth);
          setIngestStatus(s);
          if (s.status === "success" || s.status === "error" || s.status === "already_ingested") {
            stopPolling();
          }
        }, 2000);
      }
    },
  });

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) as Node<NodeData> | undefined;

  const vizResults = nodes.filter(
    (n) => n.data.kind === "visualization" && n.data.result && (n.data.result as unknown[]).length > 0
  ) as Node<NodeData>[];

  const [activeResultId, setActiveResultId] = useState<string | null>(null);
  const [resultsOpen, setResultsOpen] = useState(false);

  // Auto-open results panel when new results arrive
  useEffect(() => {
    if (vizResults.length > 0) {
      setResultsOpen(true);
      setActiveResultId((prev) => prev && vizResults.find((n) => n.id === prev) ? prev : vizResults[0].id);
    }
  }, [vizResults.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const activeResult = vizResults.find((n) => n.id === activeResultId);

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-white font-bold text-lg">Mitzu</h1>
          <span className="text-gray-500 text-xs">NYC Taxi Analytics</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Ingest controls */}
          <div className="flex items-center gap-2 text-sm">
            <select
              value={ingestYear}
              onChange={(e) => setIngestYear(Number(e.target.value))}
              className="bg-gray-800 text-white rounded px-2 py-1 border border-gray-700 text-xs"
            >
              {[2022, 2023, 2024, 2025].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <select
              value={ingestMonth}
              onChange={(e) => setIngestMonth(Number(e.target.value))}
              className="bg-gray-800 text-white rounded px-2 py-1 border border-gray-700 text-xs"
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <option key={m} value={m}>
                  {new Date(2024, m - 1).toLocaleString("en", { month: "short" })}
                </option>
              ))}
            </select>
            <button
              onClick={() => ingestMutation.mutate()}
              disabled={ingestMutation.isPending}
              className="bg-emerald-700 hover:bg-emerald-600 disabled:bg-emerald-900 text-white text-xs font-medium px-3 py-1 rounded transition-colors"
            >
              {ingestMutation.isPending ? "Starting…" : "Ingest"}
            </button>
            {ingestStatus && (
              <span className={`text-xs ${
                ingestStatus.status === "success" || ingestStatus.status === "already_ingested" ? "text-emerald-400" :
                ingestStatus.status === "error" ? "text-red-400" : "text-yellow-400"
              }`}>
                {ingestStatus.status === "success" ? `✓ ${ingestStatus.row_count?.toLocaleString()} rows` :
                 ingestStatus.status === "already_ingested" ? "already ingested" :
                 ingestStatus.status === "error" ? `✗ ${ingestStatus.error_msg ?? "failed"}` :
                 "ingesting…"}
              </span>
            )}
          </div>

          <button
            onClick={() => logoutMutation.mutate()}
            className="text-gray-400 hover:text-white text-xs transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Pipeline area */}
        <div className={`flex min-h-0 ${resultsOpen && vizResults.length > 0 ? "flex-[0_0_45%]" : "flex-1"}`}>
          <NodePalette />
          <div className="flex-1 relative">
            <PipelineCanvas onNodeSelect={setSelectedNodeId} />
          </div>
          {selectedNode && <NodeConfigPanel node={selectedNode} />}
        </div>

        {/* Results panel */}
        {vizResults.length > 0 && (
          <div className={`shrink-0 flex flex-col border-t border-gray-800 bg-gray-900 ${resultsOpen ? "flex-[0_0_55%]" : "h-10"}`}>
            {/* Results toolbar */}
            <div className="flex items-center gap-0 border-b border-gray-800 shrink-0 h-10">
              <button
                onClick={() => setResultsOpen((v) => !v)}
                className="flex items-center gap-2 px-3 h-full text-xs text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
              >
                <span>{resultsOpen ? "▼" : "▲"}</span>
                <span className="font-medium">Results</span>
                <span className="bg-indigo-700 text-white rounded px-1.5 py-0.5 text-[10px]">{vizResults.length}</span>
              </button>
              {resultsOpen && vizResults.map((n) => (
                <button
                  key={n.id}
                  onClick={() => setActiveResultId(n.id)}
                  className={`px-4 h-full text-xs border-r border-gray-800 transition-colors ${
                    n.id === activeResultId
                      ? "text-white bg-gray-800 border-b-2 border-b-indigo-500"
                      : "text-gray-400 hover:text-white hover:bg-gray-800"
                  }`}
                >
                  {n.data.label}
                </button>
              ))}
            </div>

            {/* Active chart */}
            {resultsOpen && activeResult && (() => {
              const cfg = activeResult.data.config as VisualizationConfig;
              const result = activeResult.data.result as Record<string, unknown>[];
              return (
                <div className="flex-1 min-h-0 p-4" style={{ minHeight: 0 }}>
                  <div style={{ width: "100%", height: "100%" }}>
                    {cfg.chart_type === "bar" && <BarChart data={result} xKey={cfg.x_key} yKey={cfg.y_key} />}
                    {cfg.chart_type === "scatter" && <ScatterChart data={result} xKey={cfg.x_key} yKey={cfg.y_key} />}
                    {cfg.chart_type === "line" && <LineChart data={result} xKey={cfg.x_key} yKey={cfg.y_key} />}
                    {cfg.chart_type === "heatmap" && <HeatmapChart data={result} xKey={cfg.x_key} yKey={cfg.y_key} />}
                  </div>
                </div>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
}
