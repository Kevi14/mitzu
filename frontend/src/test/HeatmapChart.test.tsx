/**
 * HeatmapChart integration test.
 *
 * Strategy: mock @nivo/heatmap at the module boundary (jsdom can't render SVG),
 * but test the REAL component code — data transformation, "No data" guard, prop
 * passing — exactly as it runs in the browser.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

// Mock nivo so we can inspect the data it receives without needing a real SVG renderer.
// The mock captures the `data` prop and renders a div we can query.
vi.mock("@nivo/heatmap", () => ({
  ResponsiveHeatMap: ({ data }: { data: { id: string; data: { x: string; y: number }[] }[] }) => (
    <div data-testid="nivo-heatmap" data-rows={data.length} data-has-values={String(data.some((r) => r.data.some((p) => p.y > 0)))} />
  ),
}));

import HeatmapChart from "@/components/charts/HeatmapChart";

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────

const DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function makeDowData(): Record<string, unknown>[] {
  const rows: Record<string, unknown>[] = [];
  for (let dow = 0; dow < 7; dow++) {
    for (let hour = 0; hour < 24; hour++) {
      rows.push({
        dow,
        dow_label: DOW_LABELS[dow],
        hour,
        revenue: (dow + 1) * (hour + 1) * 100,
      });
    }
  }
  return rows;
}

// ──────────────────────────────────────────────────────────────
// DOW revenue heatmap (the failing case)
// ──────────────────────────────────────────────────────────────

describe("HeatmapChart — DOW revenue heatmap", () => {
  const data = makeDowData();

  it("renders the chart (not 'No data') when data is present", () => {
    render(<HeatmapChart data={data} xKey="hour" yKey="dow_label" />);
    expect(screen.queryByText("No data")).not.toBeInTheDocument();
    expect(screen.getByTestId("nivo-heatmap")).toBeInTheDocument();
  });

  it("passes 7 rows (one per DOW) to nivo", () => {
    render(<HeatmapChart data={data} xKey="hour" yKey="dow_label" />);
    expect(screen.getByTestId("nivo-heatmap")).toHaveAttribute("data-rows", "7");
  });

  it("passes non-zero cell values to nivo (revenue, not dow index)", () => {
    render(<HeatmapChart data={data} xKey="hour" yKey="dow_label" />);
    expect(screen.getByTestId("nivo-heatmap")).toHaveAttribute("data-has-values", "true");
  });
});

// ──────────────────────────────────────────────────────────────
// Borough flow heatmap
// ──────────────────────────────────────────────────────────────

describe("HeatmapChart — borough flow", () => {
  const boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx"];
  const data: Record<string, unknown>[] = boroughs.flatMap((from) =>
    boroughs.map((to) => ({ from_borough: from, to_borough: to, trips: from === to ? 10000 : 500 }))
  );

  it("renders the chart (not 'No data')", () => {
    render(<HeatmapChart data={data} xKey="to_borough" yKey="from_borough" />);
    expect(screen.queryByText("No data")).not.toBeInTheDocument();
    expect(screen.getByTestId("nivo-heatmap")).toBeInTheDocument();
  });

  it("passes one row per from_borough to nivo", () => {
    render(<HeatmapChart data={data} xKey="to_borough" yKey="from_borough" />);
    expect(screen.getByTestId("nivo-heatmap")).toHaveAttribute("data-rows", String(boroughs.length));
  });
});

// ──────────────────────────────────────────────────────────────
// Edge cases
// ──────────────────────────────────────────────────────────────

describe("HeatmapChart — edge cases", () => {
  it("shows 'No data' for empty array", () => {
    render(<HeatmapChart data={[]} xKey="hour" yKey="dow_label" />);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.queryByTestId("nivo-heatmap")).not.toBeInTheDocument();
  });

  it("shows a helpful message when no value column exists (xKey + yKey exhaust all numeric columns)", () => {
    // Reproduces: user sets xKey=hour yKey=trips on trip_count_by_hour data
    const data = Array.from({ length: 24 }, (_, h) => ({ hour: h, trips: h * 100 }));
    render(<HeatmapChart data={data as Record<string, unknown>[]} xKey="hour" yKey="trips" />);
    expect(screen.queryByTestId("nivo-heatmap")).not.toBeInTheDocument();
    expect(screen.getByText(/3rd numeric column/)).toBeInTheDocument();
    expect(screen.getByText(/Bar or Line/)).toBeInTheDocument();
  });
});
