CREATE TABLE IF NOT EXISTS uploaded_artifacts (
    generation_id TEXT    NOT NULL,
    slide_number  INTEGER NOT NULL CHECK (slide_number BETWEEN 1 AND 9),
    public_url    TEXT    NOT NULL,
    uploaded_at   TEXT    NOT NULL,
    PRIMARY KEY (generation_id, slide_number)
);
