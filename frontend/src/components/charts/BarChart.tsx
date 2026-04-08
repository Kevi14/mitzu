import {
  BarChart as ReBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";

const SERIES_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6"];

interface Props {
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
}

export default function BarChart({ data, xKey, yKey }: Props) {
  if (!data.length) return null;

  // Auto-detect x key if blank
  const resolvedX = xKey || Object.keys(data[0]).find((k) => typeof data[0][k] !== "number") || Object.keys(data[0])[0];
  // Auto-detect numeric series: all numeric keys except x key
  const allKeys = Object.keys(data[0]).filter((k) => k !== resolvedX && typeof data[0][k] === "number");
  const series = yKey && allKeys.includes(yKey)
    ? [yKey, ...allKeys.filter((k) => k !== yKey)]
    : allKeys;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ReBarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey={xKey} tick={{ fill: "#94a3b8", fontSize: 11 }} />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} width={50} />
        <Tooltip
          contentStyle={{ background: "#0f172a", border: "1px solid #334155", fontSize: 12 }}
          labelStyle={{ color: "#cbd5e1" }}
        />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />}
        {series.map((key, i) => (
          <Bar key={key} dataKey={key} fill={SERIES_COLORS[i % SERIES_COLORS.length]} radius={[3, 3, 0, 0]} />
        ))}
      </ReBarChart>
    </ResponsiveContainer>
  );
}
