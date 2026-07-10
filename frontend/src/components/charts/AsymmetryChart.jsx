// Asymmetry history: bar per session, colour-coded, reference line at 10%.
import {
  Bar, BarChart, Cell, CartesianGrid, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

function aiColor(ai) {
  if (ai == null) return "#555";
  if (ai < 10) return "#28e07a";
  if (ai <= 15) return "#f59e0b";
  return "#ef4444";
}

export default function AsymmetryChart({ sessions }) {
  const data = sessions
    .filter((s) => s.avg_asymmetry != null)
    .map((s, i) => ({ session: `#${i + 1}`, ai: s.avg_asymmetry }));

  return (
    <div className="chart-card">
      <h3>Bilateral Asymmetry (AI %)</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis dataKey="session" stroke="#aaa" />
          <YAxis stroke="#aaa" />
          <Tooltip contentStyle={{ background: "#1b1b20", border: "1px solid #333" }} />
          <ReferenceLine y={10} stroke="#f59e0b" strokeDasharray="4 4"
            label={{ value: "10% warning", fill: "#f59e0b", position: "insideTopRight" }} />
          <Bar dataKey="ai">
            {data.map((d, i) => <Cell key={i} fill={aiColor(d.ai)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
