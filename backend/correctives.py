"""TRACK B — Corrective exercise knowledge base (Phase 8).

A plain Python dict is a valid, defensible "recommendation engine" at this
scope: the mapping error_code -> {cause, cues, exercises, reference} is small,
static, and read-only. It would only warrant a graph database (e.g. Neo4j) if we
needed to traverse relationships between causes, muscles, and exercises — which
we don't here. Easy to maintain: add an entry, done.
"""

CORRECTIVES = {
    "KNEE_VALGUS": {
        "cause": "Hip abductor weakness (Gluteus Medius)",
        "cues": ["Push knees outward", "Imagine spreading the floor apart"],
        "exercises": ["Clamshells 3x15", "Side-lying hip abduction 3x15", "Monster walks 3x20"],
        "reference": "Mauntel et al. 2017",
    },
    "KNEE_CAVE": {
        "cause": "Hip abductor weakness / poor motor control",
        "cues": ["Drive knees over toes", "Screw feet into the floor"],
        "exercises": ["Banded squats 3x12", "Clamshells 3x15", "Lateral band walks 3x20"],
        "reference": "Powers 2010",
    },
    "TORSO_LEAN": {
        "cause": "Weak anterior core / limited ankle dorsiflexion",
        "cues": ["Chest up", "Brace the core before descending"],
        "exercises": ["Goblet squats 3x10", "Front planks 3x30s", "Ankle mobility drills 3x10"],
        "reference": "Escamilla 2001",
    },
    "SHALLOW_DEPTH": {
        "cause": "Limited hip/ankle mobility or depth confidence",
        "cues": ["Sit down between the hips", "Reach hip crease below the knee"],
        "exercises": ["Box squats to depth 3x8", "Deep goblet squat holds 3x30s", "Ankle rockers 3x10"],
        "reference": "NSCA squat guidelines",
    },
    "HEEL_RISE": {
        "cause": "Restricted ankle dorsiflexion",
        "cues": ["Keep heels planted", "Spread weight across the whole foot"],
        "exercises": ["Weighted ankle dorsiflexion 3x12", "Calf stretches 3x30s", "Heel-elevated squats 3x10"],
        "reference": "Kim et al. 2015",
    },
    "BUTT_WINK": {
        "cause": "Posterior pelvic tilt at depth (hamstring/hip mobility)",
        "cues": ["Maintain a neutral spine", "Stop just above where the pelvis tucks"],
        "exercises": ["90/90 hip stretch 3x30s", "Hamstring mobility 3x10", "Tempo squats to threshold 3x6"],
        "reference": "Schoenfeld 2010",
    },
    "ELBOW_FLARE": {
        "cause": "Pectoral fatigue shifting load to triceps",
        "cues": ["Tuck elbows ~45 degrees", "Bend the bar / spread the floor"],
        "exercises": ["Push-up negatives 3x6", "Close-grip push-ups 3x8", "Serratus wall slides 3x12"],
        "reference": "NSCA press mechanics",
    },
    "HIP_SHIFT": {
        "cause": "Bilateral strength/mobility asymmetry",
        "cues": ["Even pressure through both feet", "Drive up symmetrically"],
        "exercises": ["Bulgarian split squats 3x10/side", "Single-leg RDL 3x10/side", "Tempo squats 3x6"],
        "reference": "Bishop et al. 2018",
    },
    "BAR_PATH_DRIFT": {
        "cause": "Lat weakness — bar drifts away from the body in the hinge",
        "cues": ["Keep the bar against the legs", "Pull the bar into you with the lats"],
        "exercises": ["Straight-arm pulldowns 3x12", "Romanian deadlifts 3x8", "Bent-over rows 3x10"],
        "reference": "Escamilla 2000",
    },
    "WRIST_EXTENSION": {
        "cause": "Grip/forearm weakness during the curl",
        "cues": ["Keep wrists neutral", "Squeeze the bar, don't let the wrist bend back"],
        "exercises": ["Wrist curls 3x15", "Reverse curls 3x12", "Farmer holds 3x30s"],
        "reference": "NSCA arm training",
    },
}


def get_corrective(error_code: str):
    return CORRECTIVES.get(error_code.strip().upper())
