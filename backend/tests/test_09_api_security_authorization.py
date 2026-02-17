"""
Tests 501-600: API Security & Authorization

Comprehensive tests for authentication, authorization, token validation,
role-based access control, SQL injection resistance, and header manipulation
against the KAILASA ERP system running in Docker containers.
"""
import base64
import hashlib
import hmac
import json
import time
import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8001"

JWT_SECRET = "library-jwt-secret-change-in-production-2026"
JWT_ALGORITHM = "HS256"


def _b64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _craft_jwt(payload: dict, secret: str = JWT_SECRET, algorithm: str = "HS256") -> str:
    """Manually craft a JWT token (avoids needing PyJWT installed)."""
    header = {"alg": algorithm, "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


class TestAPISecurityAuthorization:

    # ==================================================================
    # Tests 501-510: Authentication Basics
    # ==================================================================

    async def test_501_valid_login_returns_token(self, client):
        """Valid admin login returns 200 with an access_token."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "admin123"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert len(data["access_token"]) > 0

    async def test_502_invalid_password_returns_401(self, client):
        """Login with wrong password returns 401."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "wrongpassword"},
        )
        assert r.status_code == 401

    async def test_503_nonexistent_user_returns_401(self, client):
        """Login with a user that does not exist returns 401."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "nonexistent_user_xyz", "password": "admin123"},
        )
        assert r.status_code == 401

    async def test_504_empty_credentials_rejected(self, client):
        """Login with empty username and password should fail."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "", "password": ""},
        )
        assert r.status_code in (401, 422)

    async def test_505_missing_password_field(self, client):
        """Login with missing password field returns 422."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry"},
        )
        assert r.status_code == 422

    async def test_506_token_is_valid_jwt_format(self, client):
        """The returned access_token has three dot-separated base64 segments."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "admin123"},
        )
        token = r.json()["access_token"]
        parts = token.split(".")
        assert len(parts) == 3
        # Each part should be non-empty
        for part in parts:
            assert len(part) > 0

    async def test_507_token_type_is_bearer(self, client):
        """Login response token_type should be 'bearer'."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "admin123"},
        )
        assert r.json()["token_type"] == "bearer"

    async def test_508_user_info_in_login_response(self, client):
        """Login response includes user info with correct fields."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "admin123"},
        )
        user = r.json()["user"]
        assert user["username"] == "dmitry"
        assert user["role"] == "admin"
        assert "id" in user
        assert "display_name" in user

    async def test_509_me_endpoint_returns_current_user(self, client, admin_headers):
        """GET /api/auth/me returns current user info with auth."""
        r = await client.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "dmitry"
        assert data["role"] == "admin"

    async def test_510_refresh_returns_new_token(self, client, admin_headers):
        """POST /api/auth/refresh returns a new access_token."""
        r = await client.post(f"{BASE_URL}/api/auth/refresh", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # New token should also be a valid JWT format
        assert len(data["access_token"].split(".")) == 3

    # ==================================================================
    # Tests 511-520: Token Validation
    # ==================================================================

    async def test_511_no_token_returns_401(self, client):
        """Request without Authorization header returns 401."""
        r = await client.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code in (401, 403)

    async def test_512_empty_bearer_returns_401(self, client):
        """Request with 'Bearer ' but no token returns 401."""
        try:
            r = await client.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": "Bearer "},
            )
            assert r.status_code in (400, 401, 403)
        except httpx.LocalProtocolError:
            pass  # Invalid header rejected at transport level — good

    async def test_513_invalid_jwt_string_returns_401(self, client):
        """Request with garbage JWT string returns 401."""
        r = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer not.a.valid.jwt.token"},
        )
        assert r.status_code == 401

    async def test_514_expired_token_returns_401(self, client):
        """A token with exp in the past should be rejected."""
        payload = {
            "sub": "dmitry",
            "role": "admin",
            "user_id": str(uuid.uuid4()),
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        }
        token = _craft_jwt(payload)
        r = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401

    async def test_515_wrong_algorithm_claim(self, client):
        """A token claiming RS256 but signed with HS256 secret should fail."""
        payload = {
            "sub": "dmitry",
            "role": "admin",
            "user_id": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600,
        }
        # Craft token with RS256 in header but sign with HMAC
        header = {"alg": "RS256", "typ": "JWT"}
        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(signature)
        token = f"{header_b64}.{payload_b64}.{sig_b64}"

        r = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401

    async def test_516_malformed_token_returns_401(self, client):
        """A completely malformed token (no dots) returns 401."""
        r = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer abcdef123456"},
        )
        assert r.status_code == 401

    async def test_517_token_with_wrong_secret(self, client):
        """Token signed with a different secret should be rejected."""
        payload = {
            "sub": "dmitry",
            "role": "admin",
            "user_id": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600,
        }
        token = _craft_jwt(payload, secret="completely-wrong-secret-key")
        r = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401

    async def test_518_token_for_nonexistent_user(self, client):
        """Token with sub pointing to nonexistent username should fail."""
        payload = {
            "sub": "ghost_user_does_not_exist",
            "role": "admin",
            "user_id": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600,
        }
        token = _craft_jwt(payload)
        r = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401

    async def test_519_spaces_in_bearer_token(self, client):
        """Authorization header with extra spaces around token should fail."""
        try:
            r = await client.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": "Bearer   "},
            )
            assert r.status_code in (400, 401, 403)
        except httpx.LocalProtocolError:
            pass  # Invalid header rejected at transport level — good

    async def test_520_case_sensitivity_of_bearer(self, client, admin_headers):
        """Authorization with 'bearer' (lowercase) instead of 'Bearer' should be handled."""
        # Extract the token from admin_headers
        auth_value = admin_headers["Authorization"]
        token = auth_value.replace("Bearer ", "")
        r = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"bearer {token}"},
        )
        # OAuth2PasswordBearer in FastAPI is case-insensitive for the scheme
        # It should either work (200) or reject (401) but not 500
        assert r.status_code in (200, 401, 403)

    # ==================================================================
    # Tests 521-530: Admin-only endpoints rejected for VIEWER
    # ==================================================================

    async def test_521_viewer_cannot_create_account(self, client, viewer_headers):
        """Viewer role cannot POST /api/gl/accounts (admin only)."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=viewer_headers,
            json={
                "account_number": "9921",
                "name": "Test Viewer Create",
                "account_type": "asset",
                "normal_balance": "debit",
            },
        )
        assert r.status_code == 403

    async def test_522_viewer_cannot_update_account(self, client, viewer_headers, accounts):
        """Viewer role cannot PUT /api/gl/accounts/{id} (admin only)."""
        acct = accounts["1110"]
        r = await client.put(
            f"{BASE_URL}/api/gl/accounts/{acct['id']}",
            headers=viewer_headers,
            json={"description": "Viewer attempted update"},
        )
        assert r.status_code == 403

    async def test_523_viewer_cannot_create_subsidiary(self, client, viewer_headers):
        """Viewer cannot POST /api/org/subsidiaries (admin only)."""
        r = await client.post(
            f"{BASE_URL}/api/org/subsidiaries",
            headers=viewer_headers,
            json={"code": "VW-TEST", "name": "Viewer Test Subsidiary"},
        )
        assert r.status_code == 403

    async def test_524_viewer_cannot_update_subsidiary(self, client, viewer_headers, hq_subsidiary):
        """Viewer cannot PUT /api/org/subsidiaries/{id} (admin only)."""
        r = await client.put(
            f"{BASE_URL}/api/org/subsidiaries/{hq_subsidiary['id']}",
            headers=viewer_headers,
            json={"name": "Viewer Attempted Rename"},
        )
        assert r.status_code == 403

    async def test_525_viewer_cannot_create_department(self, client, viewer_headers, hq_subsidiary):
        """Viewer cannot POST /api/org/departments (admin only)."""
        r = await client.post(
            f"{BASE_URL}/api/org/departments",
            headers=viewer_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "code": "VW-DEPT",
                "name": "Viewer Dept",
            },
        )
        assert r.status_code == 403

    async def test_526_viewer_cannot_close_fiscal_period(self, client, viewer_headers, fiscal_periods):
        """Viewer cannot POST /api/org/fiscal-periods/{id}/close (admin only)."""
        # Get any period to test with
        period = list(fiscal_periods.values())[0]
        r = await client.post(
            f"{BASE_URL}/api/org/fiscal-periods/{period['id']}/close",
            headers=viewer_headers,
        )
        assert r.status_code == 403

    async def test_527_viewer_cannot_reopen_fiscal_period(self, client, viewer_headers, fiscal_periods):
        """Viewer cannot POST /api/org/fiscal-periods/{id}/reopen (admin only)."""
        period = list(fiscal_periods.values())[0]
        r = await client.post(
            f"{BASE_URL}/api/org/fiscal-periods/{period['id']}/reopen",
            headers=viewer_headers,
        )
        assert r.status_code == 403

    async def test_528_viewer_cannot_create_subsystem(self, client, viewer_headers):
        """Viewer cannot POST /api/subsystems (admin only)."""
        r = await client.post(
            f"{BASE_URL}/api/subsystems",
            headers=viewer_headers,
            json={
                "name": "Viewer System",
                "system_type": "library",
                "base_url": "http://example.com",
            },
        )
        assert r.status_code == 403

    async def test_529_viewer_cannot_update_subsystem(self, client, viewer_headers):
        """Viewer cannot PUT /api/subsystems/{id} (admin only)."""
        # First get a subsystem ID
        list_r = await client.get(f"{BASE_URL}/api/subsystems", headers=viewer_headers)
        if list_r.status_code == 200 and list_r.json()["items"]:
            sub_id = list_r.json()["items"][0]["id"]
        else:
            sub_id = str(uuid.uuid4())

        r = await client.put(
            f"{BASE_URL}/api/subsystems/{sub_id}",
            headers=viewer_headers,
            json={"name": "Viewer Renamed"},
        )
        assert r.status_code == 403

    async def test_530_viewer_cannot_create_account_mapping(self, client, viewer_headers, accounts):
        """Viewer cannot POST /api/subsystems/{id}/mappings (admin only)."""
        fake_id = str(uuid.uuid4())
        r = await client.post(
            f"{BASE_URL}/api/subsystems/{fake_id}/mappings",
            headers=viewer_headers,
            json={
                "source_account_code": "VW-001",
                "target_account_id": accounts["1110"]["id"],
            },
        )
        assert r.status_code == 403

    # ==================================================================
    # Tests 531-540: Admin-only endpoints rejected for ACCOUNTANT
    # ==================================================================

    async def test_531_accountant_cannot_create_account(self, client, accountant_headers):
        """Accountant role cannot POST /api/gl/accounts (admin only)."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=accountant_headers,
            json={
                "account_number": "9931",
                "name": "Acct Create Attempt",
                "account_type": "asset",
                "normal_balance": "debit",
            },
        )
        assert r.status_code == 403

    async def test_532_accountant_cannot_update_account(self, client, accountant_headers, accounts):
        """Accountant cannot PUT /api/gl/accounts/{id} (admin only)."""
        acct = accounts["1110"]
        r = await client.put(
            f"{BASE_URL}/api/gl/accounts/{acct['id']}",
            headers=accountant_headers,
            json={"description": "Accountant attempted update"},
        )
        assert r.status_code == 403

    async def test_533_accountant_cannot_create_subsidiary(self, client, accountant_headers):
        """Accountant cannot POST /api/org/subsidiaries (admin only)."""
        r = await client.post(
            f"{BASE_URL}/api/org/subsidiaries",
            headers=accountant_headers,
            json={"code": "AC-TEST", "name": "Accountant Test Sub"},
        )
        assert r.status_code == 403

    async def test_534_accountant_cannot_update_subsidiary(self, client, accountant_headers, hq_subsidiary):
        """Accountant cannot PUT /api/org/subsidiaries/{id} (admin only)."""
        r = await client.put(
            f"{BASE_URL}/api/org/subsidiaries/{hq_subsidiary['id']}",
            headers=accountant_headers,
            json={"name": "Accountant Attempted Rename"},
        )
        assert r.status_code == 403

    async def test_535_accountant_cannot_create_department(self, client, accountant_headers, hq_subsidiary):
        """Accountant cannot POST /api/org/departments (admin only)."""
        r = await client.post(
            f"{BASE_URL}/api/org/departments",
            headers=accountant_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "code": "AC-DEPT",
                "name": "Accountant Dept",
            },
        )
        assert r.status_code == 403

    async def test_536_accountant_cannot_close_period(self, client, accountant_headers, fiscal_periods):
        """Accountant cannot POST /api/org/fiscal-periods/{id}/close (admin only)."""
        period = list(fiscal_periods.values())[0]
        r = await client.post(
            f"{BASE_URL}/api/org/fiscal-periods/{period['id']}/close",
            headers=accountant_headers,
        )
        assert r.status_code == 403

    async def test_537_accountant_cannot_reopen_period(self, client, accountant_headers, fiscal_periods):
        """Accountant cannot POST /api/org/fiscal-periods/{id}/reopen (admin only)."""
        period = list(fiscal_periods.values())[0]
        r = await client.post(
            f"{BASE_URL}/api/org/fiscal-periods/{period['id']}/reopen",
            headers=accountant_headers,
        )
        assert r.status_code == 403

    async def test_538_accountant_cannot_create_subsystem(self, client, accountant_headers):
        """Accountant cannot POST /api/subsystems (admin only)."""
        r = await client.post(
            f"{BASE_URL}/api/subsystems",
            headers=accountant_headers,
            json={
                "name": "Accountant System",
                "system_type": "library",
                "base_url": "http://example.com",
            },
        )
        assert r.status_code == 403

    async def test_539_accountant_cannot_update_subsystem(self, client, accountant_headers):
        """Accountant cannot PUT /api/subsystems/{id} (admin only)."""
        list_r = await client.get(f"{BASE_URL}/api/subsystems", headers=accountant_headers)
        if list_r.status_code == 200 and list_r.json()["items"]:
            sub_id = list_r.json()["items"][0]["id"]
        else:
            sub_id = str(uuid.uuid4())

        r = await client.put(
            f"{BASE_URL}/api/subsystems/{sub_id}",
            headers=accountant_headers,
            json={"name": "Accountant Renamed"},
        )
        assert r.status_code == 403

    async def test_540_accountant_cannot_create_account_mapping(self, client, accountant_headers, accounts):
        """Accountant cannot POST /api/subsystems/{id}/mappings (admin only)."""
        # Get a subsystem ID if one exists
        list_r = await client.get(f"{BASE_URL}/api/subsystems", headers=accountant_headers)
        if list_r.status_code == 200 and list_r.json()["items"]:
            sub_id = list_r.json()["items"][0]["id"]
        else:
            sub_id = str(uuid.uuid4())

        r = await client.post(
            f"{BASE_URL}/api/subsystems/{sub_id}/mappings",
            headers=accountant_headers,
            json={
                "source_account_code": "AC-001",
                "target_account_id": accounts["1110"]["id"],
            },
        )
        assert r.status_code == 403

    # ==================================================================
    # Tests 541-550: Accountant CAN access accountant-level endpoints
    # ==================================================================

    async def test_541_accountant_can_create_journal_entry(
        self, client, accountant_headers, accounts, hq_subsidiary
    ):
        """Accountant can POST /api/gl/journal-entries (admin or accountant)."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=accountant_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 541 accountant JE",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 100, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 100},
                ],
            },
        )
        assert r.status_code == 201
        assert r.json()["status"] == "draft"

    async def test_542_accountant_can_post_journal_entry(
        self, client, accountant_headers, accounts, hq_subsidiary
    ):
        """Accountant can POST /api/gl/journal-entries/{id}/post."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        # Create a draft JE first
        create_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=accountant_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 542 accountant post",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 50, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 50},
                ],
            },
        )
        assert create_r.status_code == 201
        je_id = create_r.json()["id"]

        # Post it
        post_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/post",
            headers=accountant_headers,
        )
        assert post_r.status_code == 200
        assert post_r.json()["status"] == "posted"

    async def test_543_accountant_can_reverse_journal_entry(
        self, client, accountant_headers, accounts, hq_subsidiary
    ):
        """Accountant can POST /api/gl/journal-entries/{id}/reverse."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        # Create and auto-post
        create_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=accountant_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 543 accountant reverse",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 75, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 75},
                ],
                "auto_post": True,
            },
        )
        je_id = create_r.json()["id"]

        rev_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/reverse",
            headers=accountant_headers,
        )
        assert rev_r.status_code == 200
        assert "reversal_id" in rev_r.json()

    async def test_544_accountant_can_create_contact(self, client, accountant_headers):
        """Accountant can POST /api/contacts (admin or accountant)."""
        r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=accountant_headers,
            json={
                "contact_type": "donor",
                "name": f"Test Donor {uuid.uuid4().hex[:8]}",
                "email": "donor544@test.com",
            },
        )
        assert r.status_code == 201
        assert "id" in r.json()

    async def test_545_accountant_can_update_contact(self, client, accountant_headers):
        """Accountant can PUT /api/contacts/{id}."""
        # Create a contact first
        create_r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=accountant_headers,
            json={
                "contact_type": "vendor",
                "name": f"Test Vendor {uuid.uuid4().hex[:8]}",
            },
        )
        contact_id = create_r.json()["id"]

        r = await client.put(
            f"{BASE_URL}/api/contacts/{contact_id}",
            headers=accountant_headers,
            json={"name": "Updated Vendor Name"},
        )
        assert r.status_code == 200

    async def test_546_accountant_can_sync_subsystem(self, client, accountant_headers):
        """Accountant can POST /api/subsystems/{id}/sync (admin or accountant)."""
        list_r = await client.get(f"{BASE_URL}/api/subsystems", headers=accountant_headers)
        if list_r.status_code == 200 and list_r.json()["items"]:
            sub_id = list_r.json()["items"][0]["id"]
            r = await client.post(
                f"{BASE_URL}/api/subsystems/{sub_id}/sync?fiscal_period=2026-02",
                headers=accountant_headers,
            )
            # Should not be 403 - it may succeed or fail with a service error
            assert r.status_code != 403
        else:
            # No subsystems exist; verify the endpoint at least rejects with 404, not 403
            fake_id = str(uuid.uuid4())
            r = await client.post(
                f"{BASE_URL}/api/subsystems/{fake_id}/sync?fiscal_period=2026-02",
                headers=accountant_headers,
            )
            assert r.status_code != 403

    async def test_547_accountant_can_list_accounts(self, client, accountant_headers):
        """Accountant can GET /api/gl/accounts (any authenticated user)."""
        r = await client.get(f"{BASE_URL}/api/gl/accounts", headers=accountant_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_548_accountant_can_list_journal_entries(self, client, accountant_headers):
        """Accountant can GET /api/gl/journal-entries."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries", headers=accountant_headers
        )
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_549_accountant_can_view_trial_balance(self, client, accountant_headers):
        """Accountant can GET /api/gl/trial-balance."""
        r = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=accountant_headers,
        )
        assert r.status_code == 200

    async def test_550_accountant_can_view_dashboard(self, client, accountant_headers):
        """Accountant can GET /api/dashboard."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=accountant_headers)
        assert r.status_code == 200
        assert "kpis" in r.json()

    # ==================================================================
    # Tests 551-560: Viewer read-only access (all GET endpoints)
    # ==================================================================

    async def test_551_viewer_can_list_accounts(self, client, viewer_headers):
        """Viewer can GET /api/gl/accounts."""
        r = await client.get(f"{BASE_URL}/api/gl/accounts", headers=viewer_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_552_viewer_can_list_journal_entries(self, client, viewer_headers):
        """Viewer can GET /api/gl/journal-entries."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries", headers=viewer_headers
        )
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_553_viewer_can_view_trial_balance(self, client, viewer_headers):
        """Viewer can GET /api/gl/trial-balance."""
        r = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=viewer_headers,
        )
        assert r.status_code == 200

    async def test_554_viewer_can_view_statement_of_activities(self, client, viewer_headers):
        """Viewer can GET /api/reports/statement-of-activities."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            headers=viewer_headers,
        )
        assert r.status_code == 200
        assert "revenue" in r.json()

    async def test_555_viewer_can_view_balance_sheet(self, client, viewer_headers):
        """Viewer can GET /api/reports/statement-of-financial-position."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            headers=viewer_headers,
        )
        assert r.status_code == 200
        assert "assets" in r.json()

    async def test_556_viewer_can_view_dashboard(self, client, viewer_headers):
        """Viewer can GET /api/dashboard."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=viewer_headers)
        assert r.status_code == 200
        assert "kpis" in r.json()

    async def test_557_viewer_can_list_subsidiaries(self, client, viewer_headers):
        """Viewer can GET /api/org/subsidiaries."""
        r = await client.get(
            f"{BASE_URL}/api/org/subsidiaries", headers=viewer_headers
        )
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_558_viewer_can_list_contacts(self, client, viewer_headers):
        """Viewer can GET /api/contacts."""
        r = await client.get(f"{BASE_URL}/api/contacts", headers=viewer_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_559_viewer_can_list_funds(self, client, viewer_headers):
        """Viewer can GET /api/gl/funds."""
        r = await client.get(f"{BASE_URL}/api/gl/funds", headers=viewer_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_560_viewer_can_list_subsystems(self, client, viewer_headers):
        """Viewer can GET /api/subsystems."""
        r = await client.get(f"{BASE_URL}/api/subsystems", headers=viewer_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    # ==================================================================
    # Tests 561-570: Viewer CANNOT write
    # ==================================================================

    async def test_561_viewer_cannot_create_journal_entry(
        self, client, viewer_headers, accounts, hq_subsidiary
    ):
        """Viewer cannot POST /api/gl/journal-entries (requires admin/accountant)."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=viewer_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Viewer JE attempt",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 10, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 10},
                ],
            },
        )
        assert r.status_code == 403

    async def test_562_viewer_cannot_create_contact(self, client, viewer_headers):
        """Viewer cannot POST /api/contacts (requires admin/accountant)."""
        r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=viewer_headers,
            json={"contact_type": "donor", "name": "Viewer Contact Attempt"},
        )
        assert r.status_code == 403

    async def test_563_viewer_cannot_post_journal_entry(
        self, client, viewer_headers, admin_headers, accounts, hq_subsidiary
    ):
        """Viewer cannot POST /api/gl/journal-entries/{id}/post."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        # Create a draft JE as admin
        create_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 563 viewer post attempt",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 10, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 10},
                ],
            },
        )
        je_id = create_r.json()["id"]

        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/post",
            headers=viewer_headers,
        )
        assert r.status_code == 403

    async def test_564_viewer_cannot_reverse_journal_entry(
        self, client, viewer_headers, admin_headers, accounts, hq_subsidiary
    ):
        """Viewer cannot POST /api/gl/journal-entries/{id}/reverse."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        create_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 564 viewer reverse attempt",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 20, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 20},
                ],
                "auto_post": True,
            },
        )
        je_id = create_r.json()["id"]

        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/reverse",
            headers=viewer_headers,
        )
        assert r.status_code == 403

    async def test_565_viewer_cannot_create_account(self, client, viewer_headers):
        """Viewer cannot POST /api/gl/accounts (duplicate of 521 for write section)."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=viewer_headers,
            json={
                "account_number": "9965",
                "name": "Viewer Account",
                "account_type": "expense",
                "normal_balance": "debit",
            },
        )
        assert r.status_code == 403

    async def test_566_viewer_cannot_create_subsidiary(self, client, viewer_headers):
        """Viewer cannot POST /api/org/subsidiaries."""
        r = await client.post(
            f"{BASE_URL}/api/org/subsidiaries",
            headers=viewer_headers,
            json={"code": "VW-566", "name": "Viewer Sub 566"},
        )
        assert r.status_code == 403

    async def test_567_viewer_cannot_create_department(self, client, viewer_headers, hq_subsidiary):
        """Viewer cannot POST /api/org/departments."""
        r = await client.post(
            f"{BASE_URL}/api/org/departments",
            headers=viewer_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "code": "VW-567",
                "name": "Viewer Dept 567",
            },
        )
        assert r.status_code == 403

    async def test_568_viewer_cannot_update_contact(self, client, viewer_headers, admin_headers):
        """Viewer cannot PUT /api/contacts/{id}."""
        # Create contact as admin
        create_r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=admin_headers,
            json={
                "contact_type": "donor",
                "name": f"Contact for 568 {uuid.uuid4().hex[:8]}",
            },
        )
        contact_id = create_r.json()["id"]

        r = await client.put(
            f"{BASE_URL}/api/contacts/{contact_id}",
            headers=viewer_headers,
            json={"name": "Viewer Update Attempt"},
        )
        assert r.status_code == 403

    async def test_569_viewer_cannot_close_period(self, client, viewer_headers, fiscal_periods):
        """Viewer cannot close fiscal period."""
        period = list(fiscal_periods.values())[0]
        r = await client.post(
            f"{BASE_URL}/api/org/fiscal-periods/{period['id']}/close",
            headers=viewer_headers,
        )
        assert r.status_code == 403

    async def test_570_viewer_cannot_create_subsystem_mapping(self, client, viewer_headers, accounts):
        """Viewer cannot POST /api/subsystems/{id}/mappings."""
        fake_id = str(uuid.uuid4())
        r = await client.post(
            f"{BASE_URL}/api/subsystems/{fake_id}/mappings",
            headers=viewer_headers,
            json={
                "source_account_code": "VW-570",
                "target_account_id": accounts["1110"]["id"],
            },
        )
        assert r.status_code == 403

    # ==================================================================
    # Tests 571-580: SQL Injection Attempts
    # ==================================================================

    async def test_571_sql_injection_in_login_username(self, client):
        """SQL injection in username field should return 401, never 500."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "' OR '1'='1'; --", "password": "admin123"},
        )
        assert r.status_code in (401, 422)
        assert r.status_code != 500

    async def test_572_sql_injection_in_login_password(self, client):
        """SQL injection in password field should return 401, never 500."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "' OR '1'='1'; --"},
        )
        assert r.status_code in (401, 422)
        assert r.status_code != 500

    async def test_573_sql_injection_in_search_params(self, client, admin_headers):
        """SQL injection in contact search param should be handled safely."""
        r = await client.get(
            f"{BASE_URL}/api/contacts?search=' OR 1=1; DROP TABLE users; --",
            headers=admin_headers,
        )
        # Should be 200 (empty results) or 422, not 500
        assert r.status_code != 500

    async def test_574_sql_injection_in_subsidiary_code(self, client, admin_headers):
        """SQL injection in subsidiary creation code field."""
        r = await client.post(
            f"{BASE_URL}/api/org/subsidiaries",
            headers=admin_headers,
            json={
                "code": "'; DROP TABLE subsidiaries; --",
                "name": "SQL Injection Test",
            },
        )
        # Should create with sanitized data or reject, not succeed as 201
        assert r.status_code in (400, 409, 422, 500), "SQL injection should not succeed"

    async def test_575_sql_injection_in_account_name(self, client, admin_headers):
        """SQL injection in account name field."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": f"57{int(time.time()) % 10000:04d}",
                "name": "'; DELETE FROM accounts; --",
                "account_type": "asset",
                "normal_balance": "debit",
            },
        )
        # Should either succeed (storing the string literally) or reject, not crash
        assert r.status_code != 500

    async def test_576_sql_injection_in_memo_field(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """SQL injection in JE memo field should be handled safely."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "'; DROP TABLE journal_entries; --",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 10, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 10},
                ],
            },
        )
        assert r.status_code != 500
        # Should succeed because SQLAlchemy uses parameterized queries
        assert r.status_code == 201

    async def test_577_sql_injection_in_contact_name(self, client, admin_headers):
        """SQL injection in contact name field."""
        r = await client.post(
            f"{BASE_URL}/api/contacts",
            headers=admin_headers,
            json={
                "contact_type": "donor",
                "name": "Robert'); DROP TABLE contacts;--",
                "email": "bobby@tables.com",
            },
        )
        assert r.status_code != 500
        # SQLAlchemy parameterized queries should handle this safely
        assert r.status_code == 201

    async def test_578_sql_injection_union_select_in_search(self, client, admin_headers):
        """UNION SELECT injection in contact search should be harmless."""
        r = await client.get(
            f"{BASE_URL}/api/contacts?search=' UNION SELECT username,password_hash FROM users; --",
            headers=admin_headers,
        )
        assert r.status_code != 500
        # Should return empty results or the literal string match
        if r.status_code == 200:
            data = r.json()
            # Results should not contain user credentials
            for item in data.get("items", []):
                assert "password_hash" not in str(item)

    async def test_579_sql_injection_in_fiscal_period_filter(self, client, admin_headers):
        """SQL injection in fiscal_period query parameter."""
        r = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=' OR 1=1; --",
            headers=admin_headers,
        )
        # Should return 404 (period not found) or similar, not 500
        assert r.status_code != 500

    async def test_580_sql_injection_in_status_filter(self, client, admin_headers):
        """SQL injection in journal entry status filter."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?status=' OR 1=1; --",
            headers=admin_headers,
        )
        # Should return empty results or handle safely, not 500
        assert r.status_code != 500

    # ==================================================================
    # Tests 581-590: Header Manipulation
    # ==================================================================

    async def test_581_wrong_content_type(self, client, admin_headers):
        """POST with wrong Content-Type should be handled gracefully."""
        headers = {**admin_headers, "Content-Type": "text/plain"}
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=headers,
            content="not json data",
        )
        # Should return 422 (validation error) or 415 (unsupported media type), not 500
        assert r.status_code in (400, 415, 422)

    async def test_582_extra_headers_dont_break_request(self, client, admin_headers):
        """Extra non-standard headers should not affect request processing."""
        headers = {
            **admin_headers,
            "X-Custom-Header": "test-value",
            "X-Request-ID": str(uuid.uuid4()),
        }
        r = await client.get(f"{BASE_URL}/api/gl/accounts", headers=headers)
        assert r.status_code == 200

    async def test_583_very_long_auth_header(self, client):
        """An extremely long Authorization header should not crash the server."""
        long_token = "A" * 10000
        r = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {long_token}"},
        )
        assert r.status_code in (400, 401, 413, 422)

    async def test_584_multiple_authorization_values(self, client):
        """Two different tokens in separate request attempts - tests idempotency."""
        # First request with an invalid token
        r1 = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_1"},
        )
        assert r1.status_code == 401

        # Second request with another invalid token
        r2 = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_2"},
        )
        assert r2.status_code == 401

    async def test_585_auth_token_in_query_param_not_header(self, client, admin_headers):
        """Token in query parameter instead of header should not authenticate."""
        token = admin_headers["Authorization"].replace("Bearer ", "")
        r = await client.get(
            f"{BASE_URL}/api/auth/me?token={token}",
        )
        # Without Authorization header, should fail
        assert r.status_code in (401, 403)

    async def test_586_xss_in_headers(self, client, admin_headers):
        """XSS attempt in custom headers should not be reflected."""
        headers = {
            **admin_headers,
            "X-Custom": "<script>alert('xss')</script>",
        }
        r = await client.get(f"{BASE_URL}/api/gl/accounts", headers=headers)
        assert r.status_code == 200
        # Response should not contain the script tag
        assert "<script>" not in r.text

    async def test_587_null_bytes_in_auth_header(self, client):
        """Null bytes in Authorization header should be handled."""
        try:
            r = await client.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": "Bearer token\x00with\x00nulls"},
            )
            # Should not crash - return 401 or 400
            assert r.status_code in (400, 401, 403)
        except httpx.LocalProtocolError:
            pass  # Invalid header rejected at transport level — good

    async def test_588_newlines_in_headers(self, client, admin_headers):
        """Headers with newline characters should be handled without HTTP splitting."""
        headers = {**admin_headers}
        # httpx will typically reject or sanitize headers with newlines,
        # so we test with a header value that's close but safe to send
        headers["X-Test"] = "value1 value2"
        r = await client.get(f"{BASE_URL}/api/gl/accounts", headers=headers)
        assert r.status_code == 200

    async def test_589_empty_json_body_on_post(self, client, admin_headers):
        """POST with empty JSON body should return validation error, not 500."""
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={},
        )
        assert r.status_code == 422

    async def test_590_xml_body_instead_of_json(self, client, admin_headers):
        """POST with XML body should not crash the server."""
        headers = {**admin_headers, "Content-Type": "application/xml"}
        r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=headers,
            content="<account><name>test</name></account>",
        )
        # Should return 415 or 422, not 500
        assert r.status_code in (400, 415, 422)

    # ==================================================================
    # Tests 591-600: Cross-Role Verification
    # ==================================================================

    async def test_591_admin_can_do_everything(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Admin can access both read and write endpoints."""
        # Read
        r1 = await client.get(f"{BASE_URL}/api/gl/accounts", headers=admin_headers)
        assert r1.status_code == 200

        # Write (create JE)
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r2 = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 591 admin full access",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 10, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 10},
                ],
            },
        )
        assert r2.status_code == 201

        # Admin-only (create account)
        acct_num = f"91{int(time.time()) % 10000:04d}"
        r3 = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": acct_num,
                "name": f"Admin Test Account {acct_num}",
                "account_type": "asset",
                "normal_balance": "debit",
            },
        )
        assert r3.status_code == 201

    async def test_592_program_manager_has_read_access(self, client):
        """Program manager (priya) can read endpoints."""
        # Login as program manager
        login_r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "priya", "password": "admin123"},
        )
        assert login_r.status_code == 200
        pm_headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}

        # Read endpoints
        r1 = await client.get(f"{BASE_URL}/api/gl/accounts", headers=pm_headers)
        assert r1.status_code == 200

        r2 = await client.get(f"{BASE_URL}/api/dashboard", headers=pm_headers)
        assert r2.status_code == 200

        r3 = await client.get(
            f"{BASE_URL}/api/org/subsidiaries", headers=pm_headers
        )
        assert r3.status_code == 200

    async def test_593_each_role_login_has_correct_role_admin(self, client):
        """Admin login response has role='admin'."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "admin123"},
        )
        assert r.json()["user"]["role"] == "admin"

    async def test_594_each_role_login_has_correct_role_accountant(self, client):
        """Accountant login response has role='accountant'."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "ramantha", "password": "admin123"},
        )
        assert r.json()["user"]["role"] == "accountant"

    async def test_595_each_role_login_has_correct_role_program_manager(self, client):
        """Program manager login response has role='program_manager'."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "priya", "password": "admin123"},
        )
        assert r.json()["user"]["role"] == "program_manager"

    async def test_596_each_role_login_has_correct_role_viewer(self, client):
        """Viewer login response has role='viewer'."""
        r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sarah", "password": "admin123"},
        )
        assert r.json()["user"]["role"] == "viewer"

    async def test_597_me_endpoint_correct_for_each_role(self, client):
        """ME endpoint returns the correct role for each user."""
        users = [
            ("dmitry", "admin"),
            ("ramantha", "accountant"),
            ("priya", "program_manager"),
            ("sarah", "viewer"),
        ]
        for username, expected_role in users:
            login_r = await client.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": username, "password": "admin123"},
            )
            token = login_r.json()["access_token"]
            me_r = await client.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me_r.status_code == 200
            assert me_r.json()["role"] == expected_role, (
                f"Expected {expected_role} for {username}, got {me_r.json()['role']}"
            )

    async def test_598_different_users_get_different_tokens(self, client):
        """Each user login produces a unique token."""
        tokens = set()
        for username in ["dmitry", "ramantha", "priya", "sarah"]:
            r = await client.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": username, "password": "admin123"},
            )
            assert r.status_code == 200
            tokens.add(r.json()["access_token"])
        # All four tokens should be unique
        assert len(tokens) == 4

    async def test_599_token_reuse_works_across_requests(self, client):
        """A single token can be reused for multiple requests."""
        login_r = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "dmitry", "password": "admin123"},
        )
        token = login_r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Make multiple requests with the same token
        r1 = await client.get(f"{BASE_URL}/api/gl/accounts", headers=headers)
        r2 = await client.get(f"{BASE_URL}/api/dashboard", headers=headers)
        r3 = await client.get(f"{BASE_URL}/api/org/subsidiaries", headers=headers)
        r4 = await client.get(f"{BASE_URL}/api/auth/me", headers=headers)

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200
        assert r4.status_code == 200

    async def test_600_public_health_endpoint_no_auth(self, client):
        """GET /api/health requires no authentication and returns healthy status."""
        r = await client.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "service" in data
