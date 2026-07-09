"""TRACK B — FastAPI foundations (Phase 2).

A multi-endpoint API demonstrating path params, query params, and Pydantic
request/response models. Data is kept in simple in-memory stores so the
endpoints are testable in Swagger UI without wiring the database yet
(DB persistence arrives in later phases via the SQLAlchemy models + Alembic).
"""

from datetime import datetime, timezone
from itertools import count

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

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
    id: int
    name: str
    email: EmailStr
    created_at: datetime


class SessionStart(BaseModel):
    exercise: str
    target_sets: int = Field(gt=0)
    reps_per_set: int = Field(gt=0)


class SessionResponse(BaseModel):
    session_id: int
    exercise: str
    target_sets: int
    reps_per_set: int
    started_at: datetime
    status: str


class RepRecord(BaseModel):
    set_num: int
    rep_num: int
    form_score: float
    duration_seconds: float


# --------------------------------------------------------------------------- #
# In-memory stores (placeholder persistence for Phase 2)
# --------------------------------------------------------------------------- #
_users: dict[int, UserResponse] = {}
_sessions: dict[int, SessionResponse] = {}
_user_ids = count(1)
_session_ids = count(1)


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/")
def root():
    return {"status": "KINESIS backend running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate) -> UserResponse:
    if any(u.email == payload.email for u in _users.values()):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = UserResponse(
        id=next(_user_ids),
        name=payload.name,
        email=payload.email,
        created_at=datetime.now(timezone.utc),
    )
    _users[user.id] = user
    return user


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int) -> UserResponse:
    user = _users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/sessions/start", response_model=SessionResponse, status_code=201)
def start_session(payload: SessionStart) -> SessionResponse:
    session = SessionResponse(
        session_id=next(_session_ids),
        exercise=payload.exercise,
        target_sets=payload.target_sets,
        reps_per_set=payload.reps_per_set,
        started_at=datetime.now(timezone.utc),
        status="active",
    )
    _sessions[session.session_id] = session
    return session


@app.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: int) -> SessionResponse:
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    exercise: str | None = Query(default=None, description="Filter by exercise"),
    limit: int = Query(default=10, gt=0, le=100),
) -> list[SessionResponse]:
    results = list(_sessions.values())
    if exercise is not None:
        results = [s for s in results if s.exercise == exercise]
    return results[:limit]
