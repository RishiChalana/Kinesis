"""Parallel Cassandra writer for landmark telemetry — a dual-write mirror of the
TimescaleDB landmark_frames hypertable.

TimescaleDB stays the source of truth; this is an additive, best-effort mirror
that shares LandmarkBuffer's existing flush cadence (see backend/landmark_store).
Everything here is gated behind CASSANDRA_ENABLED (default off), so the app and
the existing test/bench paths are completely unaffected unless a cluster is
configured. Cassandra write failures are swallowed and logged — they must never
break the primary TimescaleDB write or the live WS stream.

Schema mirrors the TimescaleDB index ix_landmark_frames_session_landmark
(session_id, landmark_id, time DESC):

  * Partition key ((session_id, landmark_id))  -> the /angles read supplies both
    as equality, so it is a single-partition read.
  * Clustering (ts DESC, frame_id ASC)         -> time-ordered trajectory falls
    out of disk order (mirrors `time DESC`); frame_id disambiguates rows that
    share a timestamp (all 33 landmarks of a frame share one ts).

Consistency (throughput-first, this is dense replaceable telemetry):
  * Writes: LOCAL_ONE   — lowest latency on the ~1000 rows/s hot path.
  * Reads:  LOCAL_QUORUM — /angles-style reads run post-session, favour a
    complete cross-replica view over freshness.

Retention (90 days), the behaviour TimescaleDB gets free from its retention +
compression policies:
  * default_time_to_live on the table auto-expires every row after 90 days.
  * TimeWindowCompactionStrategy (1-day windows) lets whole expired SSTables be
    dropped without rewrite — the analogue of TimescaleDB dropping a chunk. TTL
    without TWCS would leave tombstones; a manual DELETE purge job is the wrong
    tool here (tombstone build-up). gc_grace_seconds is left at the 10-day
    default. SSTables are LZ4-compressed by default, so no "compress after N
    days" policy is needed.
"""

import logging
import os

logger = logging.getLogger(__name__)

_TRUE = {"1", "true", "yes", "on"}

CASSANDRA_ENABLED = os.getenv("CASSANDRA_ENABLED", "false").lower() in _TRUE
CONTACT_POINTS = [
    h.strip() for h in os.getenv("CASSANDRA_CONTACT_POINTS", "127.0.0.1").split(",")
    if h.strip()
]
PORT = int(os.getenv("CASSANDRA_PORT", "9042"))
KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", "kinesis")
LOCAL_DC = os.getenv("CASSANDRA_LOCAL_DC", "datacenter1")
# Benchmark/dev keyspace: RF=1 on a single node (LOCAL_QUORUM of RF=1 == 1, so it
# works against one node, unlike RF=3). PRODUCTION uses RF=3 — see CREATE_KEYSPACE.
REPLICATION_FACTOR = int(os.getenv("CASSANDRA_REPLICATION_FACTOR", "1"))

# 90-day retention, mirroring TimescaleDB add_retention_policy(INTERVAL '90 days').
TTL_SECONDS = 90 * 24 * 60 * 60  # 7_776_000
GC_GRACE_SECONDS = 10 * 24 * 60 * 60  # 864_000 — Cassandra's default 10 days.

# PRODUCTION keyspace (documented, not what the benchmark creates):
#   CREATE KEYSPACE kinesis WITH replication =
#       {'class': 'NetworkTopologyStrategy', 'dc1': 3};
# The benchmark keyspace below uses the same strategy with the local DC at RF=1.
CREATE_KEYSPACE = (
    "CREATE KEYSPACE IF NOT EXISTS {ks} WITH replication = "
    "{{'class': 'NetworkTopologyStrategy', '{dc}': {rf}}}"
)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS landmark_frames (
    session_id  int,
    landmark_id int,
    ts          timestamp,
    frame_id    int,
    x_norm      float,
    y_norm      float,
    visibility  float,
    PRIMARY KEY ((session_id, landmark_id), ts, frame_id)
) WITH CLUSTERING ORDER BY (ts DESC, frame_id ASC)
  AND default_time_to_live = {ttl}
  AND gc_grace_seconds = {gc}
  AND compaction = {{'class': 'TimeWindowCompactionStrategy',
                     'compaction_window_unit': 'DAYS',
                     'compaction_window_size': 1}}
