"""MediaPipe Pose landmark name -> id mapping (Phase 6).

Kept in the backend so the time-series /angles endpoint can accept human
names like LEFT_KNEE without importing the heavyweight mediapipe package.
Matches mediapipe.solutions.pose.PoseLandmark.
"""

POSE_LANDMARK_IDS = {
    "NOSE": 0,
    "LEFT_EYE_INNER": 1,
    "LEFT_EYE": 2,
    "LEFT_EYE_OUTER": 3,
    "RIGHT_EYE_INNER": 4,
    "RIGHT_EYE": 5,
    "RIGHT_EYE_OUTER": 6,
    "LEFT_EAR": 7,
    "RIGHT_EAR": 8,
    "MOUTH_LEFT": 9,
    "MOUTH_RIGHT": 10,
    "LEFT_SHOULDER": 11,
    "RIGHT_SHOULDER": 12,
    "LEFT_ELBOW": 13,
    "RIGHT_ELBOW": 14,
    "LEFT_WRIST": 15,
    "RIGHT_WRIST": 16,
    "LEFT_PINKY": 17,
    "RIGHT_PINKY": 18,
    "LEFT_INDEX": 19,
    "RIGHT_INDEX": 20,
    "LEFT_THUMB": 21,
    "RIGHT_THUMB": 22,
    "LEFT_HIP": 23,
    "RIGHT_HIP": 24,
    "LEFT_KNEE": 25,
    "RIGHT_KNEE": 26,
    "LEFT_ANKLE": 27,
    "RIGHT_ANKLE": 28,
    "LEFT_HEEL": 29,
    "RIGHT_HEEL": 30,
    "LEFT_FOOT_INDEX": 31,
    "RIGHT_FOOT_INDEX": 32,
}


def resolve_landmark(landmark: str) -> int | None:
    """Accept either a landmark name (LEFT_KNEE) or a numeric id string."""
    if landmark is None:
        return None
    key = landmark.strip().upper()
    if key in POSE_LANDMARK_IDS:
        return POSE_LANDMARK_IDS[key]
    if key.isdigit() and 0 <= int(key) <= 32:
        return int(key)
    return None
