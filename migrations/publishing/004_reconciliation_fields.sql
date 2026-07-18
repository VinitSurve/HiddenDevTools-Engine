ALTER TABLE published_generations ADD COLUMN sheet_sync_state TEXT DEFAULT 'PENDING';
ALTER TABLE published_generations ADD COLUMN sheet_sync_attempts INTEGER DEFAULT 0;
ALTER TABLE published_generations ADD COLUMN last_sheet_sync_at DATETIME;
ALTER TABLE published_generations ADD COLUMN last_sheet_sync_error TEXT;
