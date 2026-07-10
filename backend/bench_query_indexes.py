"""Phase 9 — EXPLAIN ANALYZE of the /sessions/{id}/detail join queries.

Seeds a large dataset (once, idempotent) so seq-scan vs index-scan is
measurable, then runs EXPLAIN (ANALYZE, FORMAT JSON) on the three queries the
detail endpoint's selectinload issues, and prints real execution times.

Run BEFORE applying the index migration, then AFTER, and compare.
    python backend/bench_query_indexes.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text  # noqa: E402

from backend.auth import hash_password  # noqa: E402
from backend.database import SessionLocal  # noqa: E402
from backend.models import FormError, Rep, Set, User, Workout  # noqa: E402

EMAIL = "benchidx@example.com"
N_WORKOUTS, SETS, REPS, ERRS = 300, 3, 10, 2


def ensure_seed(db):
    u = db.scalar(select(User).where(User.email == EMAIL))
    if u is None:
        u = User(name="BenchIdx", email=EMAIL, hashed_password=hash_password("pw"))
        db.add(u)
        db.flush()
    existing = db.scalar(select(Workout.id).where(Workout.user_id == u.id).limit(1))
    if existing is not None:
        return u.id
    print(f"seeding {N_WORKOUTS} workouts x {SETS} sets x {REPS} reps x {ERRS} errors ...")
    for _ in range(N_WORKOUTS):
        w = Workout(user_id=u.id, exercise="squat")
        db.add(w)
        db.flush()
        for sn in range(SETS):
            s = Set(workout_id=w.id, set_number=sn + 1)
            db.add(s)
            db.flush()
            for rn in range(REPS):
                r = Rep(set_id=s.id, rep_number=rn + 1, form_score=85)
                db.add(r)
                db.flush()
                for _e in range(ERRS):
                    db.add(FormError(rep_id=r.id, error_code="KNEE_CAVE", severity="MEDIUM"))
        db.commit()
    print("seed done.")
    return u.id


def _exec_ms(db, sql):
    row = db.execute(text(f"EXPLAIN (ANALYZE, FORMAT JSON) {sql}")).scalar()
    plan = row[0] if isinstance(row, list) else json.loads(row)[0]
    return plan["Execution Time"], plan["Plan"]["Node Type"]


def main():
    db = SessionLocal()
    uid = ensure_seed(db)

    # One workout's ids, as the detail endpoint would resolve them.
    wid = db.scalar(select(Workout.id).where(Workout.user_id == uid).limit(1))
    sids = db.scalars(select(Set.id).where(Set.workout_id == wid)).all()
    rids = db.scalars(select(Rep.id).where(Rep.set_id.in_(sids))).all()
    sids_sql = ",".join(map(str, sids))
    rids_sql = ",".join(map(str, rids))

    total_rows = {
        "workouts": db.scalar(select(text("count(*)")).select_from(Workout)),
        "reps": db.scalar(select(text("count(*)")).select_from(Rep)),
        "form_errors": db.scalar(select(text("count(*)")).select_from(FormError)),
    }
    print(f"table sizes: {total_rows}")

    queries = {
        "sets by workout_id": f"SELECT * FROM sets WHERE workout_id = {wid}",
        "reps by set_id IN": f"SELECT * FROM reps WHERE set_id IN ({sids_sql})",
        "form_errors by rep_id IN": f"SELECT * FROM form_errors WHERE rep_id IN ({rids_sql})",
    }
    print("\nEXPLAIN ANALYZE (execution time / plan node):")
    total = 0.0
    for name, sql in queries.items():
        ms, node = _exec_ms(db, sql)
        total += ms
        print(f"    {name:28s}: {ms:7.3f} ms   [{node}]")
    print(f"    {'TOTAL':28s}: {total:7.3f} ms")
    db.close()


if __name__ == "__main__":
    main()
