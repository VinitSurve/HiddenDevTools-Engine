-- Drop the old table (SQLite has limited ALTER capabilities for things like ENUMs and renaming)
DROP TABLE IF EXISTS processed_comments;

CREATE TABLE processed_comments (
    comment_id TEXT PRIMARY KEY,
    media_id TEXT NOT NULL,
    instagram_user_id TEXT NOT NULL,
    username TEXT,
    original_text TEXT,
    normalized_text TEXT,
    matched_keyword TEXT,
    status TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at DATETIME,
    last_error TEXT,
    next_retry_at DATETIME
);
