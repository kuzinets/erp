-- ============================================================================
-- KAILASA ERP System - Initial Schema (Phase 1)
-- General Ledger, Fund Accounting, Multi-Subsidiary, Subsystem Integration
-- PostgreSQL 16+ required (gen_random_uuid)
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. USERS (created first so other tables can reference)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(50)  UNIQUE NOT NULL,
    password_hash   VARCHAR(200) NOT NULL,
    display_name    VARCHAR(200) NOT NULL,
    email           VARCHAR(200),
    role            VARCHAR(30)  NOT NULL DEFAULT 'viewer'
                        CHECK (role IN ('admin', 'accountant', 'program_manager', 'viewer')),
    subsidiary_id   UUID,          -- populated after subsidiaries table exists
    is_active       BOOLEAN      DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 2. ORGANIZATION TABLES
-- ============================================================================

-- --------------------------------------------------------------------------
-- subsidiaries: each sangha/location is a subsidiary
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subsidiaries (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code                VARCHAR(20)  UNIQUE NOT NULL,
    name                VARCHAR(200) NOT NULL,
    parent_id           UUID         REFERENCES subsidiaries(id),
    currency            VARCHAR(3)   DEFAULT 'USD',
    timezone            VARCHAR(50)  DEFAULT 'UTC',
    address             TEXT,
    is_active           BOOLEAN      DEFAULT TRUE,
    library_entity_code VARCHAR(50), -- maps to Library entity_code for sync
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Now add the FK from users -> subsidiaries
ALTER TABLE users
    ADD CONSTRAINT fk_users_subsidiary
    FOREIGN KEY (subsidiary_id) REFERENCES subsidiaries(id);

-- --------------------------------------------------------------------------
-- departments: within subsidiaries
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    subsidiary_id   UUID         NOT NULL REFERENCES subsidiaries(id),
    code            VARCHAR(20)  NOT NULL,
    name            VARCHAR(200) NOT NULL,
    is_active       BOOLEAN      DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE(subsidiary_id, code)
);

