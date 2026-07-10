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
    hash_password,
    verify_password,
)
from backend.connection_manager import ConnectionManager
from backend.database import get_db
from backend.landmarks import resolve_landmark
from backend.models import (
    FormError,
    LandmarkFrame,
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
# WebSocket — live pose stream (see docs/websocket_schema.md)
# --------------------------------------------------------------------------- #
manager = ConnectionManager()


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
        "left_angle": data.get("left_angle"),
        "right_angle": data.get("right_angle"),
        # {ai_pct, dominant_side, risk} | null
        "asymmetry": data.get("asymmetry"),
        # {phase, eccentric_s, isometric_s, concentric_s, eccentric_ok,
        #  concentric_ok} | null
        "tempo": data.get("tempo"),
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
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
                    return

            try:
                data = json.loads(message) if message else {}
            except json.JSONDecodeError:
                data = {}

            # Heartbeat replies keep the connection alive; nothing to echo.
            if data.get("type") == "pong":
                continue

            await websocket.send_text(json.dumps(build_frame_message(data)))
    except WebSocketDisconnect:
        manager.disconnect(session_id)
