"""phase 9 fk indexes

Revision ID: ba47161738da
Revises: 68259d84c269
Create Date: 2026-07-10 15:26:11.579116

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba47161738da'
down_revision: Union[str, Sequence[str], None] = '68259d84c269'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add FK indexes to speed up the session-detail joins (Phase 9).

    NOTE: autogenerate again proposed dropping the landmark_frames indexes
    (raw-SQL/TimescaleDB objects it can't see) — removed as false positives.
    landmark_frames.session_id is already covered by the Phase 6 composite index
    ix_landmark_frames_session_landmark, so no separate index is added for it.
    """
    op.create_index(op.f('ix_form_errors_rep_id'), 'form_errors', ['rep_id'], unique=False)
    op.create_index(op.f('ix_reps_set_id'), 'reps', ['set_id'], unique=False)
    op.create_index(op.f('ix_sets_workout_id'), 'sets', ['workout_id'], unique=False)
    op.create_index(op.f('ix_workouts_user_id'), 'workouts', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_workouts_user_id'), table_name='workouts')
    op.drop_index(op.f('ix_sets_workout_id'), table_name='sets')
    op.drop_index(op.f('ix_reps_set_id'), table_name='reps')
    op.drop_index(op.f('ix_form_errors_rep_id'), table_name='form_errors')
