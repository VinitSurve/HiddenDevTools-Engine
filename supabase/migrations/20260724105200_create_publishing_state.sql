-- Phase 7.7 Durable Production State Migration
-- Creates Postgres tables equivalent to the local SQLite schema.

CREATE TABLE IF NOT EXISTS public.published_generations (
    generation_id TEXT PRIMARY KEY,
    media_id TEXT NOT NULL,
    permalink TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sheet_sync_state TEXT DEFAULT 'PENDING' CHECK (sheet_sync_state IN ('PENDING', 'SUCCESS', 'FAILED')),
    sheet_sync_attempts INTEGER DEFAULT 0 CHECK (sheet_sync_attempts >= 0),
    last_sheet_sync_at TIMESTAMPTZ,
    last_sheet_sync_error TEXT
);

CREATE TABLE IF NOT EXISTS public.uploaded_artifacts (
    generation_id TEXT NOT NULL,
    slide_number INTEGER NOT NULL CHECK (slide_number BETWEEN 1 AND 9),
    public_url TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (generation_id, slide_number)
);

CREATE TABLE IF NOT EXISTS public.upload_attempts (
    generation_id TEXT NOT NULL,
    slide_number INTEGER NOT NULL CHECK (slide_number BETWEEN 1 AND 9),
    remote_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    public_url TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (generation_id, slide_number)
);

CREATE TABLE IF NOT EXISTS public.instagram_publication_attempts (
    generation_id TEXT PRIMARY KEY,
    child_creation_ids JSONB,
    carousel_creation_id TEXT,
    publish_state TEXT NOT NULL,
    media_id TEXT,
    permalink TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
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

-- Indexes for reconciliation queries
CREATE INDEX IF NOT EXISTS idx_published_generations_sheet_sync_state 
ON public.published_generations(sheet_sync_state);

CREATE INDEX IF NOT EXISTS idx_instagram_pub_attempts_publish_state 
ON public.instagram_publication_attempts(publish_state);

CREATE INDEX IF NOT EXISTS idx_instagram_pub_attempts_updated_at 
ON public.instagram_publication_attempts(updated_at);

-- RLS: Enable RLS and provide NO public policies (service_role required to access)
ALTER TABLE public.published_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploaded_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.upload_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.instagram_publication_attempts ENABLE ROW LEVEL SECURITY;

-- Explicitly revoke all public grants to be safe
REVOKE ALL ON public.published_generations FROM PUBLIC;
REVOKE ALL ON public.uploaded_artifacts FROM PUBLIC;
REVOKE ALL ON public.upload_attempts FROM PUBLIC;
REVOKE ALL ON public.instagram_publication_attempts FROM PUBLIC;
