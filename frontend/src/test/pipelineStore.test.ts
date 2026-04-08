/**
 * Tests for the pipelineStore execute() auto-fill logic.
 *
 * The backend owns chart_type/x_key/y_key decisions and returns them in viz node
 * metadata. The store must apply them correctly in all cases.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { usePipelineStore } from "@/store/pipelineStore";
import type { Node, Edge } from "@xyflow/react";
import type { NodeData } from "@/types/pipeline";

// Mock the analytics API
vi.mock("@/api/analytics", () => ({
  analyticsApi: {
    executePipeline: vi.fn(),
  },
}));

import { analyticsApi } from "@/api/analytics";

function makeVizNode(config: object): Node<NodeData> {
  return {
    id: "viz",
    type: "visualization",
    position: { x: 0, y: 0 },
    data: { kind: "visualization", label: "Viz", config: config as NodeData["config"] },
  };
}

function makeAggNode(): Node<NodeData> {
  return {
    id: "agg",
    type: "aggregation",
    position: { x: 0, y: 0 },
    data: { kind: "aggregation", label: "Agg", config: { analytic_type: "dow_revenue_heatmap" } as NodeData["config"] },
  };
}

const edges: Edge[] = [{ id: "e1", source: "agg", target: "viz" }];

const fakeApiResponse = {
  results: {
    viz: {
      data: [{ dow: 1, dow_label: "Mon", hour: 8, revenue: 12345 }],
      metadata: { chart_type: "heatmap", x_key: "hour", y_key: "dow_label" },
    },
  },
};

beforeEach(() => {
  // Reset store to initial state between tests
  usePipelineStore.setState({ nodes: [], edges: [], isExecuting: false, error: null, lastResults: null });
  vi.mocked(analyticsApi.executePipeline).mockResolvedValue(fakeApiResponse as never);
});

describe("pipelineStore — viz node auto-fill", () => {
  it("applies chart_type from backend when viz is unconfigured (x_key='')", async () => {
    usePipelineStore.setState({
      nodes: [makeAggNode(), makeVizNode({ chart_type: "bar", x_key: "", y_key: "" })],
      edges,
    });

    await usePipelineStore.getState().execute();

    const vizNode = usePipelineStore.getState().nodes.find((n) => n.id === "viz")!;
    const cfg = vizNode.data.config as { chart_type: string; x_key: string; y_key: string };
    expect(cfg.chart_type).toBe("heatmap");
    expect(cfg.x_key).toBe("hour");
    expect(cfg.y_key).toBe("dow_label");
  });

  it("still applies chart_type when x_key was already set by a prior execution", async () => {
    // Simulates: user ran pipeline once → x_key got filled → chart_type stayed "bar"
    usePipelineStore.setState({
      nodes: [makeAggNode(), makeVizNode({ chart_type: "bar", x_key: "hour", y_key: "dow_label" })],
      edges,
    });

    await usePipelineStore.getState().execute();

    const vizNode = usePipelineStore.getState().nodes.find((n) => n.id === "viz")!;
    const cfg = vizNode.data.config as { chart_type: string };
    expect(cfg.chart_type).toBe("heatmap"); // must NOT stay "bar"
  });

  it("backend always wins on chart_type even when user had previously set a different type", async () => {
    // x_key is already configured, user previously had chart_type="line"
    // BE returns chart_type="heatmap" — should override
    usePipelineStore.setState({
      nodes: [makeAggNode(), makeVizNode({ chart_type: "line", x_key: "hour", y_key: "revenue" })],
      edges,
    });

    await usePipelineStore.getState().execute();

    const vizNode = usePipelineStore.getState().nodes.find((n) => n.id === "viz")!;
    const cfg = vizNode.data.config as { chart_type: string };
    expect(cfg.chart_type).toBe("heatmap");
  });

  it("attaches result data to the viz node", async () => {
    usePipelineStore.setState({
      nodes: [makeAggNode(), makeVizNode({ chart_type: "bar", x_key: "", y_key: "" })],
      edges,
    });

    await usePipelineStore.getState().execute();

    const vizNode = usePipelineStore.getState().nodes.find((n) => n.id === "viz")!;
    expect(vizNode.data.result).toEqual(fakeApiResponse.results.viz.data);
  });
});
