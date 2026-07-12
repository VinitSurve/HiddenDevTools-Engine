CREATE TABLE IF NOT EXISTS processed_comments (
    comment_id TEXT PRIMARY KEY,
    media_id TEXT NOT NULL,
    instagram_user_id TEXT NOT NULL,
    username TEXT,
    normalized_text TEXT,
    matched_keyword TEXT,
    status TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
