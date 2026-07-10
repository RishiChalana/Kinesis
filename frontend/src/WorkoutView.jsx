import { useEffect, useRef, useState } from "react";
import AlertStack from "./components/AlertStack";
import RepCounter from "./components/RepCounter";
import { drawSkeleton } from "./skeleton";
import "./WorkoutView.css";

const WS_HOST = "ws://localhost:8000";
const SEND_INTERVAL_MS = 66; // ~15 fps upstream
const ALERT_TTL_MS = 3000;

export default function WorkoutView() {
  const videoRef = useRef(null);
  const hiddenCanvasRef = useRef(null);
  const overlayRef = useRef(null);
  const wsRef = useRef(null);
  const rafRef = useRef(null);
  const streamRef = useRef(null);
  const lastSentRef = useRef(0);
  const alertsRef = useRef(new Map());

  const [sessionId, setSessionId] = useState("demo");
  const [exercise, setExercise] = useState("squat");
  const [connected, setConnected] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const [frame, setFrame] = useState({ rep_count: 0, state: "UP", form_score: null });
  const [alerts, setAlerts] = useState([]);

  // --- webcam ---
  useEffect(() => {
    let cancelled = false;
    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: "user", frameRate: { ideal: 30 } },
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (err) {
        if (err.name === "NotAllowedError" || err.name === "NotFoundError") {
          setCameraError("Enable camera permission to start a workout.");
        } else {
          setCameraError(`Camera error: ${err.message}`);
        }
      }
    }
    startCamera();
    return () => {
      cancelled = true;
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // --- alert cleanup (drop alerts not seen for 3s) ---
  useEffect(() => {
    const id = setInterval(() => {
      const now = Date.now();
      let changed = false;
      for (const [key, a] of alertsRef.current) {
        if (now - a.lastSeen > ALERT_TTL_MS) {
          alertsRef.current.delete(key);
          changed = true;
        }
      }
      if (changed) setAlerts(Array.from(alertsRef.current.values()));
    }, 500);
    return () => clearInterval(id);
  }, []);

  function refreshAlert(key, type, title, message) {
    alertsRef.current.set(key, { key, type, title, message, lastSeen: Date.now() });
  }

  function handleMessage(msg) {
    setFrame(msg);

    const ov = overlayRef.current;
    if (ov) drawSkeleton(ov.getContext("2d"), msg.landmarks, ov.width, ov.height);

    // Tracking lost: person out of frame for too long. Distinct grey alert;
    // the skeleton simply stops updating rather than freezing on stale data.
    if (msg.state === "TRACKING_LOST") {
      refreshAlert("tracking", "tracking", "Tracking lost",
        "We lost you — step back into frame.");
    }

    for (const e of msg.active_errors || []) {
      refreshAlert(`error:${e.code}`, "error", "Form Error", e.message);
    }
    for (const c of msg.compensation_events || []) {
      refreshAlert(`comp:${c.code}`, "compensation", `Compensation — ${c.muscle}`, c.message);
    }
    if (msg.asymmetry && (msg.asymmetry.risk === "WARNING" || msg.asymmetry.risk === "HIGH")) {
      const a = msg.asymmetry;
      refreshAlert("asym", "asymmetry", `Asymmetry ${a.risk}`,
        `${a.ai_pct.toFixed(1)}% — ${a.dominant_side} side higher`);
    }
    setAlerts(Array.from(alertsRef.current.values()));
  }

  // --- rAF frame-send loop ---
  function loop(t) {
    const ws = wsRef.current;
    const video = videoRef.current;
    if (ws && ws.readyState === WebSocket.OPEN && video && video.readyState >= 2) {
      if (t - lastSentRef.current >= SEND_INTERVAL_MS) {
        lastSentRef.current = t;
        const c = hiddenCanvasRef.current;
        const ctx = c.getContext("2d");
        ctx.drawImage(video, 0, 0, c.width, c.height);
        const b64 = c.toDataURL("image/jpeg", 0.6);
        ws.send(JSON.stringify({ frame: b64, session_id: sessionId, exercise }));
      }
    }
    rafRef.current = requestAnimationFrame(loop);
  }

  function connect() {
    if (wsRef.current) return;
    const ws = new WebSocket(`${WS_HOST}/ws/${sessionId}`);
    ws.onopen = () => {
      setConnected(true);
      rafRef.current = requestAnimationFrame(loop);
    };
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "ping") {
        ws.send(JSON.stringify({ type: "pong" }));
        return;
      }
      handleMessage(msg);
    };
    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    wsRef.current = ws;
  }

  function disconnect() {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (wsRef.current) wsRef.current.close();
    wsRef.current = null;
    setConnected(false);
  }

  useEffect(() => () => disconnect(), []); // cleanup on unmount

  return (
    <div className="workout">
      <header className="workout-header">
        <h1>KINESIS</h1>
        <div className="controls">
          <input value={sessionId} onChange={(e) => setSessionId(e.target.value)}
                 disabled={connected} placeholder="session id" />
          <select value={exercise} onChange={(e) => setExercise(e.target.value)}
                  disabled={connected}>
            <option value="squat">Squat</option>
            <option value="deadlift">Deadlift</option>
            <option value="bicep_curl">Bicep Curl</option>
            <option value="pushup">Push-up</option>
            <option value="lunge">Lunge</option>
          </select>
          {connected ? (
            <button className="btn stop" onClick={disconnect}>Stop</button>
          ) : (
            <button className="btn start" onClick={connect}>Start</button>
          )}
          <span className={`dot ${connected ? "on" : "off"}`} />
        </div>
      </header>

      <div className="stage">
        <div className="video-container">
          <video ref={videoRef} autoPlay playsInline muted className="feed" />
          <canvas ref={overlayRef} width={640} height={480} className="overlay" />
          {cameraError && <div className="camera-error">{cameraError}</div>}
        </div>

        <RepCounter repCount={frame.rep_count} state={frame.state}
                    formScore={frame.form_score} />
      </div>

      <AlertStack alerts={alerts} />
      <canvas ref={hiddenCanvasRef} width={640} height={480} style={{ display: "none" }} />
    </div>
  );
}
