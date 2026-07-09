"""KINESIS backend API (Phase 3).

Phase 2 in-memory stores are replaced with real DB writes. Auth endpoints
(register/login) issue JWTs; workout endpoints are protected and derive the
user_id from the token, never from the request body.
"""

import asyncio
import json
import time
from datetime import datetime

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
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.connection_manager import ConnectionManager
from backend.database import get_db
from backend.models import User, Workout

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
# Sessions (protected — user_id comes from the token, not the body)
# --------------------------------------------------------------------------- #
@app.post("/sessions/start", response_model=SessionResponse, status_code=201)
def start_session(
    payload: SessionStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workout:
    workout = Workout(user_id=current_user.id, exercise=payload.exercise)
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


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


# --------------------------------------------------------------------------- #
# WebSocket — live pose stream (see docs/websocket_schema.md)
# --------------------------------------------------------------------------- #
manager = ConnectionManager()


def build_frame_message(data: dict) -> dict:
    """Build an outgoing frame message per the schema. Phase-5/6 fields are
    placeholders (null/empty) for now; the CV client supplies frame_id, state,
    rep_count and angles."""
    return {
        "frame_id": data.get("frame_id"),
        "timestamp": data.get("timestamp", time.time()),
        "rep_count": data.get("rep_count", 0),
        "state": data.get("state", "UP"),
        "form_score": None,
        "active_errors": [],
        "left_angle": data.get("left_angle"),
        "right_angle": data.get("right_angle"),
        "asymmetry_pct": None,
        "tempo_phase": None,
        "tempo_seconds": None,
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
