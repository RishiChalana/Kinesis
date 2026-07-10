// Form-score arc gauge: red 0-60, orange 60-80, green 80-100.

function scoreColor(score) {
  if (score == null) return "#555";
  if (score < 60) return "#ff3b3b";
  if (score < 80) return "#ff9f1c";
  return "#28e07a";
}

// Describe a semicircle arc path from `startFrac` to `endFrac` (0..1, left->right).
function arcPath(cx, cy, r, startFrac, endFrac) {
  const a0 = Math.PI + startFrac * Math.PI;
  const a1 = Math.PI + endFrac * Math.PI;
  const x0 = cx + r * Math.cos(a0);
  const y0 = cy + r * Math.sin(a0);
  const x1 = cx + r * Math.cos(a1);
  const y1 = cy + r * Math.sin(a1);
  return `M ${x0} ${y0} A ${r} ${r} 0 0 1 ${x1} ${y1}`;
}

export default function FormGauge({ score }) {
  const cx = 90;
  const cy = 90;
  const r = 70;
  const frac = score == null ? 0 : Math.max(0, Math.min(100, score)) / 100;

  return (
    <div className="form-gauge">
      <svg width="180" height="110" viewBox="0 0 180 110">
        <path d={arcPath(cx, cy, r, 0, 1)} stroke="#2a2a2a" strokeWidth="14"
              fill="none" strokeLinecap="round" />
        {score != null && (
          <path d={arcPath(cx, cy, r, 0, frac)} stroke={scoreColor(score)}
                strokeWidth="14" fill="none" strokeLinecap="round" />
        )}
        <text x="90" y="86" textAnchor="middle" fontSize="30" fontWeight="700"
              fill={scoreColor(score)}>
          {score == null ? "--" : Math.round(score)}
        </text>
      </svg>
      <div className="form-gauge-label">FORM</div>
    </div>
  );
}