-- --------------------------------------------------------------------------
-- fiscal_years
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fiscal_years (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(50) NOT NULL,
    start_date  DATE        NOT NULL,
    end_date    DATE        NOT NULL,
    is_closed   BOOLEAN     DEFAULT FALSE,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- --------------------------------------------------------------------------
-- fiscal_periods: 12 months per year
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fiscal_periods (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    fiscal_year_id  UUID         NOT NULL REFERENCES fiscal_years(id),
    period_code     VARCHAR(7)   NOT NULL,
    period_name     VARCHAR(50),
    start_date      DATE         NOT NULL,
    end_date        DATE         NOT NULL,
    status          VARCHAR(20)  DEFAULT 'open'
                        CHECK (status IN ('open', 'closed', 'adjusting')),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE(fiscal_year_id, period_code)
);

-- ============================================================================
-- 3. FUND ACCOUNTING
-- ============================================================================

CREATE TABLE IF NOT EXISTS funds (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(20)  UNIQUE NOT NULL,
    name        VARCHAR(200) NOT NULL,
    fund_type   VARCHAR(30)  NOT NULL
                    CHECK (fund_type IN ('unrestricted', 'temporarily_restricted', 'permanently_restricted')),
    description TEXT,
    is_active   BOOLEAN      DEFAULT TRUE,
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 4. GENERAL LEDGER
-- ============================================================================

-- --------------------------------------------------------------------------
-- accounts: chart of accounts
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    account_number  VARCHAR(10)  UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    account_type    VARCHAR(20)  NOT NULL
                        CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    normal_balance  VARCHAR(10)  NOT NULL
                        CHECK (normal_balance IN ('debit', 'credit')),
    parent_id       UUID         REFERENCES accounts(id),
    fund_id         UUID         REFERENCES funds(id),
    is_active       BOOLEAN      DEFAULT TRUE,
    description     TEXT,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- --------------------------------------------------------------------------
-- journal_entries: header records
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journal_entries (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_number        SERIAL,
    subsidiary_id       UUID         NOT NULL REFERENCES subsidiaries(id),
    fiscal_period_id    UUID         NOT NULL REFERENCES fiscal_periods(id),
    entry_date          DATE         NOT NULL,
    memo                TEXT,
    source              VARCHAR(30)  DEFAULT 'manual'
                            CHECK (source IN ('manual', 'library', 'temple', 'import', 'system')),
    source_reference    VARCHAR(200),
    status              VARCHAR(20)  DEFAULT 'draft'
                            CHECK (status IN ('draft', 'posted', 'reversed')),
    posted_by           UUID         REFERENCES users(id),
    posted_at           TIMESTAMP,
    reversed_by_je_id   UUID         REFERENCES journal_entries(id),
    created_by          UUID         NOT NULL REFERENCES users(id),
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- --------------------------------------------------------------------------
-- journal_lines: debit/credit lines
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journal_lines (
    id                  UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_entry_id    UUID           NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    line_number         INTEGER        NOT NULL,
    account_id          UUID           NOT NULL REFERENCES accounts(id),
    debit_amount        NUMERIC(14,2)  DEFAULT 0,
    credit_amount       NUMERIC(14,2)  DEFAULT 0,
    memo                VARCHAR(500),
    department_id       UUID           REFERENCES departments(id),
    fund_id             UUID           REFERENCES funds(id),
    cost_center         VARCHAR(50),
    quantity            NUMERIC(10,2),
    currency            VARCHAR(3)     DEFAULT 'USD',
    exchange_rate       NUMERIC(10,6)  DEFAULT 1.000000,
    created_at          TIMESTAMP      NOT NULL DEFAULT NOW(),
    CHECK (debit_amount >= 0 AND credit_amount >= 0),
    CHECK (NOT (debit_amount > 0 AND credit_amount > 0))
);

-- ============================================================================
-- 5. CONTACTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS contacts (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_type    VARCHAR(20)  NOT NULL
                        CHECK (contact_type IN ('donor', 'vendor', 'volunteer', 'member', 'other')),
    name            VARCHAR(200) NOT NULL,
    email           VARCHAR(200),
    phone           VARCHAR(50),
    address_line_1  VARCHAR(200),
    address_line_2  VARCHAR(200),
    city            VARCHAR(100),
    state           VARCHAR(100),
    country         VARCHAR(100),
    zip_code        VARCHAR(20),
    subsidiary_id   UUID         REFERENCES subsidiaries(id),
    notes           TEXT,
    is_active       BOOLEAN      DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 6. SUBSYSTEM INTEGRATION
-- ============================================================================

-- --------------------------------------------------------------------------
-- subsystem_configs: external system connections
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subsystem_configs (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    VARCHAR(100) NOT NULL,
    system_type             VARCHAR(30)  NOT NULL
                                CHECK (system_type IN ('library', 'temple', 'merchandise', 'custom')),
    base_url                VARCHAR(500) NOT NULL,
    api_username            VARCHAR(100),
    api_password_hash       VARCHAR(200),
    subsidiary_id           UUID         REFERENCES subsidiaries(id),
    sync_frequency_minutes  INTEGER      DEFAULT 1440,
    last_sync_at            TIMESTAMP,
    is_active               BOOLEAN      DEFAULT TRUE,
    created_at              TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- --------------------------------------------------------------------------
-- subsystem_account_mappings: map external account codes to ERP accounts
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subsystem_account_mappings (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    subsystem_config_id     UUID         NOT NULL REFERENCES subsystem_configs(id),
    source_account_code     VARCHAR(20)  NOT NULL,
    target_account_id       UUID         NOT NULL REFERENCES accounts(id),
    source_posting_type     VARCHAR(20),
    description             VARCHAR(200),
    is_active               BOOLEAN      DEFAULT TRUE,
    UNIQUE(subsystem_config_id, source_account_code, source_posting_type)
);

-- --------------------------------------------------------------------------
-- sync_logs: audit trail of subsystem sync runs
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_logs (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    subsystem_config_id     UUID         NOT NULL REFERENCES subsystem_configs(id),
    started_at              TIMESTAMP    NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMP,
    status                  VARCHAR(20)  DEFAULT 'running'
                                CHECK (status IN ('running', 'success', 'partial', 'failed')),
    fiscal_period_synced    VARCHAR(7),
    postings_imported       INTEGER      DEFAULT 0,
    journal_entries_created INTEGER      DEFAULT 0,
    error_message           TEXT,
    details                 JSONB
);

-- ============================================================================
-- 7. INDEXES
-- ============================================================================

-- users
CREATE INDEX IF NOT EXISTS idx_users_username       ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_role           ON users (role);

-- subsidiaries
CREATE INDEX IF NOT EXISTS idx_subsidiaries_code       ON subsidiaries (code);
CREATE INDEX IF NOT EXISTS idx_subsidiaries_parent_id  ON subsidiaries (parent_id);

-- departments
CREATE INDEX IF NOT EXISTS idx_departments_subsidiary_id ON departments (subsidiary_id);

-- fiscal_periods
CREATE INDEX IF NOT EXISTS idx_fiscal_periods_period_code    ON fiscal_periods (period_code);
CREATE INDEX IF NOT EXISTS idx_fiscal_periods_fiscal_year_id ON fiscal_periods (fiscal_year_id);

-- funds
CREATE INDEX IF NOT EXISTS idx_funds_code      ON funds (code);
CREATE INDEX IF NOT EXISTS idx_funds_fund_type ON funds (fund_type);

-- accounts
CREATE INDEX IF NOT EXISTS idx_accounts_account_number ON accounts (account_number);
CREATE INDEX IF NOT EXISTS idx_accounts_account_type   ON accounts (account_type);
CREATE INDEX IF NOT EXISTS idx_accounts_parent_id      ON accounts (parent_id);

-- journal_entries
CREATE INDEX IF NOT EXISTS idx_journal_entries_subsidiary_id    ON journal_entries (subsidiary_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_fiscal_period_id ON journal_entries (fiscal_period_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_status           ON journal_entries (status);
CREATE INDEX IF NOT EXISTS idx_journal_entries_entry_date       ON journal_entries (entry_date);
CREATE INDEX IF NOT EXISTS idx_journal_entries_source           ON journal_entries (source);
CREATE INDEX IF NOT EXISTS idx_journal_entries_created_by       ON journal_entries (created_by);

-- journal_lines
CREATE INDEX IF NOT EXISTS idx_journal_lines_journal_entry_id ON journal_lines (journal_entry_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_account_id       ON journal_lines (account_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_fund_id          ON journal_lines (fund_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_department_id    ON journal_lines (department_id);

-- contacts
CREATE INDEX IF NOT EXISTS idx_contacts_contact_type   ON contacts (contact_type);
CREATE INDEX IF NOT EXISTS idx_contacts_subsidiary_id  ON contacts (subsidiary_id);
CREATE INDEX IF NOT EXISTS idx_contacts_name           ON contacts (name);

-- subsystem integration
CREATE INDEX IF NOT EXISTS idx_subsystem_configs_system_type       ON subsystem_configs (system_type);
CREATE INDEX IF NOT EXISTS idx_subsystem_configs_subsidiary_id     ON subsystem_configs (subsidiary_id);
CREATE INDEX IF NOT EXISTS idx_subsystem_account_mappings_config   ON subsystem_account_mappings (subsystem_config_id);
CREATE INDEX IF NOT EXISTS idx_sync_logs_subsystem_config_id       ON sync_logs (subsystem_config_id);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status                    ON sync_logs (status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_started_at                ON sync_logs (started_at);

-- ============================================================================
-- 8. TRIGGER: auto-update updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_subsidiaries_updated_at
    BEFORE UPDATE ON subsidiaries
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_journal_entries_updated_at
    BEFORE UPDATE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_contacts_updated_at
    BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 9. SEED DATA
-- ============================================================================

-- --------------------------------------------------------------------------
-- 9a. Subsidiaries: HQ + 4 sangha locations
-- --------------------------------------------------------------------------
INSERT INTO subsidiaries (id, code, name, currency) VALUES
    ('00000000-0000-0000-0000-000000000001', 'HQ', 'KAILASA Global Headquarters', 'USD')
ON CONFLICT (code) DO NOTHING;

INSERT INTO subsidiaries (id, code, name, parent_id, currency, timezone, library_entity_code) VALUES
    ('00000000-0000-0000-0000-000000000010', 'SUB-CHENNAI', 'Chennai Sangha',
        '00000000-0000-0000-0000-000000000001', 'INR', 'Asia/Kolkata', 'LOC-001'),
    ('00000000-0000-0000-0000-000000000011', 'SUB-LA', 'Los Angeles Sangha',
        '00000000-0000-0000-0000-000000000001', 'USD', 'America/Los_Angeles', 'LOC-002'),
    ('00000000-0000-0000-0000-000000000012', 'SUB-NYC', 'New York Sangha',
        '00000000-0000-0000-0000-000000000001', 'USD', 'America/New_York', 'LOC-003'),
    ('00000000-0000-0000-0000-000000000013', 'SUB-ASHRAM', 'Test Ashram QA',
        '00000000-0000-0000-0000-000000000001', 'USD', 'UTC', 'LOC-004')
ON CONFLICT (code) DO NOTHING;

-- --------------------------------------------------------------------------
-- 9b. Default departments
-- --------------------------------------------------------------------------
INSERT INTO departments (subsidiary_id, code, name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'ADMIN', 'Administration'),
    ('00000000-0000-0000-0000-000000000001', 'FIN',   'Finance'),
    ('00000000-0000-0000-0000-000000000001', 'PROG',  'Programs'),
    ('00000000-0000-0000-0000-000000000010', 'LIB',   'Library Operations'),
    ('00000000-0000-0000-0000-000000000010', 'TEMPLE', 'Temple Operations')
ON CONFLICT (subsidiary_id, code) DO NOTHING;

-- --------------------------------------------------------------------------
-- 9c. Funds
-- --------------------------------------------------------------------------
INSERT INTO funds (id, code, name, fund_type) VALUES
    ('00000000-0000-0000-0000-000000000100', 'GEN',  'General Fund',       'unrestricted'),
    ('00000000-0000-0000-0000-000000000101', 'FOOD', 'Food Giveaway Fund', 'temporarily_restricted'),
    ('00000000-0000-0000-0000-000000000102', 'EDU',  'Education Fund',     'temporarily_restricted'),
    ('00000000-0000-0000-0000-000000000103', 'BLDG', 'Building Fund',      'permanently_restricted')
ON CONFLICT (code) DO NOTHING;

-- --------------------------------------------------------------------------
-- 9d. Fiscal year FY2026 with 12 periods
-- --------------------------------------------------------------------------
INSERT INTO fiscal_years (id, name, start_date, end_date) VALUES
    ('00000000-0000-0000-0000-000000000500', 'FY2026', '2026-01-01', '2026-12-31')
ON CONFLICT DO NOTHING;

INSERT INTO fiscal_periods (id, fiscal_year_id, period_code, period_name, start_date, end_date, status) VALUES
    ('00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000500',
        '2026-01', 'January 2026',   '2026-01-01', '2026-01-31', 'closed'),
    ('00000000-0000-0000-0000-000000000502', '00000000-0000-0000-0000-000000000500',
        '2026-02', 'February 2026',  '2026-02-01', '2026-02-28', 'open'),
    ('00000000-0000-0000-0000-000000000503', '00000000-0000-0000-0000-000000000500',
        '2026-03', 'March 2026',     '2026-03-01', '2026-03-31', 'open'),
    ('00000000-0000-0000-0000-000000000504', '00000000-0000-0000-0000-000000000500',
        '2026-04', 'April 2026',     '2026-04-01', '2026-04-30', 'open'),
    ('00000000-0000-0000-0000-000000000505', '00000000-0000-0000-0000-000000000500',
        '2026-05', 'May 2026',       '2026-05-01', '2026-05-31', 'open'),
    ('00000000-0000-0000-0000-000000000506', '00000000-0000-0000-0000-000000000500',
        '2026-06', 'June 2026',      '2026-06-01', '2026-06-30', 'open'),
    ('00000000-0000-0000-0000-000000000507', '00000000-0000-0000-0000-000000000500',
        '2026-07', 'July 2026',      '2026-07-01', '2026-07-31', 'open'),
    ('00000000-0000-0000-0000-000000000508', '00000000-0000-0000-0000-000000000500',
        '2026-08', 'August 2026',    '2026-08-01', '2026-08-31', 'open'),
    ('00000000-0000-0000-0000-000000000509', '00000000-0000-0000-0000-000000000500',
        '2026-09', 'September 2026', '2026-09-01', '2026-09-30', 'open'),
    ('00000000-0000-0000-0000-000000000510', '00000000-0000-0000-0000-000000000500',
        '2026-10', 'October 2026',   '2026-10-01', '2026-10-31', 'open'),
    ('00000000-0000-0000-0000-000000000511', '00000000-0000-0000-0000-000000000500',
        '2026-11', 'November 2026',  '2026-11-01', '2026-11-30', 'open'),
    ('00000000-0000-0000-0000-000000000512', '00000000-0000-0000-0000-000000000500',
        '2026-12', 'December 2026',  '2026-12-01', '2026-12-31', 'open')
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- 9e. Chart of Accounts (~50 accounts, full hierarchy)
-- --------------------------------------------------------------------------

-- ===== ASSETS (1000-1999) =====
INSERT INTO accounts (id, account_number, name, account_type, normal_balance, parent_id, description) VALUES
    -- Current Assets
    ('00000000-0000-0000-0001-000000001000', '1000', 'Assets',
        'asset', 'debit', NULL, 'Top-level asset category'),
    ('00000000-0000-0000-0001-000000001100', '1100', 'Current Assets',
        'asset', 'debit', '00000000-0000-0000-0001-000000001000', 'Short-term assets'),
    ('00000000-0000-0000-0001-000000001110', '1110', 'Cash - Checking',
        'asset', 'debit', '00000000-0000-0000-0001-000000001100', 'Main checking account'),
    ('00000000-0000-0000-0001-000000001120', '1120', 'Cash - Savings',
        'asset', 'debit', '00000000-0000-0000-0001-000000001100', 'Savings account'),
    ('00000000-0000-0000-0001-000000001130', '1130', 'Cash - Petty Cash',
        'asset', 'debit', '00000000-0000-0000-0001-000000001100', 'Petty cash on hand'),
    ('00000000-0000-0000-0001-000000001140', '1140', 'Cash - PayPal/Online',
        'asset', 'debit', '00000000-0000-0000-0001-000000001100', 'Online payment processor balances'),
    ('00000000-0000-0000-0001-000000001200', '1200', 'Accounts Receivable',
        'asset', 'debit', '00000000-0000-0000-0001-000000001100', 'Amounts owed to the organization'),
    ('00000000-0000-0000-0001-000000001210', '1210', 'Pledges Receivable',
        'asset', 'debit', '00000000-0000-0000-0001-000000001100', 'Promised but not yet received donations'),
    ('00000000-0000-0000-0001-000000001300', '1300', 'Prepaid Expenses',
        'asset', 'debit', '00000000-0000-0000-0001-000000001100', 'Advance payments for future services'),
    ('00000000-0000-0000-0001-000000001400', '1400', 'Inventory - Books & Materials',
        'asset', 'debit', '00000000-0000-0000-0001-000000001100', 'Library and merchandise inventory'),
    -- Fixed Assets
    ('00000000-0000-0000-0001-000000001500', '1500', 'Fixed Assets',
        'asset', 'debit', '00000000-0000-0000-0001-000000001000', 'Long-term tangible assets'),
    ('00000000-0000-0000-0001-000000001510', '1510', 'Buildings & Improvements',
        'asset', 'debit', '00000000-0000-0000-0001-000000001500', 'Temple and ashram buildings'),
    ('00000000-0000-0000-0001-000000001520', '1520', 'Furniture & Equipment',
        'asset', 'debit', '00000000-0000-0000-0001-000000001500', 'Office and temple equipment'),
    ('00000000-0000-0000-0001-000000001530', '1530', 'Vehicles',
        'asset', 'debit', '00000000-0000-0000-0001-000000001500', 'Organization vehicles'),
    ('00000000-0000-0000-0001-000000001590', '1590', 'Accumulated Depreciation',
        'asset', 'credit', '00000000-0000-0000-0001-000000001500', 'Contra asset for depreciation')
ON CONFLICT (account_number) DO NOTHING;

-- ===== LIABILITIES (2000-2999) =====
INSERT INTO accounts (id, account_number, name, account_type, normal_balance, parent_id, description) VALUES
    ('00000000-0000-0000-0001-000000002000', '2000', 'Liabilities',
        'liability', 'credit', NULL, 'Top-level liability category'),
    ('00000000-0000-0000-0001-000000002100', '2100', 'Current Liabilities',
        'liability', 'credit', '00000000-0000-0000-0001-000000002000', 'Short-term obligations'),
    ('00000000-0000-0000-0001-000000002110', '2110', 'Accounts Payable',
        'liability', 'credit', '00000000-0000-0000-0001-000000002100', 'Amounts owed to vendors'),
    ('00000000-0000-0000-0001-000000002120', '2120', 'Accrued Expenses',
        'liability', 'credit', '00000000-0000-0000-0001-000000002100', 'Expenses incurred but not yet paid'),
    ('00000000-0000-0000-0001-000000002130', '2130', 'Payroll Liabilities',
        'liability', 'credit', '00000000-0000-0000-0001-000000002100', 'Wages and taxes payable'),
    ('00000000-0000-0000-0001-000000002140', '2140', 'Deferred Revenue',
        'liability', 'credit', '00000000-0000-0000-0001-000000002100', 'Payments received for future services'),
    ('00000000-0000-0000-0001-000000002200', '2200', 'Long-Term Liabilities',
        'liability', 'credit', '00000000-0000-0000-0001-000000002000', 'Long-term obligations'),
    ('00000000-0000-0000-0001-000000002210', '2210', 'Mortgage Payable',
        'liability', 'credit', '00000000-0000-0000-0001-000000002200', 'Building mortgage'),
    ('00000000-0000-0000-0001-000000002220', '2220', 'Notes Payable',
        'liability', 'credit', '00000000-0000-0000-0001-000000002200', 'Long-term notes')
ON CONFLICT (account_number) DO NOTHING;

-- ===== EQUITY / NET ASSETS (3000-3999) =====
INSERT INTO accounts (id, account_number, name, account_type, normal_balance, parent_id, fund_id, description) VALUES
    ('00000000-0000-0000-0001-000000003000', '3000', 'Net Assets',
        'equity', 'credit', NULL, NULL, 'Top-level net assets category'),
    ('00000000-0000-0000-0001-000000003100', '3100', 'Net Assets - Unrestricted',
        'equity', 'credit', '00000000-0000-0000-0001-000000003000',
        '00000000-0000-0000-0000-000000000100', 'General unrestricted net assets'),
    ('00000000-0000-0000-0001-000000003200', '3200', 'Net Assets - Temporarily Restricted',
        'equity', 'credit', '00000000-0000-0000-0001-000000003000', NULL,
        'Donor-restricted for specific purposes/time'),
    ('00000000-0000-0000-0001-000000003300', '3300', 'Net Assets - Permanently Restricted',
        'equity', 'credit', '00000000-0000-0000-0001-000000003000', NULL,
        'Endowment-style permanently restricted'),
    ('00000000-0000-0000-0001-000000003900', '3900', 'Retained Surplus / Deficit',
        'equity', 'credit', '00000000-0000-0000-0001-000000003000', NULL,
        'Accumulated surplus or deficit from prior years')
ON CONFLICT (account_number) DO NOTHING;

-- ===== REVENUE (4000-4999) =====
INSERT INTO accounts (id, account_number, name, account_type, normal_balance, parent_id, description) VALUES
    ('00000000-0000-0000-0001-000000004000', '4000', 'Revenue',
        'revenue', 'credit', NULL, 'Top-level revenue category'),
    -- Donation Revenue
    ('00000000-0000-0000-0001-000000004100', '4100', 'Donation Revenue - Unrestricted',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004000', 'General donations without restrictions'),
    ('00000000-0000-0000-0001-000000004110', '4110', 'Donation Revenue - Temporarily Restricted',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004000', 'Purpose or time restricted donations'),
    ('00000000-0000-0000-0001-000000004120', '4120', 'Donation Revenue - Permanently Restricted',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004000', 'Endowment donations'),
    -- Program Revenue
    ('00000000-0000-0000-0001-000000004200', '4200', 'Program Revenue',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004000', 'Revenue from programs and services'),
    ('00000000-0000-0000-0001-000000004210', '4210', 'Course Fees',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004200', 'Spiritual and educational course fees'),
    ('00000000-0000-0000-0001-000000004220', '4220', 'Event Revenue',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004200', 'Festival and event ticket sales'),
    -- Sales Revenue
    ('00000000-0000-0000-0001-000000004300', '4300', 'Sales Revenue',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004000', 'Revenue from product sales'),
    ('00000000-0000-0000-0001-000000004310', '4310', 'Book Sales',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004300', 'Library/bookstore book sales'),
    ('00000000-0000-0000-0001-000000004320', '4320', 'Merchandise Sales',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004300', 'Temple and spiritual merchandise'),
    -- Other Revenue
    ('00000000-0000-0000-0001-000000004400', '4400', 'Grant Revenue',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004000', 'Government and foundation grants'),
    ('00000000-0000-0000-0001-000000004500', '4500', 'Interest & Investment Income',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004000', 'Bank interest and investment returns'),
    ('00000000-0000-0000-0001-000000004900', '4900', 'Other Revenue',
        'revenue', 'credit', '00000000-0000-0000-0001-000000004000', 'Miscellaneous revenue')
ON CONFLICT (account_number) DO NOTHING;

-- ===== EXPENSES (5000-9999) =====
INSERT INTO accounts (id, account_number, name, account_type, normal_balance, parent_id, description) VALUES
    ('00000000-0000-0000-0001-000000005000', '5000', 'Expenses',
        'expense', 'debit', NULL, 'Top-level expense category'),
    -- Program Expenses
    ('00000000-0000-0000-0001-000000005100', '5100', 'Program Expenses',
        'expense', 'debit', '00000000-0000-0000-0001-000000005000', 'Direct program delivery costs'),
    ('00000000-0000-0000-0001-000000005110', '5110', 'Program Supplies',
        'expense', 'debit', '00000000-0000-0000-0001-000000005100', 'Materials for programs'),
    ('00000000-0000-0000-0001-000000005120', '5120', 'Program Travel',
        'expense', 'debit', '00000000-0000-0000-0001-000000005100', 'Travel for program delivery'),
    -- Cost of Goods Sold
    ('00000000-0000-0000-0001-000000005200', '5200', 'Cost of Goods Sold',
        'expense', 'debit', '00000000-0000-0000-0001-000000005000', 'Direct costs of items sold'),
    ('00000000-0000-0000-0001-000000005210', '5210', 'Cost of Books Sold',
        'expense', 'debit', '00000000-0000-0000-0001-000000005200', 'Cost basis of books sold'),
    ('00000000-0000-0000-0001-000000005220', '5220', 'Cost of Merchandise Sold',
        'expense', 'debit', '00000000-0000-0000-0001-000000005200', 'Cost basis of merchandise sold'),
    -- Personnel Expenses
    ('00000000-0000-0000-0001-000000006000', '6000', 'Personnel Expenses',
        'expense', 'debit', '00000000-0000-0000-0001-000000005000', 'Staff compensation and benefits'),
    ('00000000-0000-0000-0001-000000006100', '6100', 'Salaries & Wages',
        'expense', 'debit', '00000000-0000-0000-0001-000000006000', 'Employee salaries'),
    ('00000000-0000-0000-0001-000000006200', '6200', 'Employee Benefits',
        'expense', 'debit', '00000000-0000-0000-0001-000000006000', 'Health insurance, retirement, etc.'),
    ('00000000-0000-0000-0001-000000006300', '6300', 'Payroll Taxes',
        'expense', 'debit', '00000000-0000-0000-0001-000000006000', 'Employer payroll tax obligations'),
    -- Occupancy & Facilities
    ('00000000-0000-0000-0001-000000007000', '7000', 'Occupancy & Facilities',
        'expense', 'debit', '00000000-0000-0000-0001-000000005000', 'Building and facility costs'),
    ('00000000-0000-0000-0001-000000007100', '7100', 'Rent',
        'expense', 'debit', '00000000-0000-0000-0001-000000007000', 'Lease and rental payments'),
    ('00000000-0000-0000-0001-000000007200', '7200', 'Utilities',
        'expense', 'debit', '00000000-0000-0000-0001-000000007000', 'Electricity, water, gas, internet'),
    ('00000000-0000-0000-0001-000000007300', '7300', 'Maintenance & Repairs',
        'expense', 'debit', '00000000-0000-0000-0001-000000007000', 'Building and equipment maintenance'),
    ('00000000-0000-0000-0001-000000007400', '7400', 'Insurance',
        'expense', 'debit', '00000000-0000-0000-0001-000000007000', 'Property and liability insurance'),
    -- Administrative Expenses
    ('00000000-0000-0000-0001-000000008000', '8000', 'Administrative Expenses',
        'expense', 'debit', '00000000-0000-0000-0001-000000005000', 'General and administrative costs'),
    ('00000000-0000-0000-0001-000000008100', '8100', 'Office Supplies',
        'expense', 'debit', '00000000-0000-0000-0001-000000008000', 'Paper, toner, general supplies'),
    ('00000000-0000-0000-0001-000000008200', '8200', 'Professional Fees',
        'expense', 'debit', '00000000-0000-0000-0001-000000008000', 'Legal, audit, consulting fees'),
    ('00000000-0000-0000-0001-000000008300', '8300', 'Technology & Software',
        'expense', 'debit', '00000000-0000-0000-0001-000000008000', 'SaaS subscriptions, hosting, IT'),
    ('00000000-0000-0000-0001-000000008400', '8400', 'Bank & Payment Fees',
        'expense', 'debit', '00000000-0000-0000-0001-000000008000', 'Banking fees, payment processor fees'),
    ('00000000-0000-0000-0001-000000008500', '8500', 'Depreciation Expense',
        'expense', 'debit', '00000000-0000-0000-0001-000000008000', 'Periodic depreciation of fixed assets'),
    -- Fundraising Expenses
    ('00000000-0000-0000-0001-000000008600', '8600', 'Fundraising Expenses',
        'expense', 'debit', '00000000-0000-0000-0001-000000005000', 'Costs of fundraising activities'),
    -- Other / Intercompany
    ('00000000-0000-0000-0001-000000009000', '9000', 'Other Expenses',
        'expense', 'debit', '00000000-0000-0000-0001-000000005000', 'Miscellaneous expenses'),
    ('00000000-0000-0000-0001-000000009900', '9900', 'Intercompany Transfers',
        'expense', 'debit', '00000000-0000-0000-0001-000000005000', 'Transfers between subsidiaries/funds')
ON CONFLICT (account_number) DO NOTHING;

-- --------------------------------------------------------------------------
-- 9f. Users (admin + 3 staff)
-- --------------------------------------------------------------------------
INSERT INTO users (id, username, password_hash, display_name, email, role) VALUES
    ('00000000-0000-0000-0000-000000000201', 'dmitry',
        '$2b$12$0ad80H7R.E9fE.D/.CY/puqEg0UBfYmT6eLufX3wpfkcUJ3a/un9i',
        'Dmitry Kuzinets', 'dmitry@kailasa.org', 'admin'),
    ('00000000-0000-0000-0000-000000000202', 'ramantha',
        '$2b$12$0ad80H7R.E9fE.D/.CY/puqEg0UBfYmT6eLufX3wpfkcUJ3a/un9i',
        'Ramantha Swami', 'ramantha@kailasa.org', 'accountant'),
    ('00000000-0000-0000-0000-000000000203', 'priya',
        '$2b$12$0ad80H7R.E9fE.D/.CY/puqEg0UBfYmT6eLufX3wpfkcUJ3a/un9i',
        'Priya Devi', 'priya@kailasa.org', 'program_manager'),
    ('00000000-0000-0000-0000-000000000204', 'sarah',
        '$2b$12$0ad80H7R.E9fE.D/.CY/puqEg0UBfYmT6eLufX3wpfkcUJ3a/un9i',
        'Sarah Chen', 'sarah@kailasa.org', 'viewer')
ON CONFLICT (username) DO NOTHING;

-- --------------------------------------------------------------------------
-- 9g. Subsystem config (Library integration)
-- --------------------------------------------------------------------------
INSERT INTO subsystem_configs (id, name, system_type, base_url, api_username, subsidiary_id) VALUES
    ('00000000-0000-0000-0000-000000000301', 'Sangha Library', 'library',
        'http://host.docker.internal:8000', 'dmitry',
        '00000000-0000-0000-0000-000000000010')
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- 9h. Subsystem account mappings (Library -> ERP)
-- --------------------------------------------------------------------------
INSERT INTO subsystem_account_mappings (subsystem_config_id, source_account_code, target_account_id, source_posting_type, description) VALUES
    ('00000000-0000-0000-0000-000000000301', '4100',
        '00000000-0000-0000-0001-000000004100', 'credit', 'Library donations -> Donation Revenue Unrestricted'),
    ('00000000-0000-0000-0000-000000000301', '5200',
        '00000000-0000-0000-0001-000000005200', 'debit', 'Library COGS -> Cost of Goods Sold'),
    ('00000000-0000-0000-0000-000000000301', '5210',
        '00000000-0000-0000-0001-000000005210', 'debit', 'Library book costs -> Cost of Books Sold'),
    ('00000000-0000-0000-0000-000000000301', '9900',
        '00000000-0000-0000-0001-000000009900', 'debit', 'Library intercompany -> Intercompany Transfers')
ON CONFLICT DO NOTHING;

-- --------------------------------------------------------------------------
-- 9i. Sample contacts
-- --------------------------------------------------------------------------
INSERT INTO contacts (contact_type, name, email, city, state, country, subsidiary_id) VALUES
    ('donor',     'Ananda Foundation',   'info@ananda.org',     'Los Angeles', 'CA', 'USA',
        '00000000-0000-0000-0000-000000000011'),
    ('vendor',    'Sacred Books Press',  'orders@sacredbooks.com', 'Chennai', 'TN', 'India',
        '00000000-0000-0000-0000-000000000010'),
    ('volunteer', 'Lakshmi Narayanan',   'lakshmi@gmail.com',   'New York', 'NY', 'USA',
        '00000000-0000-0000-0000-000000000012'),
    ('member',    'Ganesha Das',         'ganesha@outlook.com', 'Chennai', 'TN', 'India',
        '00000000-0000-0000-0000-000000000010')
ON CONFLICT DO NOTHING;

COMMIT;
