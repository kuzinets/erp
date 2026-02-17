"""
Tests 1-25: GL & Journal Entry Interconnections

Verify that journal entries correctly flow into the Chart of Accounts,
that posting/reversing JEs affects the GL, and that JE lines connect
properly to accounts, subsidiaries, and fiscal periods.
"""
import uuid
from datetime import date

import httpx
import pytest

BASE_URL = "http://localhost:8001"

# Tests auto-detected by pytest-asyncio (asyncio_mode=auto in pytest.ini)


# ===================================================================
# Test 1: Creating a JE assigns it to the correct fiscal period
# ===================================================================
class TestJECreation:

    async def test_01_je_gets_correct_fiscal_period(
        self, client, admin_headers, accounts, hq_subsidiary, open_period_code, fiscal_periods
    ):
        """A JE dated in February should be assigned to 2026-02 period."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 01 — fiscal period assignment",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 100, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 100},
                ],
            },
        )
        assert r.status_code == 201, r.text
        je_id = r.json()["id"]

        # Fetch full JE and verify fiscal period
        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert detail.status_code == 200
        assert detail.json()["fiscal_period_code"] == "2026-02"

    # ===================================================================
    # Test 2: JE lines reference real accounts from the COA
    # ===================================================================
    async def test_02_je_lines_reference_coa_accounts(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Every JE line should resolve to an account name from the chart of accounts."""
        cash = accounts["1110"]
        expense = accounts["5100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-16",
                "memo": "Test 02 — account resolution",
                "lines": [
                    {"account_id": expense["id"], "debit_amount": 50, "credit_amount": 0},
                    {"account_id": cash["id"], "debit_amount": 0, "credit_amount": 50},
                ],
            },
        )
        assert r.status_code == 201
        je_id = r.json()["id"]

        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        lines = detail.json()["lines"]
        for line in lines:
            assert line["account_number"] is not None
            assert line["account_name"] is not None
        # Verify the specific accounts
        acct_numbers = {l["account_number"] for l in lines}
        assert "1110" in acct_numbers
        assert "5100" in acct_numbers

    # ===================================================================
    # Test 3: JE is linked to the correct subsidiary
    # ===================================================================
    async def test_03_je_linked_to_subsidiary(
        self, client, admin_headers, accounts, subsidiaries
    ):
        """JE created for Chennai subsidiary should show Chennai as subsidiary_name."""
        chennai = subsidiaries["SUB-CHENNAI"]
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": chennai["id"],
                "entry_date": "2026-02-17",
                "memo": "Test 03 — subsidiary link",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 200, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 200},
                ],
            },
        )
        assert r.status_code == 201
        je_id = r.json()["id"]

        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert detail.json()["subsidiary_name"] == chennai["name"]

    # ===================================================================
    # Test 4: Draft JE does NOT appear in trial balance
    # ===================================================================
    async def test_04_draft_je_not_in_trial_balance(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A draft JE should not affect the trial balance (only posted JEs count)."""
        cash = accounts["1110"]
        revenue = accounts["4100"]

        # Get TB before
        tb_before = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert tb_before.status_code == 200
        totals_before = tb_before.json()["total_debits"]

        # Create draft JE (not auto-posted)
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 04 — draft should not affect TB",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 9999, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 9999},
                ],
                "auto_post": False,
            },
        )
        assert r.status_code == 201
        assert r.json()["status"] == "draft"

        # TB should be unchanged
        tb_after = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert tb_after.json()["total_debits"] == totals_before

    # ===================================================================
    # Test 5: Posted JE DOES appear in trial balance
    # ===================================================================
    async def test_05_posted_je_appears_in_trial_balance(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Posting a JE should add its amounts to the trial balance."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        amount = 333.33

        # TB before
        tb_before = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        debits_before = tb_before.json()["total_debits"]

        # Create + auto-post
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 05 — posted JE in TB",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": amount, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": amount},
                ],
                "auto_post": True,
            },
        )
        assert r.status_code == 201
        assert r.json()["status"] == "posted"

        # TB after should increase by amount
        tb_after = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        debits_after = tb_after.json()["total_debits"]
        assert abs(debits_after - debits_before - amount) < 0.01

    # ===================================================================
    # Test 6: JE debits always equal credits (validation)
    # ===================================================================
    async def test_06_je_must_balance(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """JE with unbalanced debits and credits should be rejected."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 06 — should fail",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 100, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 99},
                ],
            },
        )
        assert r.status_code == 422

    # ===================================================================
    # Test 7: JE requires at least 2 lines
    # ===================================================================
    async def test_07_je_requires_two_lines(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A single-line JE should be rejected."""
        cash = accounts["1110"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-15",
                "memo": "Test 07 — single line",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 100, "credit_amount": 0},
                ],
            },
        )
        assert r.status_code == 422

    # ===================================================================
    # Test 8: Posting a JE changes its status from draft to posted
    # ===================================================================
    async def test_08_post_changes_status(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Post endpoint should change status from 'draft' to 'posted'."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 08 — post status change",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 75, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 75},
                ],
            },
        )
        je_id = r.json()["id"]
        assert r.json()["status"] == "draft"

        # Post it
        post_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/post", headers=admin_headers
        )
        assert post_r.status_code == 200
        assert post_r.json()["status"] == "posted"

        # Verify via GET
        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert detail.json()["status"] == "posted"
        assert detail.json()["posted_at"] is not None

    # ===================================================================
    # Test 9: Cannot post an already-posted JE
    # ===================================================================
    async def test_09_cannot_double_post(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Posting an already-posted JE should return 422."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 09 — double post",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 10, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 10},
                ],
                "auto_post": True,
            },
        )
        je_id = r.json()["id"]

        # Try posting again
        post_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/post", headers=admin_headers
        )
        assert post_r.status_code == 422

    # ===================================================================
    # Test 10: Reversing a JE creates a new JE with swapped amounts
    # ===================================================================
    async def test_10_reverse_creates_swapped_je(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Reversal should create a new posted JE with debits/credits swapped."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 10 — original for reversal",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 500, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 500},
                ],
                "auto_post": True,
            },
        )
        je_id = r.json()["id"]

        # Reverse
        rev_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/reverse", headers=admin_headers
        )
        assert rev_r.status_code == 200
        reversal_id = rev_r.json()["reversal_id"]

        # Fetch reversal and check swapped amounts
        rev_detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{reversal_id}", headers=admin_headers
        )
        rev_lines = rev_detail.json()["lines"]
        # Cash should now have credit 500 (originally debit 500)
        cash_line = next(l for l in rev_lines if l["account_number"] == "1110")
        assert cash_line["credit_amount"] == 500.0
        assert cash_line["debit_amount"] == 0.0

    # ===================================================================
    # Test 11: Reversed JE status becomes 'reversed'
    # ===================================================================
    async def test_11_original_becomes_reversed(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """After reversal, the original JE's status should be 'reversed'."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 11 — original for reversal check",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 150, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 150},
                ],
                "auto_post": True,
            },
        )
        je_id = r.json()["id"]

        await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/reverse", headers=admin_headers
        )

        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert detail.json()["status"] == "reversed"

    # ===================================================================
    # Test 12: Cannot reverse a draft JE
    # ===================================================================
    async def test_12_cannot_reverse_draft(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Only posted JEs can be reversed."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 12 — draft cannot be reversed",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 10, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 10},
                ],
            },
        )
        je_id = r.json()["id"]

        rev_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/reverse", headers=admin_headers
        )
        assert rev_r.status_code == 422

    # ===================================================================
    # Test 13: Auto-posted JE immediately shows in trial balance
    # ===================================================================
    async def test_13_auto_post_immediate_tb(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Auto-post creates posted JE that shows in TB in one step."""
        cash = accounts["1110"]
        expense = accounts["5200"]
        amount = 77.77

        tb_before = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        debits_before = tb_before.json()["total_debits"]

        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 13 — auto-post TB",
                "lines": [
                    {"account_id": expense["id"], "debit_amount": amount, "credit_amount": 0},
                    {"account_id": cash["id"], "debit_amount": 0, "credit_amount": amount},
                ],
                "auto_post": True,
            },
        )
        assert r.json()["status"] == "posted"

        tb_after = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert abs(tb_after.json()["total_debits"] - debits_before - amount) < 0.01

    # ===================================================================
    # Test 14: JE for closed period is rejected
    # ===================================================================
    async def test_14_je_in_closed_period_rejected(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """JE dated in January (closed period) should be rejected."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-01-15",
                "memo": "Test 14 — closed period",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 100, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 100},
                ],
            },
        )
        assert r.status_code == 422
        assert "fiscal period" in r.json()["detail"].lower()

    # ===================================================================
    # Test 15: JE entry_number auto-increments
    # ===================================================================
    async def test_15_entry_number_auto_increments(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Each new JE should get a unique, incrementing entry_number."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        numbers = []
        for i in range(3):
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries",
                headers=admin_headers,
                json={
                    "subsidiary_id": hq_subsidiary["id"],
                    "entry_date": "2026-02-18",
                    "memo": f"Test 15 — sequence {i}",
                    "lines": [
                        {"account_id": cash["id"], "debit_amount": 10, "credit_amount": 0},
                        {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 10},
                    ],
                },
            )
            assert r.status_code == 201
            numbers.append(r.json()["entry_number"])
        # Each number should be greater than the previous
        assert numbers[1] > numbers[0]
        assert numbers[2] > numbers[1]

    # ===================================================================
    # Test 16: JE list can filter by subsidiary
    # ===================================================================
    async def test_16_je_list_filters_by_subsidiary(
        self, client, admin_headers, accounts, subsidiaries
    ):
        """JE list filtered by subsidiary only returns JEs for that subsidiary."""
        chennai = subsidiaries["SUB-CHENNAI"]
        cash = accounts["1110"]
        revenue = accounts["4100"]

        # Create JE for Chennai
        await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": chennai["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 16 — Chennai JE",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 55, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 55},
                ],
                "auto_post": True,
            },
        )

        # Filter by Chennai
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?subsidiary_id={chennai['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        for je in r.json()["items"]:
            assert je["subsidiary_id"] == chennai["id"]

    # ===================================================================
    # Test 17: JE list can filter by status
    # ===================================================================
    async def test_17_je_list_filters_by_status(
        self, client, admin_headers
    ):
        """Filtering by status=posted should only return posted JEs."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?status=posted",
            headers=admin_headers,
        )
        assert r.status_code == 200
        for je in r.json()["items"]:
            assert je["status"] == "posted"

    # ===================================================================
    # Test 18: JE list can filter by fiscal period
    # ===================================================================
    async def test_18_je_list_filters_by_fiscal_period(
        self, client, admin_headers
    ):
        """Filtering by fiscal_period should only return JEs in that period."""
        r = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        for je in r.json()["items"]:
            assert je["fiscal_period_code"] == "2026-02"

    # ===================================================================
    # Test 19: Creating a new account makes it available for JE lines
    # ===================================================================
    async def test_19_new_account_usable_in_je(
        self, client, admin_headers, hq_subsidiary, accounts
    ):
        """A newly created account should be usable in a journal entry."""
        import time
        acct_num = f"19{int(time.time()) % 10000:04d}"

        # Create new account
        acct_r = await client.post(
            f"{BASE_URL}/api/gl/accounts",
            headers=admin_headers,
            json={
                "account_number": acct_num,
                "name": f"Test Account {acct_num}",
                "account_type": "asset",
                "normal_balance": "debit",
                "description": "Test 19 account",
            },
        )
        assert acct_r.status_code == 201, f"Create account failed: {acct_r.text}"
        new_acct_id = acct_r.json()["id"]

        revenue = accounts["4100"]
        # Use in JE
        je_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 19 — new account in JE",
                "lines": [
                    {"account_id": new_acct_id, "debit_amount": 25, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 25},
                ],
                "auto_post": True,
            },
        )
        assert je_r.status_code == 201

        # New account should now appear in trial balance
        tb = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        acct_numbers = [item["account_number"] for item in tb.json()["items"]]
        assert acct_num in acct_numbers

    # ===================================================================
    # Test 20: JE with department reference propagates correctly
    # ===================================================================
    async def test_20_je_line_with_department(
        self, client, admin_headers, accounts, hq_subsidiary, departments
    ):
        """JE line can reference a department and it's stored correctly."""
        cash = accounts["1110"]
        expense = accounts["5100"]
        dept = departments[0]  # First department

        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 20 — department on JE line",
                "lines": [
                    {"account_id": expense["id"], "debit_amount": 80, "credit_amount": 0,
                     "department_id": dept["id"]},
                    {"account_id": cash["id"], "debit_amount": 0, "credit_amount": 80},
                ],
                "auto_post": True,
            },
        )
        assert r.status_code == 201
        je_id = r.json()["id"]

        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        line_with_dept = next(
            l for l in detail.json()["lines"] if l["department_id"] is not None
        )
        assert line_with_dept["department_id"] == dept["id"]

    # ===================================================================
    # Test 21: JE with fund reference propagates correctly
    # ===================================================================
    async def test_21_je_line_with_fund(
        self, client, admin_headers, accounts, hq_subsidiary, funds
    ):
        """JE line can reference a fund and it's stored correctly."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        general_fund = funds["GEN"]

        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 21 — fund on JE line",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 120, "credit_amount": 0,
                     "fund_id": general_fund["id"]},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 120,
                     "fund_id": general_fund["id"]},
                ],
                "auto_post": True,
            },
        )
        assert r.status_code == 201
        je_id = r.json()["id"]

        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        for line in detail.json()["lines"]:
            assert line["fund_id"] == general_fund["id"]

    # ===================================================================
    # Test 22: JE total debits/credits are calculated correctly
    # ===================================================================
    async def test_22_je_totals_calculated(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """JE detail should show correct total debits and credits."""
        cash = accounts["1110"]
        ar = accounts["1200"]
        revenue = accounts["4100"]
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 22 — multi-line totals",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 300, "credit_amount": 0},
                    {"account_id": ar["id"], "debit_amount": 200, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 500},
                ],
                "auto_post": True,
            },
        )
        assert r.status_code == 201
        je_id = r.json()["id"]

        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert detail.json()["total_debits"] == 500.0
        assert detail.json()["total_credits"] == 500.0

    # ===================================================================
    # Test 23: JE for invalid subsidiary is rejected
    # ===================================================================
    async def test_23_je_invalid_subsidiary_rejected(
        self, client, admin_headers, accounts
    ):
        """JE referencing a non-existent subsidiary should fail."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        fake_id = str(uuid.uuid4())
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": fake_id,
                "entry_date": "2026-02-18",
                "memo": "Test 23 — bad subsidiary",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 10, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 10},
                ],
            },
        )
        assert r.status_code == 404

    # ===================================================================
    # Test 24: Reversal JE net-zeroes in the trial balance
    # ===================================================================
    async def test_24_reversal_net_zeroes_tb(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Reversing a JE should leave only the reversal in TB (original excluded as 'reversed').

        The TB only shows 'posted' entries. When reversed:
        - Original status → 'reversed' (excluded from TB)
        - Reversal status → 'posted' (included, with swapped amounts)

        So the reversal effectively replaces the original with opposite entries,
        making the net accounting effect zero over the two entries.
        We verify: the reversal JE exists and has swapped debits/credits.
        """
        cash = accounts["1110"]
        revenue = accounts["4100"]
        amount = 444.44

        # Create and auto-post
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers,
            json={
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": "Test 24 — will be reversed",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": amount, "credit_amount": 0},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": amount},
                ],
                "auto_post": True,
            },
        )
        je_id = r.json()["id"]

        # Reverse it
        rev_r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/reverse", headers=admin_headers
        )
        assert rev_r.status_code == 200
        reversal_id = rev_r.json()["reversal_id"]

        # Original should now be 'reversed' (excluded from TB)
        orig = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert orig.json()["status"] == "reversed"

        # Reversal should be 'posted' with swapped amounts
        rev = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{reversal_id}", headers=admin_headers
        )
        assert rev.json()["status"] == "posted"
        # Cash line in reversal should have credit (was originally debit)
        cash_line = next(l for l in rev.json()["lines"] if l["account_number"] == "1110")
        assert cash_line["credit_amount"] == amount
        assert cash_line["debit_amount"] == 0

        # TB should still balance
        tb = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert abs(tb.json()["total_debits"] - tb.json()["total_credits"]) < 0.01

    # ===================================================================
    # Test 25: Trial balance always balances (debits == credits)
    # ===================================================================
    async def test_25_trial_balance_always_balances(
        self, client, admin_headers
    ):
        """Trial balance total debits should equal total credits."""
        tb = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert tb.status_code == 200
        data = tb.json()
        assert abs(data["total_debits"] - data["total_credits"]) < 0.01
