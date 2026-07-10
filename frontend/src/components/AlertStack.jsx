// Fixed top-right alert stack. Colour-coded by type:
//   red    = form error
//   purple = compensation event
//   orange = asymmetry warning
//   grey   = tracking lost (person out of frame)
// Alerts auto-dismiss 3s after their source clears from incoming frames.

const TYPE_CLASS = {
  error: "alert-error",
  compensation: "alert-compensation",
  asymmetry: "alert-asymmetry",
  tracking: "alert-tracking",
};

export default function AlertStack({ alerts }) {
  return (
    <div className="alert-stack">
      {alerts.map((a) => (
        <div key={a.key} className={`alert ${TYPE_CLASS[a.type]}`}>
          <div className="alert-title">{a.title}</div>
          <div className="alert-msg">{a.message}</div>
        </div>
      ))}
    </div>
  );
}
