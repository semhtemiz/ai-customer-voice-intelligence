"""SQLite connections with explicit transaction ownership and FK enforcement."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 2
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


@contextmanager
def connect(path: Path, *, readonly=False):
    if readonly:
        # FastAPI's sync dependency, endpoint and cleanup may run on different
        # workers. Each request owns its connection; operations remain sequential.
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5, check_same_thread=False)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def initialize_schema(connection):
    # executescript implicitly commits; execute individual DDL statements so
    # schema changes and dataset replacement remain in the same transaction.
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version == 1:
        connection.execute("DROP INDEX IF EXISTS review_topics_run_topic")
        connection.execute("ALTER TABLE review_topics RENAME TO review_topics_v1")
        ddl = SCHEMA_PATH.read_text(encoding="utf-8")
        table = next(part for part in ddl.split(';') if 'CREATE TABLE IF NOT EXISTS review_topics (' in part)
        connection.execute(table)
        connection.execute("INSERT INTO review_topics SELECT * FROM review_topics_v1")
        connection.execute("DROP TABLE review_topics_v1")
    for statement in SCHEMA_PATH.read_text(encoding="utf-8").split(";"):
        if statement.strip():
            connection.execute(statement)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def database_ready(path: Path):
    """Readiness requires a completed import and a supported, intact schema."""
    if not path.is_file():
        return False
    try:
        with connect(path, readonly=True) as connection:
            if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                return False
            state = connection.execute("SELECT row_count FROM import_state WHERE id=1").fetchone()
            if state is None:
                return False
            for table in ("reviews", "analysis_runs", "review_predictions", "review_topic_results", "review_topics"):
                connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
            return connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == state["row_count"]
    except (sqlite3.Error, OSError):
        return False
