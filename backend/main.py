"""KINESIS backend API (Phase 3).

Phase 2 in-memory stores are replaced with real DB writes. Auth endpoints
(register/login) issue JWTs; workout endpoints are protected and derive the
user_id from the token, never from the request body.
"""

import asyncio
import json
import time
from datetime import datetime, timezone

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.auth import (
    create_access_token,
    get_current_user,
    get_user_id_from_token,
    hash_password,
    verify_password,
)
from backend.connection_manager import ConnectionManager
from backend.correctives import CORRECTIVES, get_corrective
from backend.database import SessionLocal, get_db
from backend.frame_processor import (
    FRAME_EXECUTOR,
    close_session,
    get_processing_session,
    process_frame,
)
from backend.landmark_store import LandmarkBuffer
from backend.landmarks import resolve_landmark
from backend.models import (
    FormError,
    LandmarkFrame,
    MovementSignature,
    Rep,
    Set,
    User,
    UserProfile,
    Workout,
)

# Heartbeat timing (seconds).
HEARTBEAT_IDLE_SECONDS = 10.0
HEARTBEAT_PONG_TIMEOUT_SECONDS = 5.0

app = FastAPI(title="KINESIS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Pydantic models
# --------------------------------------------------------------------------- #
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SessionStart(BaseModel):
    exercise: str
    target_sets: int = Field(gt=0)
    reps_per_set: int = Field(gt=0)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    exercise: str
    started_at: datetime
    ended_at: datetime | None = None
    avg_form_score: float | None = None
    avg_asymmetry: float | None = None


class SessionStartResponse(BaseModel):
    session_id: int
    websocket_url: str
    exercise: str
    target_sets: int
    reps_per_set: int
    started_at: datetime


class FormErrorCreate(BaseModel):
    code: str
    severity: str | None = None
    frame_count: int | None = None
    frames_total: int | None = None


class RepCreate(BaseModel):
    set_number: int
    rep_number: int
    form_score: float | None = None
    tempo_eccentric_s: float | None = None
    tempo_concentric_s: float | None = None
    tempo_isometric_s: float | None = None
    left_angle: float | None = None
    right_angle: float | None = None
    asymmetry_pct: float | None = None
    compensation_detected: bool | None = None
    errors: list[FormErrorCreate] = Field(default_factory=list)


class RepIdResponse(BaseModel):
    rep_id: int


class SessionEndSummary(BaseModel):
    session_id: int
    ended_at: datetime
    rep_count: int
    avg_form_score: float | None = None
    avg_asymmetry: float | None = None


class ProfileUpsert(BaseModel):
    torso_femur_ratio: float | None = None
    shoulder_width_px: float | None = None
    hip_width_px: float | None = None
    squat_depth_threshold: float | None = None
    squat_lean_threshold: float | None = None
    natural_hinge_angle: float | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    torso_femur_ratio: float | None = None
    shoulder_width_px: float | None = None
    hip_width_px: float | None = None
    squat_depth_threshold: float | None = None
    squat_lean_threshold: float | None = None
    natural_hinge_angle: float | None = None
    calibrated_at: datetime | None = None


class FormErrorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    error_code: str
    severity: str | None = None
    frame_count: int | None = None
    frames_total: int | None = None


class RepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rep_number: int
    form_score: float | None = None
    tempo_eccentric_s: float | None = None
    tempo_concentric_s: float | None = None
    tempo_isometric_s: float | None = None
    left_angle: float | None = None
    right_angle: float | None = None
    asymmetry_pct: float | None = None
    compensation_detected: bool | None = None
    form_errors: list[FormErrorOut] = Field(default_factory=list)


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    set_number: int
    avg_form_score: float | None = None
    reps: list[RepOut] = Field(default_factory=list)


class SessionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    exercise: str
    started_at: datetime
    ended_at: datetime | None = None
    avg_form_score: float | None = None
    avg_asymmetry: float | None = None
    sets: list[SetOut] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.get("/")
def root():
    return {"status": "KINESIS backend running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id))


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
@app.get("/users/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# --------------------------------------------------------------------------- #
# Calibration profile (upsert / fetch)
# --------------------------------------------------------------------------- #
@app.post("/users/{user_id}/profile", response_model=ProfileResponse)
def upsert_profile(
    user_id: int,
    payload: ProfileUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot modify another user's profile")

    profile = db.scalar(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    values = payload.model_dump()
    if profile is None:
        profile = UserProfile(user_id=user_id, **values)  # insert
        db.add(profile)
    else:
        for key, val in values.items():  # update in place (upsert)
            setattr(profile, key, val)
    profile.calibrated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile


@app.get("/users/{user_id}/profile", response_model=ProfileResponse)
def get_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot read another user's profile")
    profile = db.scalar(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    if profile is None:
        # Clean 404 so the calibration engine's fallback path can rely on it.
        raise HTTPException(status_code=404, detail="No calibration profile yet")
    return profile


# --------------------------------------------------------------------------- #
# Sessions (protected — user_id comes from the token, not the body)
# --------------------------------------------------------------------------- #
def _owned_workout(session_id: int, current_user: User, db: Session) -> Workout:
    """Fetch a workout, 404 if missing or not owned by the caller."""
    workout = db.get(Workout, session_id)
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return workout


@app.post("/sessions/start", response_model=SessionStartResponse, status_code=201)
def start_session(
    payload: SessionStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionStartResponse:
    workout = Workout(user_id=current_user.id, exercise=payload.exercise)
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return SessionStartResponse(
        session_id=workout.id,
        websocket_url=f"/ws/{workout.id}",
        exercise=workout.exercise,
        target_sets=payload.target_sets,
        reps_per_set=payload.reps_per_set,
        started_at=workout.started_at,
    )


@app.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    exercise: str | None = Query(default=None, description="Filter by exercise"),
    limit: int = Query(default=10, gt=0, le=100),
) -> list[Workout]:
    stmt = select(Workout).where(Workout.user_id == current_user.id)
    if exercise is not None:
        stmt = stmt.where(Workout.exercise == exercise)
    stmt = stmt.order_by(Workout.started_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@app.post("/sessions/{session_id}/reps", response_model=RepIdResponse, status_code=201)
def save_rep(
    session_id: int,
    payload: RepCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepIdResponse:
    workout = _owned_workout(session_id, current_user, db)

    # Find-or-create the Set for this set_number within the workout.
    set_row = db.scalar(
        select(Set).where(
            Set.workout_id == workout.id, Set.set_number == payload.set_number
        )
    )
    if set_row is None:
        set_row = Set(workout_id=workout.id, set_number=payload.set_number)
        db.add(set_row)
        db.flush()  # assign set_row.id

    rep = Rep(
        set_id=set_row.id,
        rep_number=payload.rep_number,
        form_score=payload.form_score,
        tempo_eccentric_s=payload.tempo_eccentric_s,
        tempo_concentric_s=payload.tempo_concentric_s,
        tempo_isometric_s=payload.tempo_isometric_s,
        left_angle=payload.left_angle,
        right_angle=payload.right_angle,
        asymmetry_pct=payload.asymmetry_pct,
        compensation_detected=payload.compensation_detected,
    )
    rep.form_errors = [
        FormError(
            error_code=e.code,
            severity=e.severity,
            frame_count=e.frame_count,
            frames_total=e.frames_total,
        )
        for e in payload.errors
    ]
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return RepIdResponse(rep_id=rep.id)


@app.patch("/sessions/{session_id}/end", response_model=SessionEndSummary)
def end_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionEndSummary:
    workout = _owned_workout(session_id, current_user, db)

    # Aggregate across all reps in the session via sets -> reps join.
    rep_stmt = (
        select(
            func.count(Rep.id),
            func.avg(Rep.form_score),
            func.avg(Rep.asymmetry_pct),
        )
        .select_from(Rep)
        .join(Set, Rep.set_id == Set.id)
        .where(Set.workout_id == workout.id)
    )
    rep_count, avg_form, avg_asym = db.execute(rep_stmt).one()

    workout.ended_at = datetime.now(timezone.utc)
    workout.avg_form_score = float(avg_form) if avg_form is not None else None
    workout.avg_asymmetry = float(avg_asym) if avg_asym is not None else None

    # Per-set average form score (dashboard + DB-consistency checks).
    set_avgs = db.execute(
        select(Rep.set_id, func.avg(Rep.form_score))
        .join(Set, Rep.set_id == Set.id)
        .where(Set.workout_id == workout.id)
        .group_by(Rep.set_id)
    ).all()
    for set_id, set_avg in set_avgs:
        set_row = db.get(Set, set_id)
        set_row.avg_form_score = float(set_avg) if set_avg is not None else None

    db.commit()
    db.refresh(workout)

    return SessionEndSummary(
        session_id=workout.id,
        ended_at=workout.ended_at,
        rep_count=rep_count,
        avg_form_score=workout.avg_form_score,
        avg_asymmetry=workout.avg_asymmetry,
    )


@app.get("/sessions/{session_id}/detail", response_model=SessionDetailResponse)
def session_detail(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workout:
    # selectinload for each nested one-to-many level: one extra SELECT ... IN
    # per level (workout -> sets -> reps -> form_errors) = constant 4 queries,
    # never N+1, and no JOIN row-explosion. See explanation in the summary.
    stmt = (
        select(Workout)
        .where(Workout.id == session_id)
        .options(
            selectinload(Workout.sets)
            .selectinload(Set.reps)
            .selectinload(Rep.form_errors)
        )
    )
    workout = db.scalar(stmt)
    if workout is None or workout.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return workout


class AnglePoint(BaseModel):
    timestamp: datetime
    value: float | None


@app.get("/sessions/{session_id}/angles", response_model=list[AnglePoint])
def session_angles(
    session_id: int,
    landmark: str = Query(..., description="Landmark name (e.g. LEFT_KNEE) or id"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AnglePoint]:
    """Time-series of one landmark's y_norm trajectory across a session, for
    Recharts. Reads the TimescaleDB hypertable ordered by time."""
    _owned_workout(session_id, current_user, db)  # ownership + existence check

    landmark_id = resolve_landmark(landmark)
    if landmark_id is None:
        raise HTTPException(status_code=422, detail=f"Unknown landmark '{landmark}'")

    stmt = (
        select(LandmarkFrame.time, LandmarkFrame.y_norm)
        .where(
            LandmarkFrame.session_id == session_id,
            LandmarkFrame.landmark_id == landmark_id,
        )
        .order_by(LandmarkFrame.time)
    )
    rows = db.execute(stmt).all()
    return [AnglePoint(timestamp=t, value=v) for t, v in rows]


# --------------------------------------------------------------------------- #
# Corrective engine + dashboard aggregates (Phase 8)
# --------------------------------------------------------------------------- #
@app.get("/correctives/{error_code}")
def get_correctives(error_code: str):
    """Corrective prescription for a form-error code (public reference data)."""
    entry = get_corrective(error_code)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No corrective for '{error_code}'")
    return {"error_code": error_code.upper(), **entry}


@app.get("/correctives")
def list_correctives():
    return sorted(CORRECTIVES.keys())


class ErrorCount(BaseModel):
    error_code: str
    count: int


@app.get("/users/{user_id}/common-errors", response_model=list[ErrorCount])
def common_errors(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ErrorCount]:
    """Top 8 form-error codes by frequency for a user, sorted descending."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot read another user's errors")
    stmt = (
        select(FormError.error_code, func.count(FormError.id).label("n"))
        .select_from(FormError)
        .join(Rep, FormError.rep_id == Rep.id)
        .join(Set, Rep.set_id == Set.id)
        .join(Workout, Set.workout_id == Workout.id)
        .where(Workout.user_id == user_id)
        .group_by(FormError.error_code)
        .order_by(func.count(FormError.id).desc())
        .limit(8)
    )
    return [ErrorCount(error_code=code, count=n) for code, n in db.execute(stmt).all()]


class TempoHistoryPoint(BaseModel):
    session_id: int
    date: datetime
    eccentric_s: float | None
    isometric_s: float | None
    concentric_s: float | None


@app.get("/users/{user_id}/tempo-history", response_model=list[TempoHistoryPoint])
def tempo_history(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TempoHistoryPoint]:
    """Per-session average tempo phase durations, for the tempo chart."""
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot read another user's data")
    stmt = (
        select(
            Workout.id,
            Workout.started_at,
            func.avg(Rep.tempo_eccentric_s),
            func.avg(Rep.tempo_isometric_s),
            func.avg(Rep.tempo_concentric_s),
        )
        .select_from(Workout)
        .join(Set, Set.workout_id == Workout.id)
        .join(Rep, Rep.set_id == Set.id)
        .where(Workout.user_id == user_id)
        .group_by(Workout.id, Workout.started_at)
        .order_by(Workout.started_at)
    )
    out = []
    for sid, date, ecc, iso, con in db.execute(stmt).all():
        out.append(TempoHistoryPoint(
            session_id=sid, date=date,
            eccentric_s=float(ecc) if ecc is not None else None,
            isometric_s=float(iso) if iso is not None else None,
            concentric_s=float(con) if con is not None else None,
        ))
    return out


# --------------------------------------------------------------------------- #
# WebSocket — live pose stream (see docs/websocket_schema.md)
# --------------------------------------------------------------------------- #
manager = ConnectionManager()

# Per-WS-session landmark buffers. Each accumulates 33 rows/frame and flushes a
# batch to the landmark_frames hypertable every FLUSH_EVERY_FRAMES frames — the
# same write path exercised by test_phase6_timescale.py / bench_performance.py,
# now wired into the live stream. Keyed by the WS session_id (the workout id).
_landmark_buffers: dict[str, LandmarkBuffer] = {}


def _flush_buffer(buf: LandmarkBuffer) -> None:
    """Blocking flush — opens a short-lived DB session and bulk-inserts. Runs on
    FRAME_EXECUTOR (off the event loop), never inline in the coroutine."""
    with SessionLocal() as db:
        buf.flush(db)


async def _persist_landmarks(session_id: str, frame_id, landmarks: list[dict]) -> None:
    """Buffer one frame's landmarks and flush a batch when the threshold is hit.
    The flush's DB I/O is offloaded to FRAME_EXECUTOR so it never blocks the
    single asyncio event loop (a synchronous flush here stalls every concurrent
    session; see docs/performance.md). Awaiting keeps this session's flushes
    ordered and the buffer single-threaded — add_frame never runs concurrently
    with a flush for the same buffer. Frames with no landmarks (no person
    tracked) buffer nothing but still count toward the flush cadence."""
    if frame_id is None:
        return
    buf = _landmark_buffers.get(session_id)
    if buf is None:
        buf = LandmarkBuffer(session_id=int(session_id))
        _landmark_buffers[session_id] = buf
    buf.add_frame(frame_id, landmarks)
    if buf.should_flush():
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(FRAME_EXECUTOR, _flush_buffer, buf)


def _close_landmarks(session_id: str) -> None:
    """Flush any remaining buffered rows and drop the buffer on disconnect."""
    buf = _landmark_buffers.pop(session_id, None)
    if buf is not None:
        with SessionLocal() as db:
            buf.flush(db)


def build_frame_message(data: dict) -> dict:
    """Build an outgoing frame message per docs/websocket_schema.md. The CV
    client supplies the computed values; asymmetry/tempo are nested objects
    (Phase 6) and may be null on frames where no rep just completed."""
    return {
        "frame_id": data.get("frame_id"),
        "timestamp": data.get("timestamp", time.time()),
        "rep_count": data.get("rep_count", 0),
        "state": data.get("state", "UP"),
        "form_score": data.get("form_score"),
        "active_errors": data.get("active_errors", []),
        # [{id, x_norm, y_norm, visibility, ...}] — drives the canvas skeleton.
        "landmarks": data.get("landmarks", []),
        "left_angle": data.get("left_angle"),
        "right_angle": data.get("right_angle"),
        # {ai_pct, dominant_side, risk} | null
        "asymmetry": data.get("asymmetry"),
        # {phase, eccentric_s, isometric_s, concentric_s, eccentric_ok,
        #  concentric_ok} | null
        "tempo": data.get("tempo"),
        # [{code, message, muscle, severity}] — Phase 7 compensation signatures.
        "compensation_events": data.get("compensation_events", []),
    }


def _load_signature(sess, user_id):
    """Load this user's stored movement-signature baseline into the live session
    (if one exists). Opens its own short-lived DB session — the WS connection is
    long-lived, so we don't hold a request-scoped session open for it."""
    with SessionLocal() as db:
        row = db.scalar(
            select(MovementSignature).where(
                MovementSignature.user_id == user_id,
                MovementSignature.exercise == sess.exercise,
            )
        )
        sess.signature.user_id = user_id
        if row is not None and row.baseline_trajectory:
            sess.signature.load_row({
                "baseline_trajectory": row.baseline_trajectory,
                "baseline_variability": row.baseline_variability,
            })


def _save_signature(sess, user_id):
    """Upsert the freshly-computed baseline into movement_signatures."""
    payload = sess.signature.to_row()
    with SessionLocal() as db:
        row = db.scalar(
            select(MovementSignature).where(
                MovementSignature.user_id == user_id,
                MovementSignature.exercise == sess.exercise,
            )
        )
        if row is None:
            db.add(MovementSignature(
                user_id=user_id, exercise=sess.exercise,
                baseline_trajectory=payload["baseline_trajectory"],
                baseline_variability=payload["baseline_variability"],
                sample_count=payload["sample_count"],
            ))
        else:
            row.baseline_trajectory = payload["baseline_trajectory"]
            row.baseline_variability = payload["baseline_variability"]
            row.sample_count = payload["sample_count"]
            row.updated_at = datetime.now(timezone.utc)
        db.commit()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str | None = Query(default=None),
):
    # SECURITY: authenticate the connection via a JWT before accepting it. The
    # user id comes from the verified token — never from a client-supplied field.
    ws_user_id = get_user_id_from_token(token)
    if ws_user_id is None:
        # Closing before accept() rejects the handshake (HTTP 403).
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    with SessionLocal() as db:
        if db.get(User, ws_user_id) is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await manager.connect(websocket, session_id)
    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(), timeout=HEARTBEAT_IDLE_SECONDS
                )
            except asyncio.TimeoutError:
                # Idle for 10s: ping and require a pong within 5s, else drop.
                await websocket.send_text(json.dumps({"type": "ping"}))
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=HEARTBEAT_PONG_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    await websocket.close(code=status.WS_1001_GOING_AWAY)
                    manager.disconnect(session_id)
                    _close_landmarks(session_id)
                    return

            try:
                data = json.loads(message) if message else {}
            except json.JSONDecodeError:
                data = {}

            # Heartbeat replies keep the connection alive; nothing to echo.
            if data.get("type") == "pong":
                continue

            frame_b64 = data.get("frame")
            if frame_b64:
                exercise = data.get("exercise", "squat")
                # user_id is taken from the verified JWT, NOT the frame payload.
                user_id = ws_user_id
                # First frame for this session? (created lazily in process_frame)
                first_frame = get_processing_session(session_id) is None

                # Real webcam frame from the browser: run the pose pipeline off
                # the event loop on the bounded FRAME_EXECUTOR (capped at 4
                # workers) so many simultaneous sessions can't spawn unbounded
                # MediaPipe threads.
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    FRAME_EXECUTOR, process_frame, session_id, frame_b64,
                    exercise, user_id,
                )

                # --- signature persistence (the WS handler's DB-handle points) ---
                sess = get_processing_session(session_id)
                if sess is not None and user_id is not None:
                    # On session start: load the user's existing baseline (if any)
                    # right after the session is created on its first frame.
                    if first_frame:
                        _load_signature(sess, user_id)
                    # When compute_baseline() just produced a fresh baseline,
                    # persist it and clear the flag.
                    if sess.signature_needs_save:
                        _save_signature(sess, user_id)
                        sess.signature_needs_save = False

                # Persist this frame's raw landmarks to the TimescaleDB
                # hypertable (batched; flushes every FLUSH_EVERY_FRAMES frames).
                await _persist_landmarks(
                    session_id, result.get("frame_id"),
                    result.get("landmarks", []),
                )

                await websocket.send_text(json.dumps(result))
            else:
                # No image (e.g. the test client): echo a schema-shaped message.
                await websocket.send_text(json.dumps(build_frame_message(data)))
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        close_session(session_id)
        _close_landmarks(session_id)
