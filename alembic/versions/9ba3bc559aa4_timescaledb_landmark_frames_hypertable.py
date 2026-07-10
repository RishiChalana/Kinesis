"""timescaledb landmark_frames hypertable

Revision ID: 9ba3bc559aa4
Revises: fcbfea4984d1
Create Date: 2026-07-10 10:39:33.689848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ba3bc559aa4'
down_revision: Union[str, Sequence[str], None] = 'fcbfea4984d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the landmark_frames hypertable + compression/retention policies."""
    # 1) Base table. Composite PK includes the partitioning column `time`,
    #    which TimescaleDB requires for any unique constraint on a hypertable.
    op.execute(
        """
        CREATE TABLE landmark_frames (
            time         TIMESTAMPTZ NOT NULL,
            session_id   INT NOT NULL,
            frame_id     INT NOT NULL,
            landmark_id  INT NOT NULL,
            x_norm       FLOAT,
            y_norm       FLOAT,
            visibility   FLOAT,
            PRIMARY KEY (time, session_id, landmark_id, frame_id)
        );
        """
    )

    # 2) Turn it into a hypertable, auto-partitioned by time.
    op.execute("SELECT create_hypertable('landmark_frames', 'time');")

    # Fast lookups for the /angles endpoint (session_id + landmark_id over time).
    op.execute(
        "CREATE INDEX ix_landmark_frames_session_landmark "
        "ON landmark_frames (session_id, landmark_id, time DESC);"
    )

    # 3) Enable columnar compression, then compress chunks older than 7 days.
    #    (add_compression_policy requires compression to be enabled first.)
    op.execute(
        """
        ALTER TABLE landmark_frames SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'session_id, landmark_id',
            timescaledb.compress_orderby = 'time DESC'
        );
        """
    )
    op.execute(
        "SELECT add_compression_policy('landmark_frames', INTERVAL '7 days');"
    )

    # 4) Auto-delete raw landmark data older than 90 days. Aggregated rep-level
    #    data (reps / form_errors / workout summaries) is kept forever.
    op.execute(
        "SELECT add_retention_policy('landmark_frames', INTERVAL '90 days');"
    )


def downgrade() -> None:
    """Drop the hypertable; its policies and index are removed with it."""
    op.execute("DROP TABLE IF EXISTS landmark_frames;")
