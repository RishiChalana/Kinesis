"""phase 8 movement_signatures + rep isometric tempo

Revision ID: 68259d84c269
Revises: 9ba3bc559aa4
Create Date: 2026-07-10 11:12:23.917464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68259d84c269'
down_revision: Union[str, Sequence[str], None] = '9ba3bc559aa4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOTE: autogenerate also proposed dropping the landmark_frames indexes
    # (ix_landmark_frames_session_landmark and TimescaleDB's landmark_frames_time_idx)
    # because they were created via raw SQL in the Phase 6 migration and aren't
    # declared on the ORM model. Those are false positives and were removed —
    # dropping them would hurt time-series query performance.
    op.create_table('movement_signatures',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('exercise', sa.String(), nullable=False),
    sa.Column('baseline_trajectory', sa.JSON(), nullable=True),
    sa.Column('baseline_variability', sa.Float(), nullable=True),
    sa.Column('sample_count', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('reps', sa.Column('tempo_isometric_s', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('reps', 'tempo_isometric_s')
    op.drop_table('movement_signatures')
