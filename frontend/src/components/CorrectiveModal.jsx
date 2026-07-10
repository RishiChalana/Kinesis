// Modal showing the corrective prescription for a form-error code.
export default function CorrectiveModal({ corrective, onClose }) {
  if (!corrective) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        <h2>{corrective.error_code}</h2>
        <p className="modal-cause"><strong>Likely cause:</strong> {corrective.cause}</p>

        <h4>Cues</h4>
        <ul>{corrective.cues.map((c, i) => <li key={i}>{c}</li>)}</ul>

        <h4>Corrective exercises</h4>
        <ul>{corrective.exercises.map((e, i) => <li key={i}>{e}</li>)}</ul>

        <p className="modal-ref">Reference: {corrective.reference}</p>
      </div>
    </div>
  );
}
