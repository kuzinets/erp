"""
RBAC Permission Registry — KAILASA ERP

Defines the canonical role-to-permission mapping. This is the "simple mode"
that humans interact with via named roles. Per-user overrides are stored in
the database for AI-configured exceptions.

Permission string format: {module}.{resource}.{action}
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# All permission strings used across the system
# ---------------------------------------------------------------------------

ALL_PERMISSIONS: list[str] = sorted([
    # General Ledger
    "gl.accounts.view",
    "gl.accounts.create",
    "gl.accounts.update",
    "gl.journal_entries.view",
    "gl.journal_entries.create",
    "gl.journal_entries.post",
    "gl.journal_entries.reverse",
    "gl.trial_balance.view",
    "gl.funds.view",
    # Organization
    "org.subsidiaries.view",
    "org.subsidiaries.create",
    "org.subsidiaries.update",
    "org.fiscal_periods.view",
    "org.fiscal_periods.close",
    "org.fiscal_periods.reopen",
    "org.departments.view",
    "org.departments.create",
    # Contacts
    "contacts.view",
    "contacts.create",
    "contacts.update",
    # Subsystems
    "subsystems.view",
    "subsystems.create",
    "subsystems.update",
    "subsystems.sync",
    # Reports & Dashboard
    "reports.financial.view",
    "reports.dashboard.view",
    # Administration
    "admin.users.view",
    "admin.users.create",
    "admin.users.update",
    "admin.users.manage_permissions",
    "admin.audit_log.view",
])


# ---------------------------------------------------------------------------
# Role → Permissions mapping (source of truth)
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, set[str]] = {
    # ── System Admin ─────────────────────────────────────────────────────
    # Full access to everything.  Manages users, system config.
    "system_admin": set(ALL_PERMISSIONS),

    # ── CFO / Controller ─────────────────────────────────────────────────
    # All financial data across all subsidiaries.  Posts/reverses JEs,
    # closes periods.  No user management.
    "controller": {
        "gl.accounts.view", "gl.accounts.create", "gl.accounts.update",
        "gl.journal_entries.view", "gl.journal_entries.create",
        "gl.journal_entries.post", "gl.journal_entries.reverse",
        "gl.trial_balance.view", "gl.funds.view",
        "org.subsidiaries.view",
        "org.fiscal_periods.view", "org.fiscal_periods.close", "org.fiscal_periods.reopen",
        "org.departments.view",
        "contacts.view", "contacts.create", "contacts.update",
        "subsystems.view", "subsystems.sync",
        "reports.financial.view", "reports.dashboard.view",
        "admin.audit_log.view",
    },

    # ── Senior Accountant ────────────────────────────────────────────────
    # Creates, posts, reverses JEs.  Manages COA, contacts, funds.
    # Can be global or subsidiary-scoped.
    "senior_accountant": {
        "gl.accounts.view", "gl.accounts.create", "gl.accounts.update",
        "gl.journal_entries.view", "gl.journal_entries.create",
        "gl.journal_entries.post", "gl.journal_entries.reverse",
        "gl.trial_balance.view", "gl.funds.view",
        "org.subsidiaries.view", "org.fiscal_periods.view",
        "org.departments.view",
        "contacts.view", "contacts.create", "contacts.update",
        "subsystems.view",
        "reports.financial.view", "reports.dashboard.view",
    },

    # ── Junior Accountant ────────────────────────────────────────────────
    # Creates draft JEs only.  Cannot post or reverse.
    # Subsidiary-scoped.
    "junior_accountant": {
        "gl.accounts.view",
        "gl.journal_entries.view", "gl.journal_entries.create",
        "gl.trial_balance.view", "gl.funds.view",
        "org.subsidiaries.view", "org.fiscal_periods.view",
        "org.departments.view",
        "contacts.view", "contacts.create", "contacts.update",
        "reports.dashboard.view",
    },

    # ── Program Manager ──────────────────────────────────────────────────
    # Views reports/dashboard for their subsidiary.
    # Manages contacts (donors, volunteers).  No GL writes.
    "program_manager": {
        "gl.accounts.view",
        "gl.journal_entries.view",
        "gl.trial_balance.view",
        "org.subsidiaries.view", "org.departments.view",
        "contacts.view", "contacts.create", "contacts.update",
        "reports.financial.view", "reports.dashboard.view",
    },

    # ── Auditor ──────────────────────────────────────────────────────────
    # Read-only across all subsidiaries.  Can view audit log.
    "auditor": {
        "gl.accounts.view",
        "gl.journal_entries.view",
        "gl.trial_balance.view", "gl.funds.view",
        "org.subsidiaries.view", "org.fiscal_periods.view",
        "org.departments.view",
        "contacts.view",
        "subsystems.view",
        "reports.financial.view", "reports.dashboard.view",
        "admin.audit_log.view",
    },

    # ── Viewer ───────────────────────────────────────────────────────────
    # Dashboard and limited data for their subsidiary only.
    "viewer": {
        "reports.dashboard.view",
        "org.subsidiaries.view",
    },
}


# ---------------------------------------------------------------------------
# Valid role names (for DB constraint and validation)
# ---------------------------------------------------------------------------

VALID_ROLES: list[str] = sorted(ROLE_PERMISSIONS.keys())


# ---------------------------------------------------------------------------
# Data scoping — which roles see all subsidiaries vs their own
# ---------------------------------------------------------------------------

GLOBAL_SCOPE_ROLES: set[str] = {"system_admin", "controller", "auditor"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_role_permissions(role: str) -> set[str]:
    """Return the base permission set for a role, or empty set if unknown."""
    return ROLE_PERMISSIONS.get(role, set())


def permission_description(permission: str) -> str:
    """Return a human-readable description for a permission string."""
    _DESCRIPTIONS: dict[str, str] = {
        "gl.accounts.view": "View chart of accounts",
        "gl.accounts.create": "Create new accounts",
        "gl.accounts.update": "Edit existing accounts",
        "gl.journal_entries.view": "View journal entries",
        "gl.journal_entries.create": "Create draft journal entries",
        "gl.journal_entries.post": "Post journal entries to the ledger",
        "gl.journal_entries.reverse": "Reverse posted journal entries",
        "gl.trial_balance.view": "View trial balance",
        "gl.funds.view": "View fund list",
        "org.subsidiaries.view": "View subsidiaries",
        "org.subsidiaries.create": "Create new subsidiaries",
        "org.subsidiaries.update": "Edit subsidiaries",
        "org.fiscal_periods.view": "View fiscal periods",
        "org.fiscal_periods.close": "Close fiscal periods",
        "org.fiscal_periods.reopen": "Reopen fiscal periods",
        "org.departments.view": "View departments",
        "org.departments.create": "Create departments",
        "contacts.view": "View contacts",
        "contacts.create": "Create contacts",
        "contacts.update": "Edit contacts",
        "subsystems.view": "View connected subsystems",
        "subsystems.create": "Create subsystem configs",
        "subsystems.update": "Edit subsystem configs",
        "subsystems.sync": "Trigger subsystem sync",
        "reports.financial.view": "View financial reports (P&L, Balance Sheet, Fund Balances)",
        "reports.dashboard.view": "View dashboard KPIs",
        "admin.users.view": "View user list",
        "admin.users.create": "Create new users",
        "admin.users.update": "Edit users (role, active, subsidiary)",
        "admin.users.manage_permissions": "Grant/revoke individual permissions",
        "admin.audit_log.view": "View audit log",
    }
    return _DESCRIPTIONS.get(permission, permission)
