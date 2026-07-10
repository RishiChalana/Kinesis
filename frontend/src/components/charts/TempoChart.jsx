// Tempo chart: grouped bars per session (eccentric/isometric/concentric).
import {
  Bar, BarChart, CartesianGrid, Legend,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

export default function TempoChart({ tempo }) {
  const data = tempo.map((t, i) => ({
    session: `#${i + 1}`,
    eccentric: t.eccentric_s,
    isometric: t.isometric_s,
    concentric: t.concentric_s,
  }));

  return (
    <div className="chart-card">
      <h3>Tempo (seconds per phase)</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis dataKey="session" stroke="#aaa" />
          <YAxis stroke="#aaa" />
          <Tooltip contentStyle={{ background: "#1b1b20", border: "1px solid #333" }} />
          <Legend />
          <Bar dataKey="eccentric" fill="#3b82f6" />
          <Bar dataKey="isometric" fill="#9ca3af" />
          <Bar dataKey="concentric" fill="#28e07a" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
