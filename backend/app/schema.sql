CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY CHECK (review_id >= 0),
    clothing_id INTEGER,
    age INTEGER CHECK (age BETWEEN 1 AND 120),
    title TEXT,
    review_text TEXT,
    review_text_clean TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    recommended_ind INTEGER CHECK (recommended_ind IN (0, 1)),
    positive_feedback_count INTEGER,
    division_name TEXT,
    department_name TEXT,
    class_name TEXT
);
CREATE TABLE IF NOT EXISTS analysis_runs (
    run_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('sentiment', 'topics')),
    method TEXT NOT NULL,
    model_id TEXT,
    model_revision TEXT,
    taxonomy_version TEXT,
    dataset_sha256 TEXT NOT NULL,
    source_sentiment_run_id TEXT REFERENCES analysis_runs(run_id) ON DELETE SET NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    eligible_count INTEGER NOT NULL CHECK (eligible_count >= 0),
    processed_count INTEGER NOT NULL CHECK (processed_count BETWEEN 0 AND eligible_count)
);
CREATE TABLE IF NOT EXISTS review_predictions (
    review_id INTEGER NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
    run_id TEXT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
    sentiment TEXT NOT NULL CHECK (sentiment IN ('positive', 'neutral', 'negative', 'unknown')),
    score REAL CHECK (score BETWEEN 0 AND 1),
    PRIMARY KEY (review_id, run_id)
);
CREATE TABLE IF NOT EXISTS review_topic_results (
    review_id INTEGER NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
    run_id TEXT NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('completed', 'failed')),
    PRIMARY KEY (review_id, run_id)
);
CREATE TABLE IF NOT EXISTS review_topics (
    review_id INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    topic TEXT NOT NULL CHECK (topic IN ('sizing', 'fabric_quality', 'color_appearance', 'style_design', 'value_price', 'shipping', 'customer_service', 'other')),
    PRIMARY KEY (review_id, run_id, topic),
    FOREIGN KEY (review_id, run_id) REFERENCES review_topic_results(review_id, run_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS import_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    dataset_sha256 TEXT NOT NULL,
    source_file TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    quality_report_json TEXT NOT NULL,
    selected_sentiment_run_id TEXT REFERENCES analysis_runs(run_id) ON DELETE SET NULL,
    selected_topic_run_id TEXT REFERENCES analysis_runs(run_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS reviews_department_class ON reviews(department_name, class_name);
CREATE INDEX IF NOT EXISTS review_predictions_run ON review_predictions(run_id, sentiment);
CREATE INDEX IF NOT EXISTS review_topics_run_topic ON review_topics(run_id, topic);
