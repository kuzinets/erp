"""
Unit Tests — Pydantic validation, auth utilities, CRUD coverage, schema enforcement.

These tests verify individual components in isolation: schema validation,
password hashing, JWT creation, and API endpoint behavior for every route.
Tests 601-700.
"""
import asyncio
import time
import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8001"


class TestUnitTests:
    """100 unit-level tests covering schemas, auth, CRUD, and API contracts."""

    # =================================================================
    # Tests 601-610: Pydantic / schema validation via API
    # =================================================================

    async def test_601_account_type_asset_accepted(self, client, admin_headers):
        """Valid account_type 'asset' should be accepted."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"601{int(time.time()) % 10000:04d}",
                "name": "Test 601 Asset",
                "account_type": "asset",
                "normal_balance": "debit",
            },
        )
        assert r.status_code == 201

    async def test_602_account_type_liability_accepted(self, client, admin_headers):
        """Valid account_type 'liability' should be accepted."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"602{int(time.time()) % 10000:04d}",
                "name": "Test 602 Liability",
                "account_type": "liability",
                "normal_balance": "credit",
            },
        )
        assert r.status_code == 201

    async def test_603_account_type_equity_accepted(self, client, admin_headers):
        """Valid account_type 'equity' should be accepted."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"603{int(time.time()) % 10000:04d}",
                "name": "Test 603 Equity",
                "account_type": "equity",
                "normal_balance": "credit",
            },
        )
        assert r.status_code == 201

    async def test_604_account_type_revenue_accepted(self, client, admin_headers):
        """Valid account_type 'revenue' should be accepted."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"604{int(time.time()) % 10000:04d}",
                "name": "Test 604 Revenue",
                "account_type": "revenue",
                "normal_balance": "credit",
            },
        )
        assert r.status_code == 201

    async def test_605_account_type_expense_accepted(self, client, admin_headers):
        """Valid account_type 'expense' should be accepted."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"605{int(time.time()) % 10000:04d}",
                "name": "Test 605 Expense",
                "account_type": "expense",
                "normal_balance": "debit",
            },
        )
        assert r.status_code == 201

    async def test_606_account_type_invalid_rejected(self, client, admin_headers):
        """Invalid account_type should be rejected with 422."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"606{int(time.time()) % 10000:04d}",
                "name": "Test 606 Invalid",
                "account_type": "cash",
                "normal_balance": "debit",
            },
        )
        assert r.status_code == 422

    async def test_607_normal_balance_debit_accepted(self, client, admin_headers):
        """normal_balance 'debit' is valid."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"607{int(time.time()) % 10000:04d}",
                "name": "Test 607 Debit",
                "account_type": "asset",
                "normal_balance": "debit",
            },
        )
        assert r.status_code == 201

    async def test_608_normal_balance_credit_accepted(self, client, admin_headers):
        """normal_balance 'credit' is valid."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"608{int(time.time()) % 10000:04d}",
                "name": "Test 608 Credit",
                "account_type": "liability",
                "normal_balance": "credit",
            },
        )
        assert r.status_code == 201

    async def test_609_normal_balance_invalid_rejected(self, client, admin_headers):
        """Invalid normal_balance should be rejected."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"609{int(time.time()) % 10000:04d}",
                "name": "Test 609 Invalid Balance",
                "account_type": "asset",
                "normal_balance": "left",
            },
        )
        assert r.status_code == 422

    async def test_610_account_missing_required_fields(self, client, admin_headers):
        """Missing required fields should return 422."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={"name": "Only Name"},
        )
        assert r.status_code == 422

    # =================================================================
    # Tests 611-620: Auth / JWT unit tests via API
    # =================================================================

    async def test_611_login_returns_access_token(self, client):
        """Login should return access_token field."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "admin123"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert len(data["access_token"]) > 20

    async def test_612_login_returns_token_type_bearer(self, client):
        """Login response should have token_type 'bearer'."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "admin123"},
        )
        assert r.json()["token_type"] == "bearer"

    async def test_613_login_returns_user_info(self, client):
        """Login response should include user dict with role."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "admin123"},
        )
        user = r.json()["user"]
        assert user["username"] == "dmitry"
        assert user["role"] == "admin"
        assert "id" in user

    async def test_614_login_wrong_password_401(self, client):
        """Wrong password should return 401."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "wrongpass"},
        )
        assert r.status_code == 401

    async def test_615_login_nonexistent_user_401(self, client):
        """Non-existent user should return 401."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "nobody", "password": "admin123"},
        )
        assert r.status_code == 401

    async def test_616_me_returns_current_user(self, client, admin_headers):
        """GET /me should return current user info."""
        r = await client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "dmitry"
        assert data["role"] == "admin"

    async def test_617_me_without_token_401(self, client):
        """GET /me without token should return 401."""
        r = await client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code in (401, 403)

    async def test_618_refresh_returns_new_token(self, client, admin_headers):
        """POST /refresh should return a new access_token."""
        r = await client.post(f"{BASE_URL}/api/auth/refresh", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_619_token_works_for_protected_routes(self, client):
        """Token from login should work on protected endpoints."""
        login = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sarah", "password": "admin123"},
        )
        token = login.json()["access_token"]
        r = await client.get(
            f"{BASE_URL}/api/gl/accounts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

    async def test_620_invalid_token_rejected(self, client):
        """Random string as token should be rejected."""
        r = await client.get(
            f"{BASE_URL}/api/gl/accounts",
            headers={"Authorization": "Bearer not-a-valid-token"},
        )
        assert r.status_code == 401

    # =================================================================
    # Tests 621-630: Account CRUD coverage
    # =================================================================

    async def test_621_list_accounts_returns_items(self, client, admin_headers):
        """GET /accounts returns items array."""
        r = await client.get(f"{BASE_URL}/api/gl/accounts", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] > 0

    async def test_622_list_accounts_filter_by_type(self, client, admin_headers):
        """Filter accounts by type."""
        r = await client.get(
            f"{BASE_URL}/api/gl/accounts?account_type=revenue",
            headers=admin_headers,
        )
        assert r.status_code == 200
        for acct in r.json()["items"]:
            assert acct["account_type"] == "revenue"

    async def test_623_get_single_account(self, client, admin_headers, accounts):
        """GET /accounts/{id} returns account details."""
        acct = accounts["1110"]
        r = await client.get(
            f"{BASE_URL}/api/gl/accounts/{acct['id']}", headers=admin_headers
        )
        assert r.status_code == 200
        assert r.json()["account_number"] == "1110"

    async def test_624_get_nonexistent_account_404(self, client, admin_headers):
        """GET /accounts/{bad_id} returns 404."""
        fake_id = str(uuid.uuid4())
        r = await client.get(
            f"{BASE_URL}/api/gl/accounts/{fake_id}", headers=admin_headers
        )
        assert r.status_code == 404

    async def test_625_create_account_returns_id(self, client, admin_headers):
        """POST /accounts returns new account with id."""
        num = f"625{int(time.time()) % 10000:04d}"
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": num,
                "name": f"Test Account {num}",
                "account_type": "asset",
                "normal_balance": "debit",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["account_number"] == num

    async def test_626_update_account_name(self, client, admin_headers):
        """PUT /accounts/{id} updates name."""
        # Create
        num = f"626{int(time.time()) % 10000:04d}"
        create_r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": num,
                "name": "Original Name 626",
                "account_type": "asset",
                "normal_balance": "debit",
            },
        )
        acct_id = create_r.json()["id"]

        # Update
        r = await client.put(
            f"{BASE_URL}/api/gl/accounts/{acct_id}",
            headers=admin_headers,
            json={"name": "Updated Name 626"},
        )
        assert r.status_code == 200

        # Verify
        get_r = await client.get(
            f"{BASE_URL}/api/gl/accounts/{acct_id}", headers=admin_headers
        )
        assert get_r.json()["name"] == "Updated Name 626"

    async def test_627_update_nonexistent_account_404(self, client, admin_headers):
        """PUT /accounts/{bad_id} returns 404."""
        r = await client.put(
            f"{BASE_URL}/api/gl/accounts/{uuid.uuid4()}",
            headers=admin_headers,
            json={"name": "No Such Account"},
        )
        assert r.status_code == 404

    async def test_628_accounts_tree_returns_nested(self, client, admin_headers):
        """GET /accounts/tree returns nested structure."""
        r = await client.get(f"{BASE_URL}/api/gl/accounts/tree", headers=admin_headers)
        assert r.status_code == 200
        tree = r.json()["items"]
        assert isinstance(tree, list)
        assert len(tree) > 0

    async def test_629_account_has_all_required_fields(self, client, admin_headers, accounts):
        """Account object has all expected fields."""
        acct = accounts["1110"]
        r = await client.get(
            f"{BASE_URL}/api/gl/accounts/{acct['id']}", headers=admin_headers
        )
        data = r.json()
        for field in ["id", "account_number", "name", "account_type", "normal_balance", "is_active"]:
            assert field in data, f"Missing field: {field}"

    async def test_630_deactivate_account(self, client, admin_headers):
        """Setting is_active=false deactivates an account."""
        num = f"630{int(time.time()) % 10000:04d}"
        create_r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": num,
                "name": "Account to Deactivate 630",
                "account_type": "asset",
                "normal_balance": "debit",
            },
        )
        acct_id = create_r.json()["id"]

        await client.put(
            f"{BASE_URL}/api/gl/accounts/{acct_id}",
            headers=admin_headers,
            json={"is_active": False},
        )

        get_r = await client.get(
            f"{BASE_URL}/api/gl/accounts/{acct_id}", headers=admin_headers
        )
        assert get_r.json()["is_active"] is False

    # =================================================================
    # Tests 631-640: Journal Entry CRUD coverage
    # =================================================================

    async def test_631_create_je_returns_entry_number(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """POST /journal-entries returns id and entry_number."""
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 631",
                "lines": [
                    {"account_id": accounts["1110"]["id"], "debit_amount": 100, "credit_amount": 0},
                    {"account_id": accounts["4100"]["id"], "debit_amount": 0, "credit_amount": 100},
                ],
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert "entry_number" in data
        assert data["status"] == "draft"

    async def test_632_create_je_auto_post(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """auto_post=true creates JE in posted status."""
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 632 auto post",
                "lines": [
                    {"account_id": accounts["1110"]["id"], "debit_amount": 50, "credit_amount": 0},
                    {"account_id": accounts["4100"]["id"], "debit_amount": 0, "credit_amount": 50},
                ],
                "auto_post": True,
            },
        )
        assert r.status_code == 201
        assert r.json()["status"] == "posted"

    async def test_633_get_je_by_id(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """GET /journal-entries/{id} returns full JE with lines."""
        create_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 633 detail",
                "lines": [
                    {"account_id": accounts["1110"]["id"], "debit_amount": 75, "credit_amount": 0},
                    {"account_id": accounts["5100"]["id"], "debit_amount": 0, "credit_amount": 75},
                ],
            },
        )
        je_id = create_r.json()["id"]

        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert data["memo"] == "Test 633 detail"
        assert len(data["lines"]) == 2

    async def test_634_get_nonexistent_je_404(self, client, admin_headers):
        """GET /journal-entries/{bad_id} returns 404."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{uuid.uuid4()}", headers=admin_headers
        )
        assert r.status_code == 404

    async def test_635_list_jes_paginated(self, client, admin_headers):
        """GET /journal-entries returns paginated results."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=5",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["page"] == 1
        assert len(data["items"]) <= 5

    async def test_636_post_je_changes_status(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """POST /journal-entries/{id}/post changes status to posted."""
        create_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 636 to post",
                "lines": [
                    {"account_id": accounts["1110"]["id"], "debit_amount": 30, "credit_amount": 0},
                    {"account_id": accounts["4100"]["id"], "debit_amount": 0, "credit_amount": 30},
                ],
            },
        )
        je_id = create_r.json()["id"]

        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/post", headers=admin_headers
        )
        assert r.status_code == 200
        assert r.json()["status"] == "posted"

    async def test_637_reverse_je_creates_reversal(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """POST /journal-entries/{id}/reverse creates reversal entry."""
        create_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 637 to reverse",
                "lines": [
                    {"account_id": accounts["1110"]["id"], "debit_amount": 40, "credit_amount": 0},
                    {"account_id": accounts["4100"]["id"], "debit_amount": 0, "credit_amount": 40},
                ],
                "auto_post": True,
            },
        )
        je_id = create_r.json()["id"]

        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/reverse", headers=admin_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert "reversal_id" in data
        assert data["status"] == "reversed"

    async def test_638_je_lines_have_account_info(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """JE lines include account_number and account_name."""
        create_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 638 line info",
                "lines": [
                    {"account_id": accounts["1110"]["id"], "debit_amount": 20, "credit_amount": 0},
                    {"account_id": accounts["4100"]["id"], "debit_amount": 0, "credit_amount": 20},
                ],
            },
        )
        je_id = create_r.json()["id"]
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        lines = r.json()["lines"]
        for line in lines:
            assert line["account_number"] is not None
            assert line["account_name"] is not None

    async def test_639_je_total_debits_equals_credits(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """JE response shows matching total_debits and total_credits."""
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 639 totals",
                "lines": [
                    {"account_id": accounts["1110"]["id"], "debit_amount": 123.45, "credit_amount": 0},
                    {"account_id": accounts["4100"]["id"], "debit_amount": 0, "credit_amount": 123.45},
                ],
                "auto_post": True,
            },
        )
        data = r.json()
        assert abs(data["total_debits"] - data["total_credits"]) < 0.01

    async def test_640_je_list_filters_by_status(self, client, admin_headers):
        """JE list can filter by status."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?status=posted",
            headers=admin_headers,
        )
        assert r.status_code == 200
        for je in r.json()["items"]:
            assert je["status"] == "posted"

    # =================================================================
    # Tests 641-650: Organization (Subsidiary/Period/Department) CRUD
    # =================================================================

    async def test_641_list_subsidiaries(self, client, admin_headers):
        """GET /org/subsidiaries returns items."""
        r = await client.get(f"{BASE_URL}/api/org/subsidiaries", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()["items"]) >= 5  # Seed data

    async def test_642_get_subsidiary_by_id(self, client, admin_headers, hq_subsidiary):
        """GET /org/subsidiaries/{id} returns details."""
        r = await client.get(
            f"{BASE_URL}/api/org/subsidiaries/{hq_subsidiary['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["code"] == "HQ"

    async def test_643_create_subsidiary(self, client, admin_headers):
        """POST /org/subsidiaries creates new subsidiary."""
        code = f"U643-{uuid.uuid4().hex[:4].upper()}"
        r = await client.post(
            f"{BASE_URL}/api/org/subsidiaries",
            headers=admin_headers,
            json={"code": code, "name": f"Unit Test 643 {code}"},
        )
        assert r.status_code == 201
        assert r.json()["code"] == code

    async def test_644_update_subsidiary_name(self, client, admin_headers):
        """PUT /org/subsidiaries/{id} updates fields."""
        code = f"U644-{uuid.uuid4().hex[:4].upper()}"
        create_r = await client.post(
            f"{BASE_URL}/api/org/subsidiaries",
            headers=admin_headers,
            json={"code": code, "name": "Original 644"},
        )
        sub_id = create_r.json()["id"]

        r = await client.put(
            f"{BASE_URL}/api/org/subsidiaries/{sub_id}",
            headers=admin_headers,
            json={"name": "Updated 644"},
        )
        assert r.status_code == 200

        get_r = await client.get(
            f"{BASE_URL}/api/org/subsidiaries/{sub_id}", headers=admin_headers
        )
        assert get_r.json()["name"] == "Updated 644"

    async def test_645_get_nonexistent_subsidiary_404(self, client, admin_headers):
        """GET /org/subsidiaries/{bad_id} returns 404."""
        r = await client.get(
            f"{BASE_URL}/api/org/subsidiaries/{uuid.uuid4()}", headers=admin_headers
        )
        assert r.status_code == 404

    async def test_646_list_fiscal_years(self, client, admin_headers):
        """GET /org/fiscal-years returns FY2026."""
        r = await client.get(f"{BASE_URL}/api/org/fiscal-years", headers=admin_headers)
        assert r.status_code == 200
        years = r.json()["items"]
        assert any(y["name"] == "FY2026" for y in years)

    async def test_647_list_fiscal_periods(self, client, admin_headers):
        """GET /org/fiscal-periods returns 12 periods."""
        r = await client.get(f"{BASE_URL}/api/org/fiscal-periods", headers=admin_headers)
        assert r.status_code == 200
        periods = r.json()["items"]
        assert len(periods) == 12

    async def test_648_fiscal_periods_filter_by_status(self, client, admin_headers):
        """GET /org/fiscal-periods?status=open filters correctly."""
        r = await client.get(
            f"{BASE_URL}/api/org/fiscal-periods?status=open", headers=admin_headers
        )
        assert r.status_code == 200
        for p in r.json()["items"]:
            assert p["status"] == "open"

    async def test_649_list_departments(self, client, admin_headers):
        """GET /org/departments returns departments."""
        r = await client.get(f"{BASE_URL}/api/org/departments", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()["items"]) >= 3  # ADMIN, FIN, PROG at least

    async def test_650_create_department(self, client, admin_headers, hq_subsidiary):
        """POST /org/departments creates new department."""
        code = f"D650-{uuid.uuid4().hex[:4].upper()}"
        r = await client.post(
            f"{BASE_URL}/api/org/departments",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "code": code,
                "name": f"Unit Test Dept {code}",
            },
        )
        assert r.status_code == 201

    # =================================================================
    # Tests 651-660: Contact CRUD coverage
    # =================================================================

    async def test_651_list_contacts(self, client, admin_headers):
        """GET /contacts returns paginated contacts."""
        r = await client.get(f"{BASE_URL}/api/contacts", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    async def test_652_create_donor_contact(self, client, admin_headers):
        """POST /contacts creates donor."""
        r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=admin_headers,
            json={
                "contact_type": "donor",
                "name": f"Test Donor {uuid.uuid4().hex[:6]}",
                "email": "donor@test.com",
            },
        )
        assert r.status_code == 201
        assert r.json()["contact_type"] == "donor"

    async def test_653_create_vendor_contact(self, client, admin_headers):
        """POST /contacts creates vendor."""
        r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=admin_headers,
            json={
                "contact_type": "vendor",
                "name": f"Test Vendor {uuid.uuid4().hex[:6]}",
            },
        )
        assert r.status_code == 201
        assert r.json()["contact_type"] == "vendor"

    async def test_654_create_volunteer_contact(self, client, admin_headers):
        """POST /contacts creates volunteer."""
        r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=admin_headers,
            json={
                "contact_type": "volunteer",
                "name": f"Test Volunteer {uuid.uuid4().hex[:6]}",
            },
        )
        assert r.status_code == 201

    async def test_655_create_member_contact(self, client, admin_headers):
        """POST /contacts creates member."""
        r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=admin_headers,
            json={
                "contact_type": "member",
                "name": f"Test Member {uuid.uuid4().hex[:6]}",
            },
        )
        assert r.status_code == 201

    async def test_656_get_contact_by_id(self, client, admin_headers):
        """GET /contacts/{id} returns full contact details."""
        create_r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=admin_headers,
            json={
                "contact_type": "donor",
                "name": "Get Contact Test 656",
                "email": "test656@example.com",
                "phone": "555-0656",
                "city": "Bengaluru",
            },
        )
        contact_id = create_r.json()["id"]

        r = await client.get(
            f"{BASE_URL}/api/contacts/{contact_id}", headers=admin_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Get Contact Test 656"
        assert data["email"] == "test656@example.com"
        assert data["city"] == "Bengaluru"

    async def test_657_update_contact(self, client, admin_headers):
        """PUT /contacts/{id} updates contact fields."""
        create_r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=admin_headers,
            json={"contact_type": "donor", "name": "Before Update 657"},
        )
        contact_id = create_r.json()["id"]

        r = await client.put(
            f"{BASE_URL}/api/contacts/{contact_id}",
            headers=admin_headers,
            json={"name": "After Update 657", "email": "updated@test.com"},
        )
        assert r.status_code == 200

        get_r = await client.get(
            f"{BASE_URL}/api/contacts/{contact_id}", headers=admin_headers
        )
        assert get_r.json()["name"] == "After Update 657"
        assert get_r.json()["email"] == "updated@test.com"

    async def test_658_contact_search(self, client, admin_headers):
        """GET /contacts?search=... filters by name."""
        name = f"Searchable-{uuid.uuid4().hex[:6]}"
        await client.post(
            f"{BASE_URL}/api/contacts",
            headers=admin_headers,
            json={"contact_type": "donor", "name": name},
        )

        r = await client.get(
            f"{BASE_URL}/api/contacts?search={name}", headers=admin_headers
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1
        assert any(name in c["name"] for c in r.json()["items"])

    async def test_659_contact_filter_by_type(self, client, admin_headers):
        """GET /contacts?contact_type=vendor returns only vendors."""
        r = await client.get(
            f"{BASE_URL}/api/contacts?contact_type=vendor", headers=admin_headers
        )
        assert r.status_code == 200
        for c in r.json()["items"]:
            assert c["contact_type"] == "vendor"

    async def test_660_get_nonexistent_contact_404(self, client, admin_headers):
        """GET /contacts/{bad_id} returns 404."""
        r = await client.get(
            f"{BASE_URL}/api/contacts/{uuid.uuid4()}", headers=admin_headers
        )
        assert r.status_code == 404

    # =================================================================
    # Tests 661-670: Trial Balance & Reports CRUD
    # =================================================================

    async def test_661_trial_balance_returns_items(self, client, admin_headers):
        """GET /trial-balance returns items with totals."""
        r = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total_debits" in data
        assert "total_credits" in data

    async def test_662_trial_balance_debits_eq_credits(self, client, admin_headers):
        """TB total_debits should equal total_credits."""
        r = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        data = r.json()
        assert abs(data["total_debits"] - data["total_credits"]) < 0.01

    async def test_663_trial_balance_invalid_period_404(self, client, admin_headers):
        """TB with invalid period returns 404."""
        r = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=9999-99",
            headers=admin_headers,
        )
        assert r.status_code == 404

    async def test_664_soa_returns_revenue_expenses(self, client, admin_headers):
        """SOA returns revenue and expenses sections."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "revenue" in data
        assert "expenses" in data
        assert "change_in_net_assets" in data

    async def test_665_soa_change_equals_revenue_minus_expenses(self, client, admin_headers):
        """SOA change_in_net_assets = revenue.total - expenses.total."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            headers=admin_headers,
        )
        data = r.json()
        expected = data["revenue"]["total"] - data["expenses"]["total"]
        assert abs(data["change_in_net_assets"] - expected) < 0.01

    async def test_666_bs_returns_assets_liabilities(self, client, admin_headers):
        """BS returns assets, liabilities, net_assets sections."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "assets" in data
        assert "liabilities" in data
        assert "net_assets" in data
        assert "is_balanced" in data

    async def test_667_bs_is_balanced(self, client, admin_headers):
        """BS should report is_balanced=True."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            headers=admin_headers,
        )
        assert r.json()["is_balanced"] is True

    async def test_668_fund_balances_returns_all_funds(self, client, admin_headers):
        """Fund balances report includes all active funds."""
        r = await client.get(
            f"{BASE_URL}/api/reports/fund-balances?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        codes = {f["fund_code"] for f in data["items"]}
        assert "GEN" in codes
        assert "FOOD" in codes

    async def test_669_fund_balances_total_matches_sum(self, client, admin_headers):
        """Fund balances total equals sum of item balances."""
        r = await client.get(
            f"{BASE_URL}/api/reports/fund-balances?fiscal_period=2026-02",
            headers=admin_headers,
        )
        data = r.json()
        calc_total = sum(i["balance"] for i in data["items"])
        assert abs(data["total"] - calc_total) < 0.01

    async def test_670_soa_invalid_period_404(self, client, admin_headers):
        """SOA with invalid period returns 404."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=9999-99",
            headers=admin_headers,
        )
        assert r.status_code == 404

    # =================================================================
    # Tests 671-680: Dashboard & health endpoint coverage
    # =================================================================

    async def test_671_dashboard_returns_kpis(self, client, admin_headers):
        """Dashboard returns KPIs object."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
        assert r.status_code == 200
        kpis = r.json()["kpis"]
        for key in ["total_revenue", "total_expenses", "net_income", "journal_entries", "subsidiaries", "funds", "accounts"]:
            assert key in kpis

    async def test_672_dashboard_net_income_eq_rev_minus_exp(self, client, admin_headers):
        """Dashboard net_income = total_revenue - total_expenses."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
        kpis = r.json()["kpis"]
        assert abs(kpis["net_income"] - (kpis["total_revenue"] - kpis["total_expenses"])) < 0.01

    async def test_673_dashboard_recent_jes_list(self, client, admin_headers):
        """Dashboard includes recent_journal_entries list."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
        data = r.json()
        assert "recent_journal_entries" in data
        assert isinstance(data["recent_journal_entries"], list)

    async def test_674_dashboard_connected_systems(self, client, admin_headers):
        """Dashboard includes connected_systems list."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
        data = r.json()
        assert "connected_systems" in data
        assert any(s["system_type"] == "library" for s in data["connected_systems"])

    async def test_675_dashboard_current_period(self, client, admin_headers):
        """Dashboard includes current_period."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
        assert r.json()["current_period"] is not None

    async def test_676_health_check_public(self, client):
        """Health check needs no auth."""
        r = await client.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"

    async def test_677_health_check_has_version(self, client):
        """Health check includes version."""
        r = await client.get(f"{BASE_URL}/api/health")
        assert "version" in r.json()

    async def test_678_health_check_has_service_name(self, client):
        """Health check includes service name."""
        r = await client.get(f"{BASE_URL}/api/health")
        assert "service" in r.json()

    async def test_679_dashboard_subsidiary_count_positive(self, client, admin_headers):
        """Dashboard subsidiary count should be > 0."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
        assert r.json()["kpis"]["subsidiaries"] > 0

    async def test_680_dashboard_account_count_positive(self, client, admin_headers):
        """Dashboard account count should be > 0."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
        assert r.json()["kpis"]["accounts"] > 0

    # =================================================================
    # Tests 681-690: Subsystem CRUD coverage
    # =================================================================

    async def test_681_list_subsystems(self, client, admin_headers):
        """GET /subsystems returns list."""
        r = await client.get(f"{BASE_URL}/api/subsystems", headers=admin_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_682_get_subsystem_by_id(self, client, admin_headers):
        """GET /subsystems/{id} returns config with mappings."""
        # Get the Sangha Library config
        list_r = await client.get(f"{BASE_URL}/api/subsystems", headers=admin_headers)
        configs = list_r.json()["items"]
        assert len(configs) > 0
        config_id = configs[0]["id"]

        r = await client.get(
            f"{BASE_URL}/api/subsystems/{config_id}", headers=admin_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert "account_mappings" in data

    async def test_683_create_subsystem(self, client, admin_headers, hq_subsidiary):
        """POST /subsystems creates new config."""
        r = await client.post(
            f"{BASE_URL}/api/subsystems",
            headers=admin_headers,
            json={
                "name": f"Test System {uuid.uuid4().hex[:6]}",
                "system_type": "custom",
                "base_url": "http://example.com",
                "subsidiary_id": hq_subsidiary["id"],
            },
        )
        assert r.status_code == 201
        assert "id" in r.json()

    async def test_684_update_subsystem(self, client, admin_headers, hq_subsidiary):
        """PUT /subsystems/{id} updates config."""
        create_r = await client.post(
            f"{BASE_URL}/api/subsystems",
            headers=admin_headers,
            json={
                "name": "To Update 684",
                "system_type": "custom",
                "base_url": "http://example.com",
                "subsidiary_id": hq_subsidiary["id"],
            },
        )
        config_id = create_r.json()["id"]

        r = await client.put(
            f"{BASE_URL}/api/subsystems/{config_id}",
            headers=admin_headers,
            json={"name": "Updated 684"},
        )
        assert r.status_code == 200

    async def test_685_get_nonexistent_subsystem_404(self, client, admin_headers):
        """GET /subsystems/{bad_id} returns 404."""
        r = await client.get(
            f"{BASE_URL}/api/subsystems/{uuid.uuid4()}", headers=admin_headers
        )
        assert r.status_code == 404

    async def test_686_list_account_mappings(self, client, admin_headers):
        """GET /subsystems/{id}/mappings returns mappings."""
        list_r = await client.get(f"{BASE_URL}/api/subsystems", headers=admin_headers)
        config_id = list_r.json()["items"][0]["id"]

        r = await client.get(
            f"{BASE_URL}/api/subsystems/{config_id}/mappings", headers=admin_headers
        )
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_687_create_account_mapping(self, client, admin_headers, accounts, hq_subsidiary):
        """POST /subsystems/{id}/mappings creates new mapping."""
        create_r = await client.post(
            f"{BASE_URL}/api/subsystems",
            headers=admin_headers,
            json={
                "name": f"Mapping Test {uuid.uuid4().hex[:6]}",
                "system_type": "custom",
                "base_url": "http://example.com",
                "subsidiary_id": hq_subsidiary["id"],
            },
        )
        config_id = create_r.json()["id"]

        r = await client.post(
            f"{BASE_URL}/api/subsystems/{config_id}/mappings",
            headers=admin_headers,
            json={
                "source_account_code": "EXT-001",
                "target_account_id": accounts["1110"]["id"],
                "description": "Test mapping",
            },
        )
        assert r.status_code == 201

    async def test_688_list_sync_logs(self, client, admin_headers):
        """GET /subsystems/{id}/sync-logs returns log list."""
        list_r = await client.get(f"{BASE_URL}/api/subsystems", headers=admin_headers)
        config_id = list_r.json()["items"][0]["id"]

        r = await client.get(
            f"{BASE_URL}/api/subsystems/{config_id}/sync-logs", headers=admin_headers
        )
        assert r.status_code == 200
        assert "items" in r.json()
        assert "total" in r.json()

    async def test_689_subsystem_has_all_fields(self, client, admin_headers):
        """Subsystem list items have expected fields."""
        r = await client.get(f"{BASE_URL}/api/subsystems", headers=admin_headers)
        item = r.json()["items"][0]
        for field in ["id", "name", "system_type", "base_url", "is_active"]:
            assert field in item, f"Missing field: {field}"

    async def test_690_subsystem_mapping_has_target_info(self, client, admin_headers):
        """Mappings include target account number and name."""
        list_r = await client.get(f"{BASE_URL}/api/subsystems", headers=admin_headers)
        config_id = list_r.json()["items"][0]["id"]

        r = await client.get(
            f"{BASE_URL}/api/subsystems/{config_id}/mappings", headers=admin_headers
        )
        if r.json()["items"]:
            mapping = r.json()["items"][0]
            assert "target_account_number" in mapping
            assert "target_account_name" in mapping

    # =================================================================
    # Tests 691-700: Fund, list endpoints, and misc CRUD
    # =================================================================

    async def test_691_list_funds(self, client, admin_headers):
        """GET /funds returns active funds."""
        r = await client.get(f"{BASE_URL}/api/gl/funds", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 4  # GEN, FOOD, EDU, BLDG

    async def test_692_fund_has_all_fields(self, client, admin_headers):
        """Fund objects have code, name, fund_type, is_active."""
        r = await client.get(f"{BASE_URL}/api/gl/funds", headers=admin_headers)
        fund = r.json()["items"][0]
        for field in ["id", "code", "name", "fund_type", "is_active"]:
            assert field in fund

    async def test_693_fund_types_correct(self, client, admin_headers):
        """All fund types are valid."""
        r = await client.get(f"{BASE_URL}/api/gl/funds", headers=admin_headers)
        valid_types = {"unrestricted", "temporarily_restricted", "permanently_restricted"}
        for fund in r.json()["items"]:
            assert fund["fund_type"] in valid_types

    async def test_694_je_list_filter_by_subsidiary(self, client, admin_headers, hq_subsidiary):
        """JE list filter by subsidiary returns only matching entries."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?subsidiary_id={hq_subsidiary['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        for je in r.json()["items"]:
            assert je["subsidiary_id"] == hq_subsidiary["id"]

    async def test_695_je_list_filter_by_fiscal_period(self, client, admin_headers):
        """JE list filter by fiscal_period."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        for je in r.json()["items"]:
            assert je["fiscal_period_code"] == "2026-02"

    async def test_696_contact_pagination(self, client, admin_headers):
        """Contact pagination works."""
        r = await client.get(
            f"{BASE_URL}/api/contacts?page=1&page_size=2", headers=admin_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1

    async def test_697_tb_filter_by_subsidiary(self, client, admin_headers, hq_subsidiary):
        """TB can filter by subsidiary."""
        r = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02&subsidiary_id={hq_subsidiary['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        # TB should still balance even filtered
        data = r.json()
        assert abs(data["total_debits"] - data["total_credits"]) < 0.01

    async def test_698_soa_filter_by_subsidiary(self, client, admin_headers, hq_subsidiary):
        """SOA can filter by subsidiary."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02&subsidiary_id={hq_subsidiary['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["subsidiary_id"] == hq_subsidiary["id"]

    async def test_699_bs_filter_by_subsidiary(self, client, admin_headers, hq_subsidiary):
        """BS can filter by subsidiary."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02&subsidiary_id={hq_subsidiary['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["is_balanced"] is True

    async def test_700_departments_filter_by_subsidiary(self, client, admin_headers, hq_subsidiary):
        """Departments filter by subsidiary."""
        r = await client.get(
            f"{BASE_URL}/api/org/departments?subsidiary_id={hq_subsidiary['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        for d in r.json()["items"]:
            assert d["subsidiary_id"] == hq_subsidiary["id"]
