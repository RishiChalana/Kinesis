# KINESIS — Methodology

The technical basis for KINESIS's four core analyses. Each section states the
computation, the thresholds used, and the biomechanical or statistical
justification. Implementation references point at the source modules.

---

## 1. Personalised biomechanical calibration

**Problem.** Population-average form thresholds (e.g. "squat to 90° knee flexion")
are biomechanically wrong for individuals. A lifter with long femurs relative to
their torso physically cannot reach the same depth/lean as a short-femured
lifter without shifting the torso forward. Penalising them against a generic
threshold gives false feedback.

**Segment-ratio computation** (`ml/calibration.py`). During a 45-second guided
sequence the system measures, per frame, pixel distances between landmark pairs
and takes the **median** across frames (robust to per-frame detection jitter):

- Torso length `torso_px` = |shoulder_midpoint_y − hip_midpoint_y|
- Femur length `femur_px` = |hip_midpoint_y − knee_midpoint_y|
- **Torso-to-femur ratio** = `torso_px / femur_px`

Pixel distances (not normalised coordinates) are used during calibration because
they are taken from a single standing frame at fixed camera distance, so scale is
constant; normalised coordinates would fold in frame-size/perspective effects.

**Personalised thresholds.** From the calibration reps:

- *Natural squat depth* = median of the per-rep minimum knee angles (deepest
  point of each of 3 squats). The user's depth threshold becomes
  `natural_depth + 5°` — not a fixed 90°.
- *Forward-lean allowance* = torso lean (shoulder–hip vs. vertical) at the
  deepest squat point, `+ 10°` tolerance.
- *Natural hinge angle* = median of per-rep minimum hip angles during the hip
  hinge.

These are stored in `user_profiles` and loaded into `KinesisPipeline` at session
start (`get_exercise_thresholds`). If a user is uncalibrated, the system falls
back to population defaults and flags it — it never blocks.

**References.** Powers, C.M. (2010) and Escamilla, R.F. (2001) on how limb-segment
proportions affect squat mechanics; the NSCA squat-biomechanics guidance on
"hip crease below parallel."

---

## 2. Compensatory movement detection

**Principle.** When a primary mover fatigues, the body recruits secondary
muscles, producing a *correlated multi-joint signature* that is invisible when
joints are examined in isolation. KINESIS detects the pattern across a temporal
window, not a single-frame angle. Implementation: `ml/compensation.py`.

### Signature 1 — Bicep-curl shoulder compensation (intra-rep)

As the biceps approach failure the anterior deltoid assists: the shoulder rises
and the elbow drifts forward *together*.

- `shoulder_rise = baseline_shoulder_y − current_shoulder_y`
- `elbow_drift = |current_elbow_x − baseline_elbow_x|`
- **Fires** `SHOULDER_COMPENSATION` when `shoulder_rise > 0.04 × torso_height`
  **AND** `elbow_drift > 0.05 × shoulder_width`, sustained **≥ 5 consecutive
  frames**.

*Justification.* Thresholds are scaled to the person's own torso height and
shoulder width, so they're proportion-independent. The 5-frame persistence
requirement rejects momentary detection noise — a genuine shrug lasts.

### Signature 2 — Squat glute fatigue (inter-rep trend)

As the gluteus maximus fatigues, the lumbar extensors take over hip extension,
so torso lean at the bottom **increases progressively across reps**.

- Store `torso_lean_angle` at the bottom of every rep.
- Fit `numpy.polyfit([1..n], lean_values, 1)`; **fires** `GLUTE_COMPENSATION`
  when **slope > +2.0°/rep** with **n ≥ 4** reps.

*Justification.* The signal is the *trend*, not any single value — a naturally
forward-leaning lifter is fine; a lifter whose lean climbs rep over rep is
fatiguing. Linear regression over ≥4 points separates trend from noise.

### Signature 3 — Push-up pectoral fatigue (inter-rep trend)

As the pectorals fatigue, elbow flare increases to shift load toward the triceps.

- Compute `elbow_flare_angle` at the bottom of each push-up.
- Fit a line; **fires** `PECTORAL_COMPENSATION` when **slope > +3.0°/rep** with
  **n ≥ 4**.

