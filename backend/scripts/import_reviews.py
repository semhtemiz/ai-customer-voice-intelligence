"""Run from the project root: python -m backend.scripts.import_reviews."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.importer import ImportValidationError, import_reviews


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "dataset/Womens Clothing E-Commerce Reviews.csv")
    parser.add_argument("--db", type=Path, help="Override DATABASE_PATH; relative to current working directory")
    args = parser.parse_args()
    try:
        result = import_reviews(args.input, args.db or Settings.from_env().database_path)
    except (ImportValidationError, OSError, sqlite3.Error) as error:
        # Never emit raw review rows on an import error.
        print(f"Import failed ({type(error).__name__}); database replacement was not committed.", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
