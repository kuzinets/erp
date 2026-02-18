# KAILASA ERP - Development Session Log

## Architecture Overview

**Stack**: FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL 16 + React/TypeScript + Tailwind CSS
**Docker**: ERP runs on ports 8001 (backend), 5433 (postgres), 3001 (frontend)
**Auth**: JWT (HS256, 480min expiry), bcrypt password hashing
**Theme**: KAILASA dark theme (slate-900/800 backgrounds, amber-500 accents)

## Commit History

### v1 — Initial Build (commit 0e34262)
- General Ledger with Chart of Accounts (hierarchical, 4-level)
- Journal Entries with double-entry validation, posting, and reversal
- Multi-subsidiary support with fiscal years and periods
- Financial reporting: Trial Balance, Statement of Activities, Statement of Financial Position
- Fund accounting (unrestricted, temporarily restricted, permanently restricted)
- Subsystem integration framework (Library, Donations, etc.)
- Contact management (vendors, donors, members)
- Department management per subsidiary
- Dashboard with KPIs
- Settings page for fiscal period management
- Dark-themed React frontend with full CRUD on all entities

### v1.1 — Integration Tests (commit 13778e0)
- 100 interconnectedness integration tests
- Tests cover cross-module flows (JE creation -> trial balance -> reports)

### v1.2 — Comprehensive Test Suite (commit 634007c)
- 600 additional tests across 6 categories:
  - Concurrency tests (race conditions, deadlocks)
  - Data integrity tests (double-entry validation, orphan prevention)
  - Performance tests (bulk operations, pagination)
  - Destructive recovery tests (crash simulation, rollback)
  - Security tests (auth, injection, CORS)
  - Unit tests (model validation, utility functions)

### v2.0-rbac — Role-Based Access Control (commit 47d61a3)
- **7 roles**: system_admin, controller, senior_accountant, junior_accountant, program_manager, auditor, viewer
- **31 granular permissions** using `module.resource.action` format
- **Separation of duties**: junior_accountant creates JEs, senior_accountant/controller posts them
- **Subsidiary-scoped data filtering**: non-global roles only see their subsidiary's data
- **Per-user permission overrides**: grant/revoke individual permissions with optional expiry (for AI-driven config)
- **Audit logging**: all mutations logged with user, action, resource, details, IP address
- **Admin API**: user CRUD, permission overrides CRUD, role listing, paginated audit log
- **Frontend updates**: `can()` replaces `isAdmin`/`isAccountant`, new User Management and Audit Log pages
- **Migration**: 002_rbac.sql seeds 4 new demo users (krishna, arjun, meera, lakshmi)

## Key Files

### Backend
- `backend/app/rbac.py` — Permission registry (ALL_PERMISSIONS, ROLE_PERMISSIONS, VALID_ROLES)
- `backend/app/models/permission.py` — UserPermissionOverride, AuditLog SQLAlchemy models
- `backend/app/middleware/auth.py` — require_permission(), resolve_permissions(), apply_subsidiary_filter(), write_audit_log()
- `backend/app/routes/admin.py` — Admin API (user CRUD, permissions, audit log)
- `backend/app/routes/gl.py` — General Ledger (accounts, journal entries, trial balance, funds)
- `backend/app/routes/org.py` — Organization (subsidiaries, fiscal years/periods, departments)
- `backend/app/routes/contacts.py` — Contact management
- `backend/app/routes/reports.py` — Financial reports
- `backend/app/routes/dashboard.py` — Dashboard KPIs
- `backend/app/routes/subsystems.py` — Subsystem integration
- `backend/app/routes/auth.py` — Login, /me, refresh (returns permissions + scope)

### Frontend
- `frontend/src/contexts/AuthContext.tsx` — permissions[], scope, can(), canAny(), canAll()
- `frontend/src/components/PermissionGuard.tsx` — Route-level permission guard
- `frontend/src/components/Layout.tsx` — Permission-filtered navigation, role badges
- `frontend/src/pages/UserManagement.tsx` — User CRUD with permission overrides
- `frontend/src/pages/AuditLog.tsx` — Paginated audit trail viewer

### Database
- `backend/migrations/001_init.sql` — Schema (accounts, journal entries, subsidiaries, etc.)
- `backend/migrations/002_rbac.sql` — RBAC tables, role migration, demo users

## Test Users (password: admin123 for all)
| Username | Role | Scope |
|----------|------|-------|
| admin | system_admin | Global |
| krishna | controller | Global |
| arjun | junior_accountant | Subsidiary-scoped |
| meera | auditor | Global |
| lakshmi | program_manager | Subsidiary-scoped |
| accountant | senior_accountant | Global |
| viewer | viewer | Subsidiary-scoped |

## Integration with Library
- Subsystem framework connects to Library via account mappings
- Library financial postings sync to ERP as journal entries
- ERP should see Library data through the subsystem integration layer
