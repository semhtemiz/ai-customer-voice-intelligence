"""Validate one CSV snapshot, then atomically replace the imported dataset."""
import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from scripts.profile_dataset import integer, profile_content, read_rows

from .db import SCHEMA_VERSION, connect, initialize_schema


class ImportValidationError(ValueError):
    pass


def nullable_text(value):
    return value.strip() or None


def bounded_integer(value, lower, upper):
    parsed = integer(value)
    return parsed if parsed is not None and lower <= parsed <= upper else None


def import_reviews(source: Path, database: Path):
    content = source.read_bytes()
    try:
        report = profile_content(content, source)
        _, raw_rows = read_rows(content)
    except (ValueError, UnicodeError, csv.Error) as error:
        raise ImportValidationError(str(error)) from error
    if report["invalid_source_id_count"] or report["duplicate_source_id_count"]:
        raise ImportValidationError("Source review IDs must be unique non-negative integers")
    rows = [(
        integer(row[""]), integer(row["Clothing ID"]), bounded_integer(row["Age"], 1, 120),
        row["Title"], row["Review Text"], " ".join(row["Review Text"].split()) or None,
        bounded_integer(row["Rating"], 1, 5), bounded_integer(row["Recommended IND"], 0, 1),
        integer(row["Positive Feedback Count"]), nullable_text(row["Division Name"]),
        nullable_text(row["Department Name"]), nullable_text(row["Class Name"]),
    ) for row in raw_rows]
    with connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, SCHEMA_VERSION):
                raise ImportValidationError("Unsupported database schema version")
            initialize_schema(connection)
            previous = connection.execute("SELECT * FROM import_state WHERE id=1").fetchone()
            if previous and previous["dataset_sha256"] == report["sha256"]:
                if connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] != previous["row_count"]:
                    raise ImportValidationError("Stored row count mismatch; database needs investigation")
                connection.commit()
                return {"status": "unchanged", "analysis_invalidated": False,
                        "report": json.loads(previous["quality_report_json"])}
            # Clear dependent caches and selections in the same replacement transaction.
            connection.execute("DELETE FROM import_state")
            connection.execute("DELETE FROM analysis_runs")
            connection.execute("DELETE FROM reviews")
            connection.executemany("INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
            connection.execute(
                """INSERT INTO import_state
                   (id,dataset_sha256,source_file,imported_at,row_count,quality_report_json)
                   VALUES (1,?,?,?,?,?)""",
                (report["sha256"], source.as_posix(), datetime.now(timezone.utc).isoformat(),
                 len(rows), json.dumps(report, ensure_ascii=False)),
            )
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise sqlite3.IntegrityError("Foreign key validation failed")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {"status": "imported", "analysis_invalidated": previous is not None, "report": report}
