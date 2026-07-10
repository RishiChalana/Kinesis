// Error frequency: bar per error code; clicking a bar opens the corrective modal.
import { useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { getCorrective } from "../../api";
import CorrectiveModal from "../CorrectiveModal";

export default function ErrorFrequencyChart({ errors }) {
  const [corrective, setCorrective] = useState(null);

  async function openCorrective(bar) {
    if (!bar || !bar.error_code) return;
    try {
      setCorrective(await getCorrective(bar.error_code));
    } catch {
      setCorrective({
        error_code: bar.error_code, cause: "No corrective on file.",
        cues: [], exercises: [], reference: "-",
      });
    }
  }

  return (
    <div className="chart-card">
      <h3>Most Common Form Errors <span className="hint">(click a bar)</span></h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={errors} layout="vertical" margin={{ left: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis type="number" stroke="#aaa" allowDecimals={false} />
          <YAxis type="category" dataKey="error_code" width={130} stroke="#aaa" />
          <Tooltip contentStyle={{ background: "#1b1b20", border: "1px solid #333" }} />
          <Bar dataKey="count" fill="#ef4444" cursor="pointer"
               onClick={(d) => openCorrective(d && d.payload)} />
        </BarChart>
      </ResponsiveContainer>
      <CorrectiveModal corrective={corrective} onClose={() => setCorrective(null)} />
    </div>
  );
}
