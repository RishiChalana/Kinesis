import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getSessionDetail, isAuthed } from "../api";
import RepTimeline from "../components/charts/RepTimeline";

export default function SessionDetail() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isAuthed()) return;
    getSessionDetail(id).then(setDetail).catch((e) => setError(e.message));
  }, [id]);

  if (!isAuthed()) return <div className="page"><p>Log in to view this session.</p></div>;
  if (error) return <div className="page"><p className="err">Error: {error}</p></div>;
  if (!detail) return <div className="page"><p>Loading…</p></div>;

  // Flatten reps across all sets into a single ordered list.
  const reps = detail.sets.flatMap((s) => s.reps);

  return (
    <div className="page">
      <h1>Session #{detail.id} — {detail.exercise}</h1>
      <p>
        Avg form: {detail.avg_form_score != null ? detail.avg_form_score.toFixed(0) : "—"} ·
        Avg AI: {detail.avg_asymmetry != null ? detail.avg_asymmetry.toFixed(1) + "%" : "—"} ·
        {detail.sets.length} sets · {reps.length} reps
      </p>
      {reps.length ? <RepTimeline reps={reps} /> : <p>No reps recorded.</p>}
    </div>
  );
}
