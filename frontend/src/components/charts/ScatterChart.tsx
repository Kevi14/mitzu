import {
  ScatterChart as ReScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";

interface DataPoint {
  trip_distance: number;
  fare_amount: number;
  is_outlier?: boolean;
}

interface Props {
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
}

export default function ScatterChart({ data, xKey, yKey }: Props) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ReScatterChart margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey={xKey} name={xKey} tick={{ fill: "#94a3b8", fontSize: 10 }} />
        <YAxis dataKey={yKey} name={yKey} tick={{ fill: "#94a3b8", fontSize: 10 }} />
        <Tooltip
          contentStyle={{ background: "#0f172a", border: "1px solid #334155", fontSize: 11 }}
          cursor={{ strokeDasharray: "3 3" }}
        />
        <Scatter data={data as unknown as DataPoint[]} name="trips">
          {(data as unknown as DataPoint[]).map((entry, i) => (
            <Cell key={i} fill={entry.is_outlier ? "#ef4444" : "#6366f1"} opacity={0.7} />
          ))}
        </Scatter>
      </ReScatterChart>
    </ResponsiveContainer>
  );
}
