import sqlite3

from fastapi.testclient import TestClient

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.importer import import_reviews
from backend.app.main import create_app


def test_missing_database_returns_503_without_creating_file(tmp_path):
    db = tmp_path / "missing.db"
    with TestClient(create_app(Settings(db))) as client:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable", "database_ready": False}
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200
    assert not db.exists()


def test_imported_database_is_ready_and_cors_is_limited(write_csv, tmp_path):
    db = tmp_path / "reviews.db"
    import_reviews(write_csv([{}]), db)
    with TestClient(create_app(Settings(db))) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database_ready": True}
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        forbidden = client.get("/health", headers={"Origin": "https://untrusted.example"})
        assert "access-control-allow-origin" not in forbidden.headers
        preflight = client.options("/health", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        })
        assert preflight.status_code == 200


def test_corrupt_and_uninitialized_databases_return_safe_503(tmp_path):
    db = tmp_path / "bad.db"
    db.write_bytes(b"not a sqlite database")
    with TestClient(create_app(Settings(db))) as client:
        assert client.get("/health").status_code == 503
    db.unlink()
    sqlite3.connect(db).close()
    with TestClient(create_app(Settings(db))) as client:
        assert client.get("/health").status_code == 503


def test_row_count_mismatch_returns_503(write_csv, tmp_path):
    db = tmp_path / "reviews.db"
    import_reviews(write_csv([{}]), db)
    with sqlite3.connect(db) as connection:
        connection.execute("DELETE FROM reviews")
    with TestClient(create_app(Settings(db))) as client:
        assert client.get("/health").status_code == 503


def test_environment_paths_and_cors_are_configurable(monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", "backend/data/custom.db")
    monkeypatch.setenv("CORS_ORIGINS", "https://dashboard.example, http://localhost:3000")
    settings = Settings.from_env()
    assert settings.database_path == PROJECT_ROOT / "backend/data/custom.db"
    assert settings.cors_origins == ("https://dashboard.example", "http://localhost:3000")
