CREATE TABLE IF NOT EXISTS upload_attempts (
    generation_id TEXT NOT NULL,
    slide_number INTEGER NOT NULL CHECK (slide_number BETWEEN 1 AND 9),
    remote_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    public_url TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    PRIMARY KEY (generation_id, slide_number)
);

CREATE TABLE IF NOT EXISTS instagram_publication_attempts (
    generation_id TEXT PRIMARY KEY,
    child_creation_ids TEXT, -- JSON array
    carousel_creation_id TEXT,
    publish_state TEXT NOT NULL,
    media_id TEXT,
    permalink TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CONSTRAINT chk_publish_state CHECK (publish_state IN (
        'CHILDREN_CREATED',
        'CAROUSEL_CREATED',
        'PUBLISH_REQUESTED',
        'PUBLISHED_MEDIA_KNOWN',
        'PUBLISH_OUTCOME_UNKNOWN',
        'PUBLISH_RETRY_AUTHORIZED',
        'PUBLISHED_VERIFIED'
    ))
);
