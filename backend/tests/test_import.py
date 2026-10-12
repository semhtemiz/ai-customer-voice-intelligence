import json
import sqlite3

import pytest

from backend.app.db import connect, database_ready
from backend.app.importer import ImportValidationError, import_reviews


def seed_analysis(db, checksum):
    with connect(db) as connection:
        connection.execute("""INSERT INTO analysis_runs
            (run_id,kind,method,dataset_sha256,started_at,status,eligible_count,processed_count)
            VALUES ('sentiment-1','sentiment','test',?,'2026-10-12','completed',1,1)""", (checksum,))
        connection.execute("""INSERT INTO analysis_runs
            (run_id,kind,method,dataset_sha256,source_sentiment_run_id,started_at,status,eligible_count,processed_count)
            VALUES ('topics-1','topics','test',?,'sentiment-1','2026-10-12','completed',1,1)""", (checksum,))
        connection.execute("INSERT INTO review_predictions VALUES (0,'sentiment-1','negative',0.8)")
        connection.execute("INSERT INTO review_topic_results VALUES (0,'topics-1','completed')")
        connection.execute("INSERT INTO review_topics VALUES (0,'topics-1','sizing')")
        connection.execute("INSERT INTO review_topics VALUES (0,'topics-1','fabric_quality')")
        connection.execute("""UPDATE import_state SET selected_sentiment_run_id='sentiment-1',
            selected_topic_run_id='topics-1' WHERE id=1""")
        connection.commit()


def test_cleaning_preserves_source_ids_and_content_duplicates(write_csv, tmp_path):
    source = write_csv([
        {"": "7", "Review Text": "  Great\n  fit  ", "Age": "999", "Rating": "9", "Recommended IND": "2",
         "Division Name": " ", "Department Name": "", "Class Name": ""},
        {"": "8", "Review Text": "  Great\n  fit  ", "Age": "999", "Rating": "9", "Recommended IND": "2",
         "Division Name": " ", "Department Name": "", "Class Name": ""},
        {"": "99", "Review Text": " \t\n ", "Rating": "5", "Recommended IND": "1"},
    ])
    db = tmp_path / "reviews.db"
    result = import_reviews(source, db)
    with connect(db) as connection:
        rows = connection.execute("SELECT * FROM reviews ORDER BY review_id").fetchall()
        assert [row["review_id"] for row in rows] == [7, 8, 99]
        assert rows[0]["review_text"] == "  Great\n  fit  "
        assert rows[0]["review_text_clean"] == "Great fit"
        assert all(rows[0][column] is None for column in (
            "age", "rating", "recommended_ind", "division_name", "department_name", "class_name"))
        assert rows[2]["review_text_clean"] is None and rows[2]["rating"] == 5
        stored = json.loads(connection.execute("SELECT quality_report_json FROM import_state").fetchone()[0])
        assert stored == result["report"]
    assert result["report"]["duplicate_content_excess_count"] == 1
    assert result["report"]["invalid_rating_count"] == 2
    assert result["report"]["invalid_recommendation_count"] == 2
    assert result["report"]["invalid_age_count"] == 2
    assert result["report"]["kpis"]["valid_rating_count"] == 1


def test_same_checksum_preserves_analysis_and_import_timestamp(write_csv, tmp_path):
    source = write_csv([{}])
    db = tmp_path / "reviews.db"
    first = import_reviews(source, db)
    seed_analysis(db, first["report"]["sha256"])
    with connect(db) as connection:
        before = dict(connection.execute("SELECT * FROM import_state").fetchone())
    second = import_reviews(source, db)
    assert second["status"] == "unchanged" and second["analysis_invalidated"] is False
    with connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM review_predictions").fetchone()[0] == 1
        assert dict(connection.execute("SELECT * FROM import_state").fetchone()) == before


def test_changed_checksum_replaces_dataset_and_clears_dependent_analysis(write_csv, tmp_path):
    source = write_csv([{}])
    db = tmp_path / "reviews.db"
    first = import_reviews(source, db)
    seed_analysis(db, first["report"]["sha256"])
    source = write_csv([{"": "50", "Rating": "1"}])
    second = import_reviews(source, db)
    assert second["analysis_invalidated"] is True
    with connect(db) as connection:
        assert connection.execute("SELECT review_id FROM reviews").fetchone()[0] == 50
        for table in ("analysis_runs", "review_predictions", "review_topic_results", "review_topics"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        state = connection.execute("SELECT * FROM import_state").fetchone()
        assert state["selected_sentiment_run_id"] is None and state["selected_topic_run_id"] is None
        assert state["dataset_sha256"] != first["report"]["sha256"]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("ids", [["0", "0"], ["-1"], [""], ["1.5"], ["abc"]])
def test_invalid_ids_preserve_existing_database(write_csv, tmp_path, ids):
    db = tmp_path / "reviews.db"
    valid = write_csv([{}])
    first = import_reviews(valid, db)
    seed_analysis(db, first["report"]["sha256"])
    before = db.read_bytes()
    invalid = write_csv([{ "": value} for value in ids], name="invalid.csv")
    with pytest.raises(ImportValidationError):
        import_reviews(invalid, db)
    assert db.read_bytes() == before and database_ready(db)


def test_database_failure_rolls_back_replacement(write_csv, tmp_path):
    db = tmp_path / "reviews.db"
    source = write_csv([{}])
    first = import_reviews(source, db)
    seed_analysis(db, first["report"]["sha256"])
    with connect(db) as connection:
        connection.execute("""CREATE TRIGGER reject_replacement BEFORE INSERT ON reviews
            BEGIN SELECT RAISE(ABORT, 'test transaction failure'); END""")
        connection.commit()
    changed = write_csv([{"": "20"}])
    with pytest.raises(sqlite3.IntegrityError):
        import_reviews(changed, db)
    with connect(db) as connection:
        assert connection.execute("SELECT review_id FROM reviews").fetchone()[0] == 0
        assert connection.execute("SELECT dataset_sha256 FROM import_state").fetchone()[0] == first["report"]["sha256"]
        assert connection.execute("SELECT COUNT(*) FROM review_topics").fetchone()[0] == 2


def test_foreign_keys_are_enforced(write_csv, tmp_path):
    db = tmp_path / "reviews.db"
    import_reviews(write_csv([{}]), db)
    with connect(db) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO review_predictions VALUES (999,'missing','positive',0.8)")


def test_empty_dataset_has_null_averages(write_csv, tmp_path):
    db = tmp_path / "reviews.db"
    result = import_reviews(write_csv([]), db)
    assert result["report"]["row_count"] == 0
    assert result["report"]["kpis"]["avg_rating"] is None
    assert database_ready(db)


@pytest.mark.parametrize("content", [
    "Rating,Review Text\n5,Good\n",  # Missing columns.
    ',Clothing ID,Age,Title,Review Text,Rating,Recommended IND,Positive Feedback Count,Division Name,Department Name,Class Name\n0,1\n',
])
def test_malformed_csv_does_not_create_database(tmp_path, content):
    source = tmp_path / "bad.csv"
    source.write_text(content)
    db = tmp_path / "reviews.db"
    with pytest.raises(ImportValidationError):
        import_reviews(source, db)
    assert not db.exists()
