"""TRACK A — Movement signature fingerprinting via DTW (Phase 8).

After enough good reps, KINESIS builds a statistical model of how a specific
user moves through an exercise — their personal kinematic fingerprint. New reps
are compared to THIS user's baseline using Dynamic Time Warping (robust to reps
taking different amounts of time), not to a generic population standard.
"""

import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

TRAJECTORY_LENGTH = 50
MAX_BASELINE_REPS = 10
GOOD_REP_FORM_SCORE = 85
DEVIATION_SIGMA = 2.5


def dtw_distance(a, b):
    """DTW distance between two 1-D angle trajectories. fastdtw feeds individual
    elements to the dist function; scipy's euclidean needs 1-D input, so each
    sequence is shaped as column vectors (N, 1)."""
    a2 = np.asarray(a, dtype=float).reshape(-1, 1)
    b2 = np.asarray(b, dtype=float).reshape(-1, 1)
    distance, _ = fastdtw(a2, b2, dist=euclidean)
    return distance


class RepTrajectory:
    """Collects (angle, timestamp) pairs during a rep, then resamples the
    variable-length angle sequence to a fixed TRAJECTORY_LENGTH points so reps
    of different durations are directly comparable."""

    def __init__(self):
        self.samples = []

    def add(self, angle, timestamp):
        if angle is not None:
            self.samples.append((float(angle), timestamp))

    def normalise(self, length=TRAJECTORY_LENGTH):
        if len(self.samples) < 2:
            return None
        angles = np.array([a for a, _ in self.samples], dtype=float)
        old_x = np.linspace(0.0, 1.0, len(angles))
        new_x = np.linspace(0.0, 1.0, length)
        return np.interp(new_x, old_x, angles)


class SignatureModel:
    def __init__(self, user_id, exercise):
        self.user_id = user_id
        self.exercise = exercise
        self.baseline_trajectories = []          # list of 50-point arrays
        self.baseline_mean = None                # mean trajectory (50,)
        self.baseline_variability = None         # mean pairwise DTW distance
        self.baseline_std = None                 # std of pairwise DTW distances

    def add_good_rep(self, trajectory, form_score):
        """Keep only well-executed reps (form_score > 85) up to the cap."""
        if (form_score is not None and form_score > GOOD_REP_FORM_SCORE
                and len(self.baseline_trajectories) < MAX_BASELINE_REPS
                and trajectory is not None):
            self.baseline_trajectories.append(np.asarray(trajectory, dtype=float))
            return True
        return False

    def compute_baseline(self):
        """Compute the mean trajectory and the natural variability (mean and
        std of pairwise DTW distances) of this user's baseline reps."""
        if len(self.baseline_trajectories) < 2:
            return False
        stack = np.stack(self.baseline_trajectories)
        self.baseline_mean = np.mean(stack, axis=0)

        dists = []
        n = len(self.baseline_trajectories)
        for i in range(n):
            for j in range(i + 1, n):
                dists.append(dtw_distance(self.baseline_trajectories[i],
                                          self.baseline_trajectories[j]))
        self.baseline_variability = float(np.mean(dists))
        self.baseline_std = float(np.std(dists))
        return True

    def compare(self, trajectory):
        """Compare an incoming rep to the baseline. Fires SIGNATURE_DEVIATION if
        the DTW distance exceeds a 2.5-sigma deviation from the user's norm."""
        if self.baseline_mean is None or trajectory is None:
            return None
        distance = dtw_distance(trajectory, self.baseline_mean)
        threshold = self.baseline_variability + DEVIATION_SIGMA * self.baseline_std
        if distance > threshold:
            return {
                "type": "SIGNATURE_DEVIATION",
                "code": "SIGNATURE_DEVIATION",
                "severity": 2,
                "distance": float(distance),
                "threshold": float(threshold),
                "message": (f"Rep deviates from your movement signature "
                            f"(DTW {distance:.1f} > {threshold:.1f})."),
            }
        return None

    # -- persistence helpers for the movement_signatures table -------------- #
    def to_row(self):
        return {
            "user_id": self.user_id,
            "exercise": self.exercise,
            "baseline_trajectory": self.baseline_mean.tolist()
            if self.baseline_mean is not None else None,
            "baseline_variability": self.baseline_variability,
            "sample_count": len(self.baseline_trajectories),
        }

    def load_row(self, row):
        self.baseline_mean = np.asarray(row["baseline_trajectory"], dtype=float)
        self.baseline_variability = row["baseline_variability"]
        # std is recoverable from stored reps; default to a fraction if absent.
        self.baseline_std = row.get("baseline_std", self.baseline_variability * 0.4)
        return self
