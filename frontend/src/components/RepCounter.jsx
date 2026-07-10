// Large centered rep counter with a CSS scale pop on increment, current state,
// and the form-score arc gauge.

import { useEffect, useRef, useState } from "react";
import FormGauge from "./FormGauge";

export default function RepCounter({ repCount, state, formScore }) {
  const [pop, setPop] = useState(false);
  const prev = useRef(repCount);

  useEffect(() => {
    if (repCount > prev.current) {
      setPop(true);
      const t = setTimeout(() => setPop(false), 300);
      prev.current = repCount;
      return () => clearTimeout(t);
    }
    prev.current = repCount;
  }, [repCount]);

  return (
    <div className="rep-counter">
      <div className={`rep-count ${pop ? "pop" : ""}`}>{repCount}</div>
      <div className="rep-state">{state || "—"}</div>
      <FormGauge score={formScore} />
    </div>
  );
}
