// Per-rep timeline: one bar per rep coloured by form_score. Tooltip shows
// errors/duration/asymmetry; clicking a bar reveals compensation info.
import { useState } from "react";
import {
  Bar, BarChart, Cell, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

function scoreColor(s) {
  if (s == null) return "#555";
  if (s < 60) return "#ef4444";
  if (s < 80) return "#f59e0b";
  return "#28e07a";
}

function RepTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const r = payload[0].payload;
  return (
    <div className="rep-tooltip">
      <div><strong>Rep {r.rep}</strong> — score {r.form_score ?? "--"}</div>
      <div>duration: {r.duration != null ? r.duration.toFixed(1) + "s" : "--"}</div>
      <div>asymmetry: {r.asymmetry_pct != null ? r.asymmetry_pct.toFixed(1) + "%" : "--"}</div>
      <div>errors: {r.errors.length ? r.errors.join(", ") : "none"}</div>
    </div>
  );
}

export default function RepTimeline({ reps }) {
  const [selected, setSelected] = useState(null);
  const data = reps.map((r) => ({
    rep: r.rep_number,
    form_score: r.form_score,
    duration: (r.tempo_eccentric_s || 0) + (r.tempo_isometric_s || 0) + (r.tempo_concentric_s || 0),
    asymmetry_pct: r.asymmetry_pct,
    errors: (r.form_errors || []).map((e) => e.error_code),
    compensation: r.compensation_detected,
  }));

  return (
    <div className="chart-card">
      <h3>Per-Rep Timeline <span className="hint">(click a bar)</span></h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis dataKey="rep" stroke="#aaa" />
          <YAxis domain={[0, 100]} stroke="#aaa" />
          <Tooltip content={<RepTooltip />} />
          <Bar dataKey="form_score" cursor="pointer"
               onClick={(d) => setSelected(d && d.payload)}>
            {data.map((d, i) => <Cell key={i} fill={scoreColor(d.form_score)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {selected && (
        <div className="rep-detail">
          Rep {selected.rep}: {selected.compensation
            ? "⚠ compensation detected during this rep"
            : "no compensation flagged"}
        </div>
      )}
    </div>
  );
}
