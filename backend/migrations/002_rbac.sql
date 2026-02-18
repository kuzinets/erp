-- ============================================================================
-- KAILASA ERP — RBAC Migration
-- Expands role system from 4 simple roles to 7 granular roles with
-- per-user permission overrides and audit logging.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. DROP OLD CONSTRAINT AND MIGRATE EXISTING USERS
-- ============================================================================

-- Drop old check constraint first
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;

-- Migrate existing users to new role names BEFORE re-adding constraint
UPDATE users SET role = 'system_admin'      WHERE role = 'admin';
UPDATE users SET role = 'senior_accountant' WHERE role = 'accountant';
-- program_manager stays the same
-- viewer stays the same

-- ============================================================================
-- 2. ADD EXPANDED ROLE CONSTRAINT
-- ============================================================================

ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN (
    'system_admin', 'controller', 'senior_accountant',
    'junior_accountant', 'program_manager', 'auditor', 'viewer'
));

-- ============================================================================
-- 3. ASSIGN SUBSIDIARY TO SCOPED USERS (were NULL before)
-- ============================================================================

-- Give program_manager (priya) the Chennai subsidiary
UPDATE users SET subsidiary_id = '00000000-0000-0000-0000-000000000010'
    WHERE username = 'priya' AND subsidiary_id IS NULL;

-- ============================================================================
-- 4. PER-USER PERMISSION OVERRIDES (AI advanced mode)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_permission_overrides (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission      VARCHAR(100) NOT NULL,
    granted         BOOLEAN      NOT NULL,      -- true = grant extra, false = revoke
    reason          TEXT,                        -- why this override exists
    granted_by      UUID         REFERENCES users(id),
    expires_at      TIMESTAMP,                  -- optional auto-expiry
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, permission)
);

CREATE INDEX IF NOT EXISTS idx_perm_overrides_user ON user_permission_overrides(user_id);
CREATE INDEX IF NOT EXISTS idx_perm_overrides_expires ON user_permission_overrides(expires_at)
    WHERE expires_at IS NOT NULL;

-- ============================================================================
-- 5. AUDIT LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID         REFERENCES users(id),
    username        VARCHAR(100),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(100),
    resource_id     VARCHAR(200),
    details         JSONB,
    ip_address      VARCHAR(45),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user       ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action     ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource   ON audit_log(resource_type, resource_id);

-- ============================================================================
-- 6. NEW SEED USERS (password: admin123 for all)
-- ============================================================================
-- bcrypt hash of 'admin123': $2b$12$0ad80H7R.E9fE.D/.CY/puqEg0UBfYmT6eLufX3wpfkcUJ3a/un9i

INSERT INTO users (id, username, password_hash, display_name, email, role, subsidiary_id) VALUES
    -- Controller (global scope — no subsidiary)
    ('00000000-0000-0000-0000-000000000205', 'krishna',
        '$2b$12$0ad80H7R.E9fE.D/.CY/puqEg0UBfYmT6eLufX3wpfkcUJ3a/un9i',
        'Krishna Murthy', 'krishna@kailasa.org', 'controller', NULL),
    -- Junior Accountant (scoped to Chennai)
    ('00000000-0000-0000-0000-000000000206', 'arjun',
        '$2b$12$0ad80H7R.E9fE.D/.CY/puqEg0UBfYmT6eLufX3wpfkcUJ3a/un9i',
        'Arjun Sharma', 'arjun@kailasa.org', 'junior_accountant',
        '00000000-0000-0000-0000-000000000010'),
    -- Auditor (global scope — no subsidiary)
    ('00000000-0000-0000-0000-000000000207', 'meera',
        '$2b$12$0ad80H7R.E9fE.D/.CY/puqEg0UBfYmT6eLufX3wpfkcUJ3a/un9i',
        'Meera Patel', 'meera@kailasa.org', 'auditor', NULL),
    -- Program Manager (scoped to LA)
    ('00000000-0000-0000-0000-000000000208', 'lakshmi',
        '$2b$12$0ad80H7R.E9fE.D/.CY/puqEg0UBfYmT6eLufX3wpfkcUJ3a/un9i',
        'Lakshmi Devi', 'lakshmi@kailasa.org', 'program_manager',
        '00000000-0000-0000-0000-000000000011')
ON CONFLICT (username) DO NOTHING;

COMMIT;
