// MediaPipe Pose connections (subset covering torso, arms, legs, feet) and a
// canvas draw helper. Landmarks are the {id, x_norm, y_norm, visibility} list
// from the WebSocket frame message.

export const POSE_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], // shoulders + arms
  [11, 23], [12, 24], [23, 24],                     // torso
  [23, 25], [25, 27], [24, 26], [26, 28],           // legs
  [27, 29], [29, 31], [27, 31],                     // left foot
  [28, 30], [30, 32], [28, 32],                     // right foot
];

const VISIBILITY_THRESHOLD = 0.5;

// Draw the skeleton. `errorIds` is a Set of landmark ids involved in an active
// error (drawn red); everything else is green.
export function drawSkeleton(ctx, landmarks, width, height, errorIds = new Set()) {
  ctx.clearRect(0, 0, width, height);
  if (!landmarks || landmarks.length === 0) return;

  const byId = new Map(landmarks.map((lm) => [lm.id, lm]));

  // Connections (white lines).
  ctx.lineWidth = 2;
  ctx.strokeStyle = "rgba(255,255,255,0.85)";
  for (const [a, b] of POSE_CONNECTIONS) {
    const la = byId.get(a);
    const lb = byId.get(b);
    if (!la || !lb) continue;
    if (la.visibility <= VISIBILITY_THRESHOLD || lb.visibility <= VISIBILITY_THRESHOLD) continue;
    ctx.beginPath();
    ctx.moveTo(la.x_norm * width, la.y_norm * height);
    ctx.lineTo(lb.x_norm * width, lb.y_norm * height);
    ctx.stroke();
  }

  // Landmark dots (green normally, red if involved in an active error).
  for (const lm of landmarks) {
    if (lm.visibility <= VISIBILITY_THRESHOLD) continue;
    ctx.beginPath();
    ctx.arc(lm.x_norm * width, lm.y_norm * height, 5, 0, 2 * Math.PI);
    ctx.fillStyle = errorIds.has(lm.id) ? "#ff3b3b" : "#28e07a";
    ctx.fill();
  }
}
