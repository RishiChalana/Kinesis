"""TRACK A — Joint angle engine (Phase 4).

The mathematical core every form feature depends on. Given three points where
B is the vertex (the joint), returns the angle A-B-C in degrees.
"""

import numpy as np


def calculate_angle(a, b, c):
    """Angle at vertex b, formed by points a and c. Args are dicts {x, y} in
    pixel coordinates. Returns float degrees.

    For a knee angle: a = hip, b = knee, c = ankle. Standing ~ 170-180 deg,
    deep squat bottom ~ 65-90 deg.
    """
    # Step 1 — two vectors pointing from the joint outward along each bone.
    v1 = (a["x"] - b["x"], a["y"] - b["y"])
    v2 = (c["x"] - b["x"], c["y"] - b["y"])

    # Step 2 — dot product.
    dot = v1[0] * v2[0] + v1[1] * v2[1]

    # Step 3 — magnitudes, with a guard against division by zero.
    mag1 = np.sqrt(v1[0] ** 2 + v1[1] ** 2)
    mag2 = np.sqrt(v2[0] ** 2 + v2[1] ** 2)
    if mag1 == 0 or mag2 == 0:
        return 180.0

    # Step 4 — cosine, clamped so float error can't push arccos out of domain.
    cos_angle = dot / (mag1 * mag2)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)

    # Step 5 — angle in degrees.
    return float(np.degrees(np.arccos(cos_angle)))
