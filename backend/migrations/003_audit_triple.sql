-- ============================================================================
-- Migration 003: Triple Audit Logging Infrastructure
-- Adds event_category column to audit_log for tiered retention policy.
-- ============================================================================

-- Add event_category column: 'mutation' (permanent), 'read_access' (90d), 'system' (30d)
ALTER TABLE audit_log
    ADD COLUMN IF NOT EXISTS event_category VARCHAR(20) DEFAULT 'mutation' NOT NULL;

-- Index for retention purge queries (category + time range)
CREATE INDEX IF NOT EXISTS ix_audit_log_category
    ON audit_log(event_category);

CREATE INDEX IF NOT EXISTS ix_audit_log_category_created
    ON audit_log(event_category, created_at);
