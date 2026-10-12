import csv

import pytest

COLUMNS = ["", "Clothing ID", "Age", "Title", "Review Text", "Rating",
           "Recommended IND", "Positive Feedback Count", "Division Name",
           "Department Name", "Class Name"]


@pytest.fixture
def write_csv(tmp_path):
    def write(rows, name="reviews.csv"):
        path = tmp_path / name
        with path.open("w", encoding="utf-8", newline="") as source:
            writer = csv.DictWriter(source, fieldnames=COLUMNS)
            writer.writeheader()
            for index, overrides in enumerate(rows):
                row = dict(zip(COLUMNS, [str(index), "42", "30", "Title", "Good fit",
                                        "4", "1", "0", "General", "Tops", "Blouses"]))
                row.update(overrides)
                writer.writerow(row)
        return path
    return write