""".format(ttl=TTL_SECONDS, gc=GC_GRACE_SECONDS)

# Row TTL comes from the table's default_time_to_live, so the INSERT stays plain.
INSERT_CQL = (
    "INSERT INTO landmark_frames "
    "(session_id, landmark_id, ts, frame_id, x_norm, y_norm, visibility) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)
# Mirrors GET /sessions/{id}/angles: one landmark's y_norm trajectory over time.
# ORDER BY ts ASC reverses the DESC clustering order to return ascending time.
SELECT_CQL = (
    "SELECT ts, y_norm FROM landmark_frames "
    "WHERE session_id = ? AND landmark_id = ? ORDER BY ts ASC"
)


class CassandraLandmarkWriter:
    """Holds a long-lived cluster/session and prepared statements. write_landmarks
    is called from the FRAME_EXECUTOR flush thread (off the event loop), so
    blocking on the async insert futures there is fine."""

    def __init__(self, cluster, session, insert_stmt, select_stmt):
        self._cluster = cluster
        self._session = session
        self._insert = insert_stmt
        self._select = select_stmt

    def write_landmarks(self, rows: list[dict]) -> int:
        """Fire one async INSERT per row (CL=LOCAL_ONE) and wait for all. `rows`
        use the LandmarkBuffer schema (key 'time'), mapped to column order here."""
        futures = [
            self._session.execute_async(self._insert, (
                r["session_id"], r["landmark_id"], r["time"], r["frame_id"],
                r["x_norm"], r["y_norm"], r["visibility"],
            ))
            for r in rows
        ]
        for f in futures:
            f.result()
        return len(futures)

    def read_trajectory(self, session_id: int, landmark_id: int):
        """(ts, y_norm) points for one landmark in a session, ascending by time
        (CL=LOCAL_QUORUM). Mirrors the /angles read for dual-write verification."""
        return [(r.ts, r.y_norm)
                for r in self._session.execute(self._select, (session_id, landmark_id))]

    def close(self):
        self._cluster.shutdown()


def _build_cluster(keyspace: str | None = None):
    """Connect with a DC-aware, token-aware profile pinned to LOCAL_DC. Imports
    live inside the function so cassandra-driver is only required when enabled."""
    from cassandra import ConsistencyLevel
    from cassandra.cluster import EXEC_PROFILE_DEFAULT, Cluster, ExecutionProfile
    from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy

    profile = ExecutionProfile(
        load_balancing_policy=TokenAwarePolicy(
            DCAwareRoundRobinPolicy(local_dc=LOCAL_DC)),
        consistency_level=ConsistencyLevel.LOCAL_ONE,
    )
    cluster = Cluster(
        contact_points=CONTACT_POINTS, port=PORT,
        execution_profiles={EXEC_PROFILE_DEFAULT: profile},
    )
    session = cluster.connect(keyspace) if keyspace else cluster.connect()
    return cluster, session


def init_schema() -> None:
    """Create the keyspace (RF from env; benchmark default RF=1) and the
    landmark_frames table. Idempotent. Safe to call from a bench setup script."""
    cluster, session = _build_cluster()
    try:
        session.execute(
            CREATE_KEYSPACE.format(ks=KEYSPACE, dc=LOCAL_DC, rf=REPLICATION_FACTOR))
        session.set_keyspace(KEYSPACE)
        session.execute(CREATE_TABLE)
    finally:
        cluster.shutdown()


_writer: CassandraLandmarkWriter | None = None
_writer_init_failed = False


def get_cassandra_writer() -> CassandraLandmarkWriter | None:
    """Return a shared writer, or None if disabled or the cluster is unreachable.
    Never raises: dual-write is best-effort and must not break the primary path.
    Self-bootstraps the schema so a fresh benchmark cluster just works. Warmed
    once at app startup (see main.lifespan) so no WS frame pays connect latency."""
    global _writer, _writer_init_failed
    if not CASSANDRA_ENABLED or _writer_init_failed:
        return None
    if _writer is None:
        try:
            from cassandra import ConsistencyLevel
            cluster, session = _build_cluster()
            session.execute(
                CREATE_KEYSPACE.format(ks=KEYSPACE, dc=LOCAL_DC, rf=REPLICATION_FACTOR))
            session.set_keyspace(KEYSPACE)
            session.execute(CREATE_TABLE)
            insert_stmt = session.prepare(INSERT_CQL)
            insert_stmt.consistency_level = ConsistencyLevel.LOCAL_ONE
            select_stmt = session.prepare(SELECT_CQL)
            select_stmt.consistency_level = ConsistencyLevel.LOCAL_QUORUM
            _writer = CassandraLandmarkWriter(
                cluster, session, insert_stmt, select_stmt)
            logger.info("Cassandra dual-write enabled (keyspace=%s, RF=%d, DC=%s)",
                        KEYSPACE, REPLICATION_FACTOR, LOCAL_DC)
        except Exception as e:
            logger.warning(
                "Cassandra writer unavailable, disabling dual-write: %s", e)
            _writer_init_failed = True
            return None
    return _writer


def close_cassandra_writer() -> None:
    global _writer
    if _writer is not None:
        _writer.close()
        _writer = None
