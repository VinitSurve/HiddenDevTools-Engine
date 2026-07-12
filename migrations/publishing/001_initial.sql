CREATE TABLE IF NOT EXISTS published_generations (
    generation_id TEXT PRIMARY KEY,
    media_id      TEXT NOT NULL,
    permalink     TEXT NOT NULL,
    published_at  TEXT NOT NULL
);
