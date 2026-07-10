"""Verify movement-signature persistence wiring (Phase 8 patch).

Exercises the exact helpers the WS handler calls:
  _save_signature(sess, user_id)  -> upsert into movement_signatures
  _load_signature(sess, user_id)  -> load baseline into a fresh session

No server needed — the helpers open their own SessionLocal. Cleans up after.

Run:  python backend/test_signature_persistence.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from backend.auth import hash_password  # noqa: E402
from backend.database import SessionLocal  # noqa: E402
from backend.frame_processor import ProcessingSession  # noqa: E402
from backend.main import _load_signature, _save_signature  # noqa: E402
from backend.models import MovementSignature, User  # noqa: E402

EMAIL = "sigpersist@example.com"


def _ensure_user():
    db = SessionLocal()
    u = db.scalar(select(User).where(User.email == EMAIL))
    if u is None:
        u = User(name="SigTest", email=EMAIL, hashed_password=hash_password("pw"))
        db.add(u)
        db.commit()
        db.refresh(u)
    uid = u.id
    db.close()
    return uid


def _cleanup(uid):
    db = SessionLocal()
    db.execute(delete(MovementSignature).where(MovementSignature.user_id == uid))
    u = db.get(User, uid)
    if u:
        db.delete(u)
    db.commit()
    db.close()


def main():
    uid = _ensure_user()
    try:
        # Build a session with a computed baseline (simulating enough good reps).
        base = np.concatenate([np.linspace(170, 80, 25), np.linspace(80, 170, 25)])
        rng = np.random.default_rng(7)
        sess = ProcessingSession("squat")
        sess.signature.user_id = uid
        for _ in range(6):
            sess.signature.add_good_rep(base + rng.normal(0, 1.0, 50), form_score=90)
        assert sess.signature.compute_baseline() is True
        assert sess.signature.baseline_mean is not None
        print(f"built baseline: {sess.signature.sample_count if hasattr(sess.signature,'sample_count') else len(sess.signature.baseline_trajectories)} reps, "
              f"variability={sess.signature.baseline_variability:.2f}")

        # SAVE (the WS handler's post-frame DB point).
        _save_signature(sess, uid)
        db = SessionLocal()
        row = db.scalar(select(MovementSignature).where(
            MovementSignature.user_id == uid, MovementSignature.exercise == "squat"))
        db.close()
        assert row is not None, "signature row was not saved"
        assert row.sample_count == 6
        assert len(row.baseline_trajectory) == 50
        print(f"saved to movement_signatures: id={row.id}, sample_count={row.sample_count}, "
              f"trajectory_len={len(row.baseline_trajectory)}")

        # LOAD into a FRESH session (the WS handler's session-start DB point).
        fresh = ProcessingSession("squat")
        assert fresh.signature.baseline_mean is None
        _load_signature(fresh, uid)
        assert fresh.signature.baseline_mean is not None, "baseline was not loaded"
        assert len(fresh.signature.baseline_mean) == 50
        np.testing.assert_allclose(
            np.asarray(fresh.signature.baseline_mean),
            np.asarray(sess.signature.baseline_mean), rtol=1e-6)
        print("loaded baseline into a fresh session — matches saved trajectory")

        # A loaded session can immediately compare/flag deviations.
        deviant = np.concatenate([np.linspace(170, 130, 25), np.linspace(130, 170, 25)])
        ev = fresh.signature.compare(deviant)
        print(f"deviant rep against loaded baseline -> "
              f"{'SIGNATURE_DEVIATION fired' if ev else 'no deviation'}")

        print("\nPASS signature persistence round-trip")
    finally:
        _cleanup(uid)
        print("cleanup done")


if __name__ == "__main__":
    main()
