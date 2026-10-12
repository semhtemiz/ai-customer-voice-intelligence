"""Profile the local review CSV without emitting customer text."""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path


def read_rows(content):
    """Parse one byte snapshot, rejecting incomplete or ambiguous CSV rows."""
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    columns = reader.fieldnames
    required = {"", "Clothing ID", "Age", "Title", "Review Text", "Rating",
                "Recommended IND", "Positive Feedback Count", "Division Name",
                "Department Name", "Class Name"}
    if not required.issubset(columns or []):
        raise ValueError(f"Missing columns: {sorted(required - set(columns or []))}")
    if len(columns) != len(set(columns)):
        raise ValueError("Duplicate CSV column names")
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("CSV row width does not match header")
    return columns, rows


def integer(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def profile_content(content, path):
    columns, rows = read_rows(content)

    ratings = [integer(row["Rating"]) for row in rows]
    recommendations = [integer(row["Recommended IND"]) for row in rows]
    ages = [integer(row["Age"]) for row in rows]
    valid_ratings = [value for value in ratings if value in range(1, 6)]
    valid_recommendations = [value for value in recommendations if value in (0, 1)]
    valid_ages = [value for value in ages if value is not None and 0 < value <= 120]
    ids = [integer(row[""]) for row in rows]
    valid_ids = [value for value in ids if value is not None and value >= 0]
    return {
        "file": path.as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "row_count": len(rows),
        "columns": columns,
        "blank_counts": {key: sum(not row[key].strip() for row in rows) for key in columns},
        "invalid_source_id_count": len(rows) - len(valid_ids),
        "duplicate_source_id_count": len(valid_ids) - len(set(valid_ids)),
        "duplicate_content_excess_count": len(rows) - len({tuple(row[c] for c in columns if c) for row in rows}),
        "invalid_rating_count": len(rows) - len(valid_ratings),
        "invalid_recommendation_count": len(rows) - len(valid_recommendations),
        "invalid_age_count": len(rows) - len(valid_ages),
        "age_range": [min(valid_ages), max(valid_ages)] if valid_ages else None,
        "rating_counts": dict(sorted(Counter(row["Rating"] for row in rows).items())),
        "department_counts": dict(sorted(Counter(row["Department Name"].strip() or "Unknown" for row in rows).items())),
        "kpis": {
            "total_reviews": len(rows),
            "avg_rating": round(sum(valid_ratings) / len(valid_ratings), 2) if valid_ratings else None,
            "recommendation_rate_pct": round(100 * sum(valid_recommendations) / len(valid_recommendations), 2) if valid_recommendations else None,
            "low_rating_rate_pct": round(100 * sum(value <= 2 for value in valid_ratings) / len(valid_ratings), 2) if valid_ratings else None,
            "valid_rating_count": len(valid_ratings),
            "valid_recommendation_count": len(valid_recommendations),
            "text_review_count": sum(bool(row["Review Text"].strip()) for row in rows),
        },
    }


def profile(path):
    return profile_content(path.read_bytes(), path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("dataset/Womens Clothing E-Commerce Reviews.csv"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(profile(args.input), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")
