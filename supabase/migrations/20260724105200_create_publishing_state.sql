-- HiddenDevTools Engine: Complete Production Supabase Setup Migration
-- Authoritative Schema for durable Instagram Carousel publishing & recovery

-- ============================================================================
-- 1. TABLE: published_generations
-- Canonical table for successfully verified and published Instagram posts.
-- ============================================================================
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

-- ============================================================================
-- 2. TABLE: uploaded_artifacts
-- Records the final uploaded 9-slide carousel artifacts for each generation.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.uploaded_artifacts (
    generation_id TEXT NOT NULL,
    slide_number INTEGER NOT NULL CHECK (slide_number BETWEEN 1 AND 9),
    public_url TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_uploaded_artifacts PRIMARY KEY (generation_id, slide_number)
);

-- ============================================================================
-- 3. TABLE: upload_attempts
-- Tracks per-slide upload attempts with SHA-256 content hashes for idempotency.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.upload_attempts (
    generation_id TEXT NOT NULL,
    slide_number INTEGER NOT NULL CHECK (slide_number BETWEEN 1 AND 9),
    remote_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    public_url TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_upload_attempts PRIMARY KEY (generation_id, slide_number)
);

-- ============================================================================
-- 4. TABLE: instagram_publication_attempts
-- State machine for Instagram container creation, publishing, and verification.
-- ============================================================================
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

-- ============================================================================
-- 5. INDEXES: Fast lookups for workers, reconciliation, and queries
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_published_generations_sheet_sync_state
ON public.published_generations(sheet_sync_state);

CREATE INDEX IF NOT EXISTS idx_instagram_pub_attempts_publish_state
ON public.instagram_publication_attempts(publish_state);

CREATE INDEX IF NOT EXISTS idx_instagram_pub_attempts_updated_at
ON public.instagram_publication_attempts(updated_at);

CREATE INDEX IF NOT EXISTS idx_upload_attempts_sha256
ON public.upload_attempts(sha256_hash);

-- ============================================================================
-- 6. ROW LEVEL SECURITY (RLS) & ACCESS GRANTS
-- Restrict access so anonymous/public users cannot read or mutate state.
-- ============================================================================
ALTER TABLE public.published_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.uploaded_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.upload_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.instagram_publication_attempts ENABLE ROW LEVEL SECURITY;

-- Revoke all permissions from public / anon
REVOKE ALL ON public.published_generations FROM PUBLIC;
REVOKE ALL ON public.uploaded_artifacts FROM PUBLIC;
REVOKE ALL ON public.upload_attempts FROM PUBLIC;
REVOKE ALL ON public.instagram_publication_attempts FROM PUBLIC;

-- Grant full control to service_role (used by engine backend & GitHub Actions)
GRANT ALL ON public.published_generations TO service_role;
GRANT ALL ON public.uploaded_artifacts TO service_role;
GRANT ALL ON public.upload_attempts TO service_role;
GRANT ALL ON public.instagram_publication_attempts TO service_role;

-- Dedicated policies ensuring service_role has unhindered access
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'published_generations' AND policyname = 'service_role_all_published_generations'
    ) THEN
        CREATE POLICY "service_role_all_published_generations"
        ON public.published_generations FOR ALL TO service_role USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'uploaded_artifacts' AND policyname = 'service_role_all_uploaded_artifacts'
    ) THEN
        CREATE POLICY "service_role_all_uploaded_artifacts"
        ON public.uploaded_artifacts FOR ALL TO service_role USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'upload_attempts' AND policyname = 'service_role_all_upload_attempts'
    ) THEN
        CREATE POLICY "service_role_all_upload_attempts"
        ON public.upload_attempts FOR ALL TO service_role USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'instagram_publication_attempts' AND policyname = 'service_role_all_instagram_attempts'
    ) THEN
        CREATE POLICY "service_role_all_instagram_attempts"
        ON public.instagram_publication_attempts FOR ALL TO service_role USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ============================================================================
-- 7. STORAGE BUCKET: posts
-- Public read access required by Meta Graph API to fetch carousel slide images.
-- ============================================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('posts', 'posts', true, 10485760, ARRAY['image/png', 'image/jpeg'])
ON CONFLICT (id) DO UPDATE SET public = true;

-- Storage Policies: Public can read, service_role can perform all actions
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'public_read_posts'
    ) THEN
        CREATE POLICY "public_read_posts"
        ON storage.objects FOR SELECT
        TO public
        USING (bucket_id = 'posts');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'service_role_manage_posts'
    ) THEN
        CREATE POLICY "service_role_manage_posts"
        ON storage.objects FOR ALL
        TO service_role
        USING (bucket_id = 'posts')
        WITH CHECK (bucket_id = 'posts');
    END IF;
END $$;
