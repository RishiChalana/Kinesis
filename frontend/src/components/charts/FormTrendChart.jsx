// Form score trend: one line per exercise, reference line at y=80.
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const COLORS = ["#28e07a", "#3b82f6", "#f59e0b", "#a855f7", "#ef4444"];

export default function FormTrendChart({ sessions }) {
  const withScores = sessions.filter((s) => s.avg_form_score != null);
  const exercises = [...new Set(withScores.map((s) => s.exercise))];
  // One row per session; each row carries only its own exercise's score.
  const data = withScores.map((s) => ({
    date: new Date(s.started_at).toLocaleDateString(),
    [s.exercise]: s.avg_form_score,
  }));

  return (
    <div className="chart-card">
      <h3>Form Score Trend</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis dataKey="date" stroke="#aaa" />
          <YAxis domain={[0, 100]} stroke="#aaa" />
          <Tooltip contentStyle={{ background: "#1b1b20", border: "1px solid #333" }} />
          <Legend />
          <ReferenceLine y={80} stroke="#28e07a" strokeDasharray="4 4"
            label={{ value: "good form", fill: "#28e07a", position: "insideTopRight" }} />
          {exercises.map((ex, i) => (
            <Line key={ex} type="monotone" dataKey={ex} stroke={COLORS[i % COLORS.length]}
              strokeWidth={2} connectNulls dot={{ r: 3 }} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
