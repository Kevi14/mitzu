import { describe, it, expect } from "vitest";
import { buildNivoData } from "@/components/charts/HeatmapChart";

const DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function makeDowData() {
  const rows: Record<string, unknown>[] = [];
  for (let dow = 0; dow < 7; dow++) {
    for (let hour = 0; hour < 24; hour++) {
      rows.push({ dow, dow_label: DOW_LABELS[dow], hour, revenue: (dow + 1) * (hour + 1) * 100 });
    }
  }
  return rows;
}

describe("buildNivoData — DOW revenue heatmap", () => {
  const data = makeDowData();

  it("succeeds with correct keys", () => {
    const result = buildNivoData(data, "hour", "dow_label");
    expect(result.ok).toBe(true);
  });

  it("returns 7 rows (one per day)", () => {
    const result = buildNivoData(data, "hour", "dow_label");
    expect(result.ok && result.rows).toHaveLength(7);
  });

  it("each row has 24 data points", () => {
    const result = buildNivoData(data, "hour", "dow_label");
    if (!result.ok) throw new Error(result.reason);
    for (const row of result.rows) expect(row.data).toHaveLength(24);
  });

  it("picks revenue as value key (not dow index 0–6)", () => {
    const result = buildNivoData(data, "hour", "dow_label");
    if (!result.ok) throw new Error(result.reason);
    const mon = result.rows.find((r) => r.id === "Mon")!;
    expect(mon.data[0].y).toBe(200); // (1+1)*(0+1)*100
  });

  it("no cell is 0 — would trigger No data guard", () => {
    const result = buildNivoData(data, "hour", "dow_label");
    if (!result.ok) throw new Error(result.reason);
    const allZero = result.rows.every((row) => row.data.every((p) => p.y === 0));
    expect(allZero).toBe(false);
  });

  it("rows are ordered Sun→Sat", () => {
    const result = buildNivoData(data, "hour", "dow_label");
    if (!result.ok) throw new Error(result.reason);
    expect(result.rows.map((r) => r.id)).toEqual(DOW_LABELS);
  });

  it("hours are sorted 0→23", () => {
    const result = buildNivoData(data, "hour", "dow_label");
    if (!result.ok) throw new Error(result.reason);
    const hours = result.rows[0].data.map((p) => Number(p.x));
    expect(hours).toEqual(Array.from({ length: 24 }, (_, i) => i));
  });
});

describe("buildNivoData — borough flow", () => {
  const boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"];
  const data: Record<string, unknown>[] = boroughs.flatMap((from) =>
    boroughs.map((to) => ({ from_borough: from, to_borough: to, trips: from === to ? 10000 : 500 }))
  );

  it("succeeds with correct keys", () => {
    expect(buildNivoData(data, "to_borough", "from_borough").ok).toBe(true);
  });

  it("returns one row per from_borough", () => {
    const result = buildNivoData(data, "to_borough", "from_borough");
    expect(result.ok && result.rows).toHaveLength(boroughs.length);
  });

  it("diagonal cells have higher value than off-diagonal", () => {
    const result = buildNivoData(data, "to_borough", "from_borough");
    if (!result.ok) throw new Error(result.reason);
    const manhattan = result.rows.find((r) => r.id === "Manhattan")!;
    expect(manhattan.data.find((p) => p.x === "Manhattan")!.y).toBeGreaterThan(
      manhattan.data.find((p) => p.x === "Brooklyn")!.y
    );
  });
});

describe("buildNivoData — error cases", () => {
  it("fails when data is empty", () => {
    const result = buildNivoData([], "x", "y");
    expect(result.ok).toBe(false);
  });

  it("fails with a clear message when no value column exists (both axes consume all numeric keys)", () => {
    // trip_count_by_hour: only {hour, trips} — user sets xKey=hour yKey=trips
    const data = Array.from({ length: 24 }, (_, h) => ({ hour: h, trips: h * 100 }));
    const result = buildNivoData(data as Record<string, unknown>[], "hour", "trips");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toMatch(/3rd numeric column/);
      expect(result.reason).toMatch(/Bar or Line/);
    }
  });

  it("succeeds when only xKey is set (yKey empty) — 1D case shows as single row", () => {
    // This is what happens when user only fills X Key
    const data = Array.from({ length: 24 }, (_, h) => ({ hour: h, trips: h * 100 }));
    const result = buildNivoData(data as Record<string, unknown>[], "hour", "");
    // yKey="" means "trips" is the remaining numeric key → becomes value column
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.rows[0].data.some((p) => p.y > 0)).toBe(true);
    }
  });
});
