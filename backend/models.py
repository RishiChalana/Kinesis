"""TRACK B — SQLAlchemy 2.0 declarative models (Phase 2).

Six tables with the exact columns from the Phase 2 schema, wired with
ForeignKeys and bidirectional relationships:

    users ──< user_profiles
    users ──< workouts ──< sets ──< reps ──< form_errors

Alembic imports `Base` from this module to autogenerate migrations.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    profiles: Mapped[list[UserProfile]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    workouts: Mapped[list[Workout]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    torso_ratio: Mapped[float | None] = mapped_column(Float)
    femur_ratio: Mapped[float | None] = mapped_column(Float)
    shoulder_width_px: Mapped[float | None] = mapped_column(Float)
    calibrated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Phase 5 calibration fields (PersonalProfile).
    torso_femur_ratio: Mapped[float | None] = mapped_column(Float)
    hip_width_px: Mapped[float | None] = mapped_column(Float)
    squat_depth_threshold: Mapped[float | None] = mapped_column(Float)
    squat_lean_threshold: Mapped[float | None] = mapped_column(Float)
    natural_hinge_angle: Mapped[float | None] = mapped_column(Float)

    user: Mapped[User] = relationship(back_populates="profiles")


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True)  # Phase 9 index
    exercise: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Phase 5 session summary, filled in on PATCH /sessions/{id}/end.
    avg_form_score: Mapped[float | None] = mapped_column(Float)
    avg_asymmetry: Mapped[float | None] = mapped_column(Float)

    user: Mapped[User] = relationship(back_populates="workouts")
    sets: Mapped[list[Set]] = relationship(
        back_populates="workout", cascade="all, delete-orphan"
    )


class Set(Base):
    __tablename__ = "sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workout_id: Mapped[int] = mapped_column(
        ForeignKey("workouts.id"), nullable=False, index=True)  # Phase 9 index
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_form_score: Mapped[float | None] = mapped_column(Float)

    workout: Mapped[Workout] = relationship(back_populates="sets")
    reps: Mapped[list[Rep]] = relationship(
        back_populates="set", cascade="all, delete-orphan"
    )


class Rep(Base):
    __tablename__ = "reps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    set_id: Mapped[int] = mapped_column(
        ForeignKey("sets.id"), nullable=False, index=True)  # Phase 9 index
    rep_number: Mapped[int] = mapped_column(Integer, nullable=False)
    form_score: Mapped[float | None] = mapped_column(Float)
    tempo_eccentric_s: Mapped[float | None] = mapped_column(Float)
    tempo_concentric_s: Mapped[float | None] = mapped_column(Float)
    tempo_isometric_s: Mapped[float | None] = mapped_column(Float)  # Phase 8
    left_asymmetry: Mapped[float | None] = mapped_column(Float)
    right_asymmetry: Mapped[float | None] = mapped_column(Float)
    compensation_detected: Mapped[bool | None] = mapped_column(Boolean)

    # Phase 5/6 bilateral angle fields (see POST /sessions/{id}/reps schema).
    left_angle: Mapped[float | None] = mapped_column(Float)
    right_angle: Mapped[float | None] = mapped_column(Float)
    asymmetry_pct: Mapped[float | None] = mapped_column(Float)

    set: Mapped[Set] = relationship(back_populates="reps")
    form_errors: Mapped[list[FormError]] = relationship(
        back_populates="rep", cascade="all, delete-orphan"
    )


class FormError(Base):
    __tablename__ = "form_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rep_id: Mapped[int] = mapped_column(
        ForeignKey("reps.id"), nullable=False, index=True)  # Phase 9 index
    error_code: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str | None] = mapped_column(String)
    frame_count: Mapped[int | None] = mapped_column(Integer)
    frames_total: Mapped[int | None] = mapped_column(Integer)

    rep: Mapped[Rep] = relationship(back_populates="form_errors")


class LandmarkFrame(Base):
    """Phase 6 — raw pose landmark time-series, stored as a TimescaleDB
    hypertable partitioned by `time`. Created by a hand-written migration
    (raw SQL for create_hypertable + compression/retention policies), not by
    autogenerate. The composite primary key includes the partitioning column
    `time` as TimescaleDB requires, and lets the ORM map the class for
    bulk_insert_mappings."""

    __tablename__ = "landmark_frames"

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    landmark_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    frame_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    x_norm: Mapped[float | None] = mapped_column(Float)
    y_norm: Mapped[float | None] = mapped_column(Float)
    visibility: Mapped[float | None] = mapped_column(Float)


class MovementSignature(Base):
    """Phase 8 — a user's personal kinematic fingerprint for one exercise.
    baseline_trajectory is the mean 50-point angle trajectory stored as JSON."""

    __tablename__ = "movement_signatures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    exercise: Mapped[str] = mapped_column(String, nullable=False)
    baseline_trajectory: Mapped[list | None] = mapped_column(JSON)
    baseline_variability: Mapped[float | None] = mapped_column(Float)
    sample_count: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
