import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSessions, isAuthed } from "../api";

export default function History() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthed()) { setLoading(false); return; }
    getSessions().then(setSessions).finally(() => setLoading(false));
  }, []);

  if (!isAuthed()) return <div className="page"><p>Log in to see your history.</p></div>;
  if (loading) return <div className="page"><p>Loading…</p></div>;

  return (
    <div className="page">
      <h1>Session History</h1>
      <table className="history-table">
        <thead>
          <tr><th>Date</th><th>Exercise</th><th>Avg Form</th><th>Avg AI%</th><th></th></tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.id}>
              <td>{new Date(s.started_at).toLocaleString()}</td>
              <td>{s.exercise}</td>
              <td>{s.avg_form_score != null ? s.avg_form_score.toFixed(0) : "—"}</td>
              <td>{s.avg_asymmetry != null ? s.avg_asymmetry.toFixed(1) : "—"}</td>
              <td><Link to={`/session/${s.id}`}>details →</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
