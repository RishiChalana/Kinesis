import { useEffect, useState } from "react";
import { getCommonErrors, getSessions, getTempoHistory, getUserId, isAuthed } from "../api";
import FormTrendChart from "../components/charts/FormTrendChart";
import AsymmetryChart from "../components/charts/AsymmetryChart";
import TempoChart from "../components/charts/TempoChart";
import ErrorFrequencyChart from "../components/charts/ErrorFrequencyChart";

export default function Dashboard() {
  const [sessions, setSessions] = useState([]);
  const [tempo, setTempo] = useState([]);
  const [errors, setErrors] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthed()) {
      setLoading(false);
      return;
    }
    const uid = getUserId();
    Promise.all([getSessions(), getTempoHistory(uid), getCommonErrors(uid)])
      .then(([s, t, e]) => {
        setSessions(s);
        setTempo(t);
        setErrors(e);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (!isAuthed()) return <div className="page"><p>Log in (top right) to see your dashboard.</p></div>;
  if (loading) return <div className="page"><p>Loading…</p></div>;
  if (error) return <div className="page"><p className="err">Error: {error}</p></div>;

  return (
    <div className="page">
      <h1>Dashboard</h1>
      {sessions.length === 0 && <p>No sessions yet — complete a workout to see charts.</p>}
      <div className="chart-grid">
        <FormTrendChart sessions={sessions} />
        <AsymmetryChart sessions={sessions} />
        <TempoChart tempo={tempo} />
        <ErrorFrequencyChart errors={errors} />
      </div>
    </div>
  );
}
