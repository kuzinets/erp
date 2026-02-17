"""
Test fixtures for KAILASA ERP interconnectedness tests.

Tests run against the LIVE Docker containers (backend on port 8001, DB on port 5433).
They verify that creating/modifying data in one module correctly propagates to all
related modules — GL, Trial Balance, Financial Statements, Fund Balances, Dashboard, etc.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8001"
ADMIN_CREDS = {"username": "dmitry", "password": "admin123"}
ACCOUNTANT_CREDS = {"username": "ramantha", "password": "admin123"}
VIEWER_CREDS = {"username": "sarah", "password": "admin123"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def login(client: httpx.AsyncClient, creds: dict) -> str:
    """Login and return the JWT token."""
    r = await client.post(f"{BASE_URL}/api/auth/login", json=creds)
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Return auth header dict for a given token."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Session-scoped fixtures (login once, share across all tests)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def client():
    """Shared async HTTP client for all tests."""
    async with httpx.AsyncClient(timeout=30.0) as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def admin_token(client):
    """Admin JWT token."""
    return await login(client, ADMIN_CREDS)


@pytest_asyncio.fixture(scope="session")
async def accountant_token(client):
    """Accountant JWT token."""
    return await login(client, ACCOUNTANT_CREDS)


@pytest_asyncio.fixture(scope="session")
async def viewer_token(client):
    """Viewer JWT token."""
    return await login(client, VIEWER_CREDS)


@pytest_asyncio.fixture(scope="session")
async def admin_headers(admin_token):
    """Auth headers for admin."""
    return auth_headers(admin_token)


@pytest_asyncio.fixture(scope="session")
async def accountant_headers(accountant_token):
    """Auth headers for accountant."""
    return auth_headers(accountant_token)


@pytest_asyncio.fixture(scope="session")
async def viewer_headers(viewer_token):
    """Auth headers for viewer."""
    return auth_headers(viewer_token)


# ---------------------------------------------------------------------------
# Lookup fixtures — fetch seed data IDs once
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def subsidiaries(client, admin_headers):
    """All active subsidiaries, keyed by code."""
    r = await client.get(f"{BASE_URL}/api/org/subsidiaries", headers=admin_headers)
    assert r.status_code == 200
    return {s["code"]: s for s in r.json()["items"]}


@pytest_asyncio.fixture(scope="session")
async def hq_subsidiary(subsidiaries):
    """HQ subsidiary dict."""
    return subsidiaries["HQ"]


@pytest_asyncio.fixture(scope="session")
async def accounts(client, admin_headers):
    """All active accounts, keyed by account_number."""
    r = await client.get(f"{BASE_URL}/api/gl/accounts", headers=admin_headers)
    assert r.status_code == 200
    return {a["account_number"]: a for a in r.json()["items"]}


@pytest_asyncio.fixture(scope="session")
async def funds(client, admin_headers):
    """All active funds, keyed by code."""
    r = await client.get(f"{BASE_URL}/api/gl/funds", headers=admin_headers)
    assert r.status_code == 200
    return {f["code"]: f for f in r.json()["items"]}


@pytest_asyncio.fixture(scope="session")
async def fiscal_periods(client, admin_headers):
    """All fiscal periods, keyed by period_code."""
    r = await client.get(f"{BASE_URL}/api/org/fiscal-periods", headers=admin_headers)
    assert r.status_code == 200
    return {p["period_code"]: p for p in r.json()["items"]}


@pytest_asyncio.fixture(scope="session")
async def departments(client, admin_headers):
    """All departments."""
    r = await client.get(f"{BASE_URL}/api/org/departments", headers=admin_headers)
    assert r.status_code == 200
    return r.json()["items"]


# ---------------------------------------------------------------------------
# Current open period helper
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def open_period_code(fiscal_periods):
    """Return an open fiscal period code (February or current month)."""
    for code, p in sorted(fiscal_periods.items()):
        if p["status"] == "open":
            return code
    pytest.fail("No open fiscal period found!")