Every fired event carries `{type: COMPENSATION, code, severity: 3, message,
muscle, recommendation}` — severity 3 distinguishes fatigue signatures from
ordinary form errors. Detectors reset between sets (rest restores capacity).

---

## 3. Movement-signature fingerprinting (DTW)

**Goal.** Compare each rep to *this user's own* movement pattern, not a generic
template. Two correct reps by the same person differ in duration but share a
*shape* (how the joint angle traverses the range). Implementation:
`ml/signature.py`.

**Trajectory normalisation.** Each rep is collected as `(angle, timestamp)`
samples and resampled to a fixed **50 points** with `numpy.interp`, so reps of
different durations are directly comparable.

**Dynamic Time Warping.** DTW aligns two time-series that differ in speed and
returns a distance that is small for similar shapes and large for divergent ones
— unlike Euclidean distance, which fails when sequences differ in length/tempo.
KINESIS uses the **`fastdtw`** library (approximate DTW, ~O(n) vs O(n²)) with
`scipy.spatial.distance.euclidean` as the point metric.

**Personal baseline.** Collect up to the 10 best reps (`form_score > 85`).
Compute the mean 50-point trajectory and the **mean and standard deviation of the
pairwise DTW distances** among baseline reps — i.e. the user's natural movement
variability.

**Deviation test.** For a new rep, `distance = DTW(rep, baseline_mean)`. **Fires**
`SIGNATURE_DEVIATION` when `distance > baseline_mean + 2.5 × baseline_std` — a
**2.5-σ** outlier from the user's personal norm (~1% under a normal model),
indicating fatigue, distraction, or form breakdown mid-session. Baselines persist
per user+exercise in `movement_signatures` and load at session start.

**Reference.** `fastdtw` (Salvador & Chan, 2007, "FastDTW: Toward accurate dynamic
time warping in linear time and space"). The 2.5-σ threshold follows the standard
z-score outlier convention.

---

## 4. Bilateral asymmetry & tempo

### Asymmetry Index (`ml/asymmetry.py`)

A standard sports-biomechanics metric comparing the same joint left vs. right in
the same frame (the sides are stored separately, never averaged):

```
AI = |left − right| / ((left + right) / 2) × 100
```

Risk bands: **OK < 10%**, **WARNING 10–15%**, **HIGH > 15%**. An absolute angle
difference matters more at a small joint angle than a large one, which is why a
*percentage* index is used. A sustained same-side average AI > 10% across ≥ 3
consecutive sets escalates to a `BILATERAL_IMBALANCE` alert with directional
info.

### Tempo (`ml/tempo.py`)

Each rep is split into eccentric / isometric / concentric phases using the
transition timestamps from the rep state machine, and scored against
evidence-based target ranges (e.g. squat eccentric 2–4 s, isometric 0.5–1.5 s,
concentric 1–2 s), following NSCA time-under-tension guidance.

---

## 5. Form rules & corrective knowledge base

Form-error → cause → cues → corrective-exercise prescriptions live in
`backend/correctives.py`, each with a cited source. Examples:

- **Knee valgus / knee cave** → hip-abductor (gluteus medius) weakness.
  *Mauntel et al. (2017); Powers (2010).* Correctives: clamshells, side-lying hip
  abduction, monster walks.
- **Excessive torso lean** → weak anterior core / limited ankle dorsiflexion.
  *Escamilla (2001).*
- **Elbow flare (push-up)** → pectoral fatigue shifting load to triceps.
  *NSCA press mechanics.*

The knowledge base is a plain, versioned Python dict — a defensible design at
this scope; it would only warrant a graph database if we needed to traverse
relationships between causes, muscles, and exercises.

---

## Rep counting (supporting method)

Reps are counted by a two-threshold **hysteresis** state machine (`ml/rep_counter.py`):
a rep completes only on a full UP→DOWN→UP cycle, with a minimum 15-frame gap
between state transitions. The dead-band between the down and up thresholds
prevents sensor noise near a single boundary from producing dozens of false
counts.

## Joint-angle computation (supporting method)

Angles are computed from three landmarks (vertex B, arms A and C) via the dot
product of the two bone vectors, with a zero-magnitude guard and
`np.clip(cos, −1, 1)` before `arccos` to prevent floating-point domain errors
(`ml/angles.py`).
