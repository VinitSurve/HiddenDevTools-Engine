-- Supabase PostgreSQL schema for production persistence (CORRECTED)

CREATE TABLE IF NOT EXISTS public.published_generations (
    generation_id TEXT PRIMARY KEY,
    media_id TEXT NOT NULL,
    permalink TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    sheet_sync_state TEXT DEFAULT 'PENDING' CHECK (sheet_sync_state IN ('PENDING', 'SUCCESS', 'FAILED')),
    sheet_sync_attempts INTEGER DEFAULT 0,
    last_sheet_sync_at TIMESTAMPTZ,
    last_sheet_sync_error TEXT
);

CREATE TABLE IF NOT EXISTS public.uploaded_artifacts (
    generation_id TEXT NOT NULL,
    slide_number INTEGER NOT NULL CHECK (slide_number BETWEEN 1 AND 9),
    public_url TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (generation_id, slide_number)
);

CREATE TABLE IF NOT EXISTS public.upload_attempts (
    generation_id TEXT NOT NULL,
    slide_number INTEGER NOT NULL CHECK (slide_number BETWEEN 1 AND 9),
    remote_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    public_url TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (generation_id, slide_number)
);

CREATE TABLE IF NOT EXISTS public.instagram_publication_attempts (
    generation_id TEXT PRIMARY KEY,
    child_creation_ids JSONB,
    carousel_creation_id TEXT,
    publish_state TEXT NOT NULL CHECK (publish_state IN (
        'CHILDREN_CREATED',
        'CAROUSEL_CREATED',
        'PUBLISH_REQUESTED',
        'PUBLISHED_MEDIA_KNOWN',
        'PUBLISH_OUTCOME_UNKNOWN',
        'PUBLISH_RETRY_AUTHORIZED',
        'PUBLISHED_VERIFIED'
    )),
    media_id TEXT,
    permalink TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Indexes for reconciliation queries:
CREATE INDEX idx_published_generations_sheet_sync_state ON public.published_generations(sheet_sync_state);
CREATE INDEX idx_instagram_pub_attempts_publish_state ON public.instagram_publication_attempts(publish_state);
CREATE INDEX idx_instagram_pub_attempts_updated_at ON public.instagram_publication_attempts(updated_at);

-- Row Level Security (RLS)
ALTER TABLE public.published_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploaded_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.upload_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.instagram_publication_attempts ENABLE ROW LEVEL SECURITY;

-- Note: No public (anon/authenticated) policies are created. 
-- The backend scheduler will use the service_role key to bypass RLS.
