import { ResponsiveHeatMap } from "@nivo/heatmap";

interface Props {
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
}

const DOW_ORDER = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export type BuildResult =
  | { ok: true; rows: { id: string; data: { x: string; y: number }[] }[] }
  | { ok: false; reason: string };

// Exported for testing
export function buildNivoData(
  data: Record<string, unknown>[],
  xKey: string,
  yKey: string
): BuildResult {
  if (!data.length) return { ok: false, reason: "No data" };

  // Pick the numeric key (not xKey/yKey) with the highest mean — reliably picks
  // "revenue"/"trips" over small category indices like "dow" (0–6).
  const numericCandidates = Object.keys(data[0]).filter(
    (k) => k !== xKey && k !== yKey && typeof data[0][k] === "number"
  );

  if (numericCandidates.length === 0) {
    return {
      ok: false,
      reason: `Heatmap needs a 3rd numeric column for cell values, but all numeric columns are already used as axes (x="${xKey}", y="${yKey}"). Try a Bar or Line chart for this data.`,
    };
  }

  const valueKey = numericCandidates.reduce(
    (best, k) => {
      const avgBest = data.reduce((s, r) => s + ((r[best] as number) || 0), 0) / data.length;
      const avgK = data.reduce((s, r) => s + ((r[k] as number) || 0), 0) / data.length;
      return avgK > avgBest ? k : best;
    },
    numericCandidates[0]
  );

  const rawX = [...new Set(data.map((r) => r[xKey]))];
  const rawY = [...new Set(data.map((r) => String(r[yKey])))];

  const sortedX = [...rawX].sort((a, b) => {
    if (typeof a === "number" && typeof b === "number") return a - b;
    return String(a).localeCompare(String(b));
  });

  const sortedY = [...rawY].sort((a, b) => {
    const ai = DOW_ORDER.indexOf(a);
    const bi = DOW_ORDER.indexOf(b);
    if (ai >= 0 && bi >= 0) return ai - bi;
    return a.localeCompare(b);
  });

  const rows = sortedY.map((yVal) => ({
    id: yVal,
    data: sortedX.map((xVal) => {
      const row = data.find(
        (r) => String(r[xKey]) === String(xVal) && String(r[yKey]) === yVal
      );
      return { x: String(xVal), y: (row?.[valueKey] as number) ?? 0 };
    }),
  }));

  return { ok: true, rows };
}

export default function HeatmapChart({ data, xKey, yKey }: Props) {
  if (!data.length) {
    return <div className="flex items-center justify-center h-32 text-gray-500 text-xs">No data</div>;
  }

  const result = buildNivoData(data, xKey, yKey);

  if (!result.ok) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-xs text-center px-6">
        {result.reason}
      </div>
    );
  }

  const nivoData = result.rows;

  const sortedX = nivoData[0]?.data.map((p) => p.x) ?? [];
  const tickValues =
    sortedX.length > 12
      ? sortedX.filter((_, i) => i % Math.ceil(sortedX.length / 8) === 0)
      : undefined;

  return (
    <div style={{ height: "100%" }}>
      <ResponsiveHeatMap
        data={nivoData}
        margin={{ top: 4, right: 8, bottom: 36, left: 80 }}
        axisTop={null}
        axisBottom={{
          tickSize: 0,
          tickPadding: 4,
          legend: xKey,
          legendOffset: 28,
          ...(tickValues ? { tickValues } : {}),
        }}
        axisLeft={{ tickSize: 0, tickPadding: 4 }}
        colors={{ type: "sequential", scheme: "purples" }}
        emptyColor="#0f172a"
        borderRadius={2}
        animate={false}
        theme={{
          axis: {
            ticks: { text: { fill: "#94a3b8", fontSize: 9 } },
            legend: { text: { fill: "#94a3b8", fontSize: 9 } },
          },
          tooltip: { container: { background: "#0f172a", border: "1px solid #334155", fontSize: 11 } },
        }}
      />
    </div>
  );
}
