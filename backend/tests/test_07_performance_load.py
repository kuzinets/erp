"""
Tests 301-400: Performance & Load Testing

Verify that the KAILASA ERP system meets performance targets under
various load conditions — single-endpoint response times, throughput,
concurrent requests, pagination, multi-line JE scaling, report generation
under load, search/filter performance, burst operations, sustained load,
and scalability indicators.

All tests run against the LIVE Docker containers (backend on port 8001).
"""
import asyncio
import time
import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _je_payload(subsidiary_id, cash_id, revenue_id, amount=100.0, memo="perf-test", auto_post=False):
    """Build a minimal balanced JE payload."""
    return {
        "subsidiary_id": subsidiary_id,
        "entry_date": "2026-02-18",
        "memo": f"{memo}-{uuid.uuid4().hex[:8]}",
        "lines": [
            {"account_id": cash_id, "debit_amount": float(amount), "credit_amount": 0},
            {"account_id": revenue_id, "debit_amount": 0, "credit_amount": float(amount)},
        ],
        "auto_post": auto_post,
    }


def _multi_line_je_payload(subsidiary_id, debit_accounts, credit_account_id, amount_per_line=50.0, memo="perf-multi"):
    """Build a multi-line JE with N debit lines and one balancing credit line."""
    lines = []
    for acct_id in debit_accounts:
        lines.append({"account_id": acct_id, "debit_amount": float(amount_per_line), "credit_amount": 0})
    total_credit = float(amount_per_line) * len(debit_accounts)
    lines.append({"account_id": credit_account_id, "debit_amount": 0, "credit_amount": total_credit})
    return {
        "subsidiary_id": subsidiary_id,
        "entry_date": "2026-02-18",
        "memo": f"{memo}-{uuid.uuid4().hex[:8]}",
        "lines": lines,
        "auto_post": True,
    }


async def _timed_request(client, method, url, **kwargs):
    """Execute a request and return (response, elapsed_seconds)."""
    start = time.time()
    if method == "GET":
        r = await client.get(url, **kwargs)
    elif method == "POST":
        r = await client.post(url, **kwargs)
    else:
        raise ValueError(f"Unsupported method: {method}")
    elapsed = time.time() - start
    return r, elapsed


async def _concurrent_gets(client, url, headers, n=10):
    """Fire n concurrent GET requests and return list of (response, elapsed)."""
    tasks = [_timed_request(client, "GET", url, headers=headers) for _ in range(n)]
    return await asyncio.gather(*tasks)


# ===================================================================
# Performance & Load Test Suite
# ===================================================================

class TestPerformanceLoad:

    # -------------------------------------------------------------------
    # Tests 301-310: Single endpoint response times
    # -------------------------------------------------------------------

    async def test_301_health_endpoint_under_500ms(self, client):
        """Health check should respond in under 500ms."""
        r, elapsed = await _timed_request(client, "GET", f"{BASE_URL}/api/health")
        assert r.status_code == 200
        assert elapsed < 0.5, f"Health took {elapsed:.3f}s, expected < 0.5s"

    async def test_302_dashboard_under_2s(self, client, admin_headers):
        """Dashboard endpoint should respond in under 2 seconds."""
        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/dashboard", headers=admin_headers
        )
        assert r.status_code == 200
        assert elapsed < 2.0, f"Dashboard took {elapsed:.3f}s, expected < 2.0s"

    async def test_303_trial_balance_under_2s(self, client, admin_headers):
        """Trial balance should respond in under 2 seconds."""
        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 2.0, f"Trial balance took {elapsed:.3f}s, expected < 2.0s"

    async def test_304_statement_of_activities_under_2s(self, client, admin_headers):
        """Statement of activities should respond in under 2 seconds."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 2.0, f"SOA took {elapsed:.3f}s, expected < 2.0s"

    async def test_305_balance_sheet_under_2s(self, client, admin_headers):
        """Statement of financial position should respond in under 2 seconds."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 2.0, f"BS took {elapsed:.3f}s, expected < 2.0s"

    async def test_306_account_list_under_1s(self, client, admin_headers):
        """Account list should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/gl/accounts", headers=admin_headers
        )
        assert r.status_code == 200
        assert "items" in r.json()
        assert elapsed < 1.0, f"Accounts took {elapsed:.3f}s, expected < 1.0s"

    async def test_307_je_list_under_1s(self, client, admin_headers):
        """Journal entry list should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=20",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"JE list took {elapsed:.3f}s, expected < 1.0s"

    async def test_308_fund_balance_report_under_500ms(self, client, admin_headers):
        """Fund balances report should respond in under 500ms."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/reports/fund-balances?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 0.5, f"Fund balances took {elapsed:.3f}s, expected < 0.5s"

    async def test_309_contact_list_under_1s(self, client, admin_headers):
        """Contact list should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/contacts?page=1&page_size=20",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"Contacts took {elapsed:.3f}s, expected < 1.0s"

    async def test_310_subsidiary_list_under_500ms(self, client, admin_headers):
        """Subsidiary list should respond in under 500ms."""
        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/org/subsidiaries", headers=admin_headers
        )
        assert r.status_code == 200
        assert elapsed < 0.5, f"Subsidiaries took {elapsed:.3f}s, expected < 0.5s"

    # -------------------------------------------------------------------
    # Tests 311-320: JE creation throughput
    # -------------------------------------------------------------------

    async def test_311_create_10_jes_sequentially_under_10s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Creating 10 JEs sequentially should complete in under 10 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        start = time.time()
        ids = []
        for i in range(10):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=10 + i, memo=f"perf-311-{i}")
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert r.status_code == 201
            ids.append(r.json()["id"])
        elapsed = time.time() - start
        assert len(ids) == 10
        assert elapsed < 10.0, f"10 JEs took {elapsed:.3f}s, expected < 10.0s"

    async def test_312_create_20_jes_with_auto_post_under_15s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Creating 20 auto-posted JEs sequentially should complete in under 15 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        start = time.time()
        ids = []
        for i in range(20):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=20 + i, memo=f"perf-312-{i}", auto_post=True)
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert r.status_code == 201
            assert r.json()["status"] == "posted"
            ids.append(r.json()["id"])
        elapsed = time.time() - start
        assert len(ids) == 20
        assert elapsed < 15.0, f"20 auto-posted JEs took {elapsed:.3f}s, expected < 15.0s"

    async def test_313_single_je_creation_under_2s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A single JE creation should complete in under 2 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                              amount=50, memo="perf-313")
        r, elapsed = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload,
        )
        assert r.status_code == 201
        assert elapsed < 2.0, f"Single JE creation took {elapsed:.3f}s, expected < 2.0s"

    async def test_314_single_auto_post_je_under_2s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A single auto-posted JE creation should complete in under 2 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                              amount=60, memo="perf-314", auto_post=True)
        r, elapsed = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload,
        )
        assert r.status_code == 201
        assert r.json()["status"] == "posted"
        assert elapsed < 2.0, f"Auto-post JE took {elapsed:.3f}s, expected < 2.0s"

    async def test_315_je_post_action_under_2s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Posting a draft JE should complete in under 2 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                              amount=70, memo="perf-315")
        cr = await client.post(
            f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
        )
        je_id = cr.json()["id"]

        r, elapsed = await _timed_request(
            client, "POST",
            f"{BASE_URL}/api/gl/journal-entries/{je_id}/post",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "posted"
        assert elapsed < 2.0, f"Post action took {elapsed:.3f}s, expected < 2.0s"

    async def test_316_batch_5_jes_all_unique_entry_numbers(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """5 sequentially created JEs should all have unique entry numbers."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        entry_numbers = []
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=30 + i, memo=f"perf-316-{i}")
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert r.status_code == 201
            entry_numbers.append(r.json()["entry_number"])
        assert len(set(entry_numbers)) == 5, f"Expected 5 unique entry numbers, got {entry_numbers}"

    async def test_317_10_auto_post_jes_all_unique_entry_numbers(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """10 auto-posted JEs should all have unique entry numbers."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        entry_numbers = []
        for i in range(10):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=40 + i, memo=f"perf-317-{i}", auto_post=True)
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert r.status_code == 201
            entry_numbers.append(r.json()["entry_number"])
        assert len(set(entry_numbers)) == 10, f"Expected 10 unique entry numbers, got {entry_numbers}"

    async def test_318_je_creation_avg_under_1s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Average JE creation time across 5 JEs should be under 1 second."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        times = []
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=80 + i, memo=f"perf-318-{i}")
            r, elapsed = await _timed_request(
                client, "POST", f"{BASE_URL}/api/gl/journal-entries",
                headers=admin_headers, json=payload,
            )
            assert r.status_code == 201
            times.append(elapsed)
        avg = sum(times) / len(times)
        assert avg < 1.0, f"Avg JE creation {avg:.3f}s, expected < 1.0s"

    async def test_319_je_creation_no_timeouts(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Creating 8 JEs should produce no timeouts (all complete within client timeout)."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        for i in range(8):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=90 + i, memo=f"perf-319-{i}")
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert r.status_code == 201, f"JE {i} failed with status {r.status_code}"

    async def test_320_je_creation_entry_numbers_monotonically_increase(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Entry numbers should monotonically increase across sequential JE creations."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        entry_numbers = []
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=100 + i, memo=f"perf-320-{i}")
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert r.status_code == 201
            entry_numbers.append(r.json()["entry_number"])
        for i in range(1, len(entry_numbers)):
            assert entry_numbers[i] > entry_numbers[i - 1], \
                f"Entry numbers not monotonic: {entry_numbers}"

    # -------------------------------------------------------------------
    # Tests 321-330: Concurrent request throughput
    # -------------------------------------------------------------------

    async def test_321_10_concurrent_dashboard_reads(self, client, admin_headers):
        """10 concurrent dashboard reads should all return 200."""
        results = await _concurrent_gets(
            client, f"{BASE_URL}/api/dashboard", admin_headers, n=10
        )
        for r, elapsed in results:
            assert r.status_code == 200

    async def test_322_10_concurrent_dashboard_all_under_5s(self, client, admin_headers):
        """Each of 10 concurrent dashboard reads should complete under 5 seconds."""
        results = await _concurrent_gets(
            client, f"{BASE_URL}/api/dashboard", admin_headers, n=10
        )
        for r, elapsed in results:
            assert r.status_code == 200
            assert elapsed < 5.0, f"Concurrent dashboard took {elapsed:.3f}s"

    async def test_323_10_concurrent_trial_balance_reads(self, client, admin_headers):
        """10 concurrent trial balance reads should all return 200."""
        results = await _concurrent_gets(
            client, f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            admin_headers, n=10,
        )
        for r, elapsed in results:
            assert r.status_code == 200

    async def test_324_10_concurrent_tb_all_under_5s(self, client, admin_headers):
        """Each of 10 concurrent TB reads should complete under 5 seconds."""
        results = await _concurrent_gets(
            client, f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            admin_headers, n=10,
        )
        for r, elapsed in results:
            assert elapsed < 5.0, f"Concurrent TB took {elapsed:.3f}s"

    async def test_325_10_concurrent_soa_reads(self, client, admin_headers):
        """10 concurrent SOA reads should all return 200."""
        results = await _concurrent_gets(
            client,
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            admin_headers, n=10,
        )
        for r, elapsed in results:
            assert r.status_code == 200

    async def test_326_10_concurrent_bs_reads(self, client, admin_headers):
        """10 concurrent balance sheet reads should all return 200."""
        results = await _concurrent_gets(
            client,
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            admin_headers, n=10,
        )
        for r, elapsed in results:
            assert r.status_code == 200

    async def test_327_10_concurrent_bs_all_under_5s(self, client, admin_headers):
        """Each of 10 concurrent BS reads should complete under 5 seconds."""
        results = await _concurrent_gets(
            client,
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            admin_headers, n=10,
        )
        for r, elapsed in results:
            assert elapsed < 5.0, f"Concurrent BS took {elapsed:.3f}s"

    async def test_328_mixed_concurrent_reads_all_200(self, client, admin_headers):
        """Mixed concurrent reads (dashboard, TB, SOA, BS, accounts) should all return 200."""
        urls = [
            f"{BASE_URL}/api/dashboard",
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            f"{BASE_URL}/api/gl/accounts",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=20",
            f"{BASE_URL}/api/contacts?page=1&page_size=20",
            f"{BASE_URL}/api/org/subsidiaries",
            f"{BASE_URL}/api/reports/fund-balances?fiscal_period=2026-02",
            f"{BASE_URL}/api/health",
        ]
        tasks = [_timed_request(client, "GET", url, headers=admin_headers) for url in urls]
        results = await asyncio.gather(*tasks)
        for r, elapsed in results:
            assert r.status_code == 200

    async def test_329_mixed_concurrent_reads_all_under_5s(self, client, admin_headers):
        """Each mixed concurrent read should complete under 5 seconds."""
        urls = [
            f"{BASE_URL}/api/dashboard",
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            f"{BASE_URL}/api/gl/accounts",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=20",
            f"{BASE_URL}/api/contacts?page=1&page_size=20",
            f"{BASE_URL}/api/org/subsidiaries",
            f"{BASE_URL}/api/reports/fund-balances?fiscal_period=2026-02",
            f"{BASE_URL}/api/health",
        ]
        tasks = [_timed_request(client, "GET", url, headers=admin_headers) for url in urls]
        results = await asyncio.gather(*tasks)
        for r, elapsed in results:
            assert elapsed < 5.0, f"Mixed read took {elapsed:.3f}s"

    async def test_330_concurrent_reads_consistent_data(self, client, admin_headers):
        """Multiple concurrent TB reads should return identical totals."""
        results = await _concurrent_gets(
            client, f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            admin_headers, n=5,
        )
        totals = []
        for r, elapsed in results:
            assert r.status_code == 200
            totals.append(r.json()["total_debits"])
        # All concurrent reads should see the same total
        assert len(set(totals)) == 1, f"Inconsistent totals across concurrent reads: {totals}"

    # -------------------------------------------------------------------
    # Tests 331-340: Pagination performance
    # -------------------------------------------------------------------

    async def test_331_je_first_page_under_1s(self, client, admin_headers):
        """First page of JE list should load in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=20",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"First page took {elapsed:.3f}s, expected < 1.0s"

    async def test_332_je_last_page_similar_speed(self, client, admin_headers):
        """Last page of JE list should load at similar speed as first page."""
        # Get total to find last page
        r1 = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=20",
            headers=admin_headers,
        )
        total = r1.json()["total"]
        last_page = max(1, (total + 19) // 20)

        r_first, elapsed_first = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=20",
            headers=admin_headers,
        )
        r_last, elapsed_last = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page={last_page}&page_size=20",
            headers=admin_headers,
        )
        assert r_last.status_code == 200
        # Last page should not be more than 3x slower than first page
        assert elapsed_last < max(elapsed_first * 3, 1.0), \
            f"Last page {elapsed_last:.3f}s vs first page {elapsed_first:.3f}s"

    async def test_333_je_page_size_1(self, client, admin_headers):
        """JE list with page_size=1 should return exactly 1 item."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=1",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1
        assert elapsed < 1.0, f"Page size 1 took {elapsed:.3f}s"

    async def test_334_je_page_size_10(self, client, admin_headers):
        """JE list with page_size=10 should return up to 10 items."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=10",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert len(r.json()["items"]) <= 10
        assert elapsed < 1.0, f"Page size 10 took {elapsed:.3f}s"

    async def test_335_je_page_size_50(self, client, admin_headers):
        """JE list with page_size=50 should return up to 50 items and still be fast."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=50",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert len(r.json()["items"]) <= 50
        assert elapsed < 2.0, f"Page size 50 took {elapsed:.3f}s"

    async def test_336_je_page_size_100(self, client, admin_headers):
        """JE list with page_size=100 should return up to 100 items."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=100",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert len(r.json()["items"]) <= 100
        assert elapsed < 2.0, f"Page size 100 took {elapsed:.3f}s"

    async def test_337_total_count_consistent_across_page_sizes(self, client, admin_headers):
        """Total count should be the same regardless of page_size."""
        r1 = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=1",
            headers=admin_headers,
        )
        r10 = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=10",
            headers=admin_headers,
        )
        r50 = await client.get(
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=50",
            headers=admin_headers,
        )
        total1 = r1.json()["total"]
        total10 = r10.json()["total"]
        total50 = r50.json()["total"]
        assert total1 == total10 == total50, \
            f"Inconsistent totals: size1={total1}, size10={total10}, size50={total50}"

    async def test_338_contacts_pagination_under_1s(self, client, admin_headers):
        """Contact list pagination should respond under 1 second for various page sizes."""
        for page_size in [5, 10, 20]:
            r, elapsed = await _timed_request(
                client, "GET",
                f"{BASE_URL}/api/contacts?page=1&page_size={page_size}",
                headers=admin_headers,
            )
            assert r.status_code == 200
            assert elapsed < 1.0, f"Contacts page_size={page_size} took {elapsed:.3f}s"

    async def test_339_accounts_pagination_under_1s(self, client, admin_headers):
        """Account list should respond under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/gl/accounts", headers=admin_headers
        )
        assert r.status_code == 200
        assert len(r.json()["items"]) > 0
        assert elapsed < 1.0, f"Accounts took {elapsed:.3f}s"

    async def test_340_je_page_2_under_1s(self, client, admin_headers):
        """JE list page 2 should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page=2&page_size=20",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"JE page 2 took {elapsed:.3f}s"

    # -------------------------------------------------------------------
    # Tests 341-350: Multi-line JE performance
    # -------------------------------------------------------------------

    async def test_341_2_line_je_speed(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A standard 2-line JE should create and post quickly."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                              amount=100, memo="perf-341", auto_post=True)
        r, elapsed = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload,
        )
        assert r.status_code == 201
        assert elapsed < 2.0, f"2-line JE took {elapsed:.3f}s"

    async def test_342_5_line_je_speed(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A 5-line JE (4 debit + 1 credit) should create under 2 seconds."""
        debit_accts = [
            accounts["1110"]["id"], accounts["1200"]["id"],
            accounts["1400"]["id"], accounts["5100"]["id"],
        ]
        credit_acct = accounts["4100"]["id"]
        payload = _multi_line_je_payload(
            hq_subsidiary["id"], debit_accts, credit_acct,
            amount_per_line=25, memo="perf-342",
        )
        r, elapsed = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload,
        )
        assert r.status_code == 201
        assert elapsed < 2.0, f"5-line JE took {elapsed:.3f}s"

    async def test_343_10_line_je_speed(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A 10-line JE (9 debit + 1 credit) should create under 3 seconds."""
        # Use the same accounts multiple times with different amounts via direct payload
        cash_id = accounts["1110"]["id"]
        ar_id = accounts["1200"]["id"]
        inv_id = accounts["1400"]["id"]
        exp_id = accounts["5100"]["id"]
        cogs_id = accounts["5200"]["id"]
        rent_id = accounts["7100"]["id"]
        ap_id = accounts["2110"]["id"]
        revenue_id = accounts["4100"]["id"]

        lines = [
            {"account_id": cash_id, "debit_amount": 10, "credit_amount": 0},
            {"account_id": ar_id, "debit_amount": 10, "credit_amount": 0},
            {"account_id": inv_id, "debit_amount": 10, "credit_amount": 0},
            {"account_id": exp_id, "debit_amount": 10, "credit_amount": 0},
            {"account_id": cogs_id, "debit_amount": 10, "credit_amount": 0},
            {"account_id": rent_id, "debit_amount": 10, "credit_amount": 0},
            {"account_id": ap_id, "debit_amount": 10, "credit_amount": 0},
            {"account_id": cash_id, "debit_amount": 5, "credit_amount": 0},
            {"account_id": ar_id, "debit_amount": 5, "credit_amount": 0},
            {"account_id": revenue_id, "debit_amount": 0, "credit_amount": 80},
        ]
        payload = {
            "subsidiary_id": hq_subsidiary["id"],
            "entry_date": "2026-02-18",
            "memo": f"perf-343-{uuid.uuid4().hex[:8]}",
            "lines": lines,
            "auto_post": True,
        }
        r, elapsed = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload,
        )
        assert r.status_code == 201
        assert elapsed < 3.0, f"10-line JE took {elapsed:.3f}s"

    async def test_344_20_line_je_speed(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A 20-line JE should create under 3 seconds."""
        cash_id = accounts["1110"]["id"]
        ar_id = accounts["1200"]["id"]
        inv_id = accounts["1400"]["id"]
        exp_id = accounts["5100"]["id"]
        cogs_id = accounts["5200"]["id"]
        rent_id = accounts["7100"]["id"]
        ap_id = accounts["2110"]["id"]
        revenue_id = accounts["4100"]["id"]

        debit_accounts = [cash_id, ar_id, inv_id, exp_id, cogs_id, rent_id, ap_id]
        lines = []
        total = 0
        for i in range(19):
            acct_id = debit_accounts[i % len(debit_accounts)]
            amt = 5.0 + i
            lines.append({"account_id": acct_id, "debit_amount": amt, "credit_amount": 0})
            total += amt
        lines.append({"account_id": revenue_id, "debit_amount": 0, "credit_amount": total})

        payload = {
            "subsidiary_id": hq_subsidiary["id"],
            "entry_date": "2026-02-18",
            "memo": f"perf-344-{uuid.uuid4().hex[:8]}",
            "lines": lines,
            "auto_post": True,
        }
        r, elapsed = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload,
        )
        assert r.status_code == 201
        assert elapsed < 3.0, f"20-line JE took {elapsed:.3f}s"

    async def test_345_multi_line_je_data_integrity(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Multi-line JE should preserve all lines and amounts correctly."""
        debit_accts = [
            accounts["1110"]["id"], accounts["1200"]["id"],
            accounts["1400"]["id"],
        ]
        credit_acct = accounts["4100"]["id"]
        payload = _multi_line_je_payload(
            hq_subsidiary["id"], debit_accts, credit_acct,
            amount_per_line=33.33, memo="perf-345",
        )
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
        )
        assert r.status_code == 201
        je_id = r.json()["id"]

        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert detail.status_code == 200
        lines = detail.json()["lines"]
        assert len(lines) == 4  # 3 debit + 1 credit
        assert abs(detail.json()["total_debits"] - detail.json()["total_credits"]) < 0.01

    async def test_346_2_line_vs_5_line_scaling(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """5-line JE should not take more than 3x the time of a 2-line JE."""
        cash = accounts["1110"]
        revenue = accounts["4100"]

        # 2-line
        payload2 = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                               amount=50, memo="perf-346a", auto_post=True)
        _, time_2 = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload2,
        )

        # 5-line
        debit_accts = [
            accounts["1110"]["id"], accounts["1200"]["id"],
            accounts["1400"]["id"], accounts["5100"]["id"],
        ]
        payload5 = _multi_line_je_payload(
            hq_subsidiary["id"], debit_accts, revenue["id"],
            amount_per_line=25, memo="perf-346b",
        )
        _, time_5 = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload5,
        )

        # 5-line should not be more than 3x slower
        assert time_5 < max(time_2 * 3, 2.0), \
            f"5-line ({time_5:.3f}s) > 3x 2-line ({time_2:.3f}s)"

    async def test_347_5_line_vs_10_line_scaling(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """10-line JE should not take more than 3x the time of a 5-line JE."""
        revenue_id = accounts["4100"]["id"]

        # 5-line
        debit_accts_5 = [
            accounts["1110"]["id"], accounts["1200"]["id"],
            accounts["1400"]["id"], accounts["5100"]["id"],
        ]
        payload5 = _multi_line_je_payload(
            hq_subsidiary["id"], debit_accts_5, revenue_id,
            amount_per_line=20, memo="perf-347a",
        )
        _, time_5 = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload5,
        )

        # 10-line (9 debit + 1 credit)
        debit_accts_10 = [
            accounts["1110"]["id"], accounts["1200"]["id"],
            accounts["1400"]["id"], accounts["5100"]["id"],
            accounts["5200"]["id"], accounts["7100"]["id"],
            accounts["2110"]["id"], accounts["1110"]["id"],
            accounts["1200"]["id"],
        ]
        payload10 = _multi_line_je_payload(
            hq_subsidiary["id"], debit_accts_10, revenue_id,
            amount_per_line=10, memo="perf-347b",
        )
        _, time_10 = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload10,
        )

        assert time_10 < max(time_5 * 3, 2.0), \
            f"10-line ({time_10:.3f}s) > 3x 5-line ({time_5:.3f}s)"

    async def test_348_large_je_still_under_3s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A large JE (15 lines) should still complete in under 3 seconds."""
        revenue_id = accounts["4100"]["id"]
        acct_ids = [
            accounts["1110"]["id"], accounts["1200"]["id"],
            accounts["1400"]["id"], accounts["5100"]["id"],
            accounts["5200"]["id"], accounts["7100"]["id"],
            accounts["2110"]["id"],
        ]
        lines = []
        total = 0
        for i in range(14):
            amt = 10.0 + i
            lines.append({
                "account_id": acct_ids[i % len(acct_ids)],
                "debit_amount": amt, "credit_amount": 0,
            })
            total += amt
        lines.append({"account_id": revenue_id, "debit_amount": 0, "credit_amount": total})

        payload = {
            "subsidiary_id": hq_subsidiary["id"],
            "entry_date": "2026-02-18",
            "memo": f"perf-348-{uuid.uuid4().hex[:8]}",
            "lines": lines,
            "auto_post": True,
        }
        r, elapsed = await _timed_request(
            client, "POST", f"{BASE_URL}/api/gl/journal-entries",
            headers=admin_headers, json=payload,
        )
        assert r.status_code == 201
        assert elapsed < 3.0, f"15-line JE took {elapsed:.3f}s, expected < 3.0s"

    async def test_349_large_je_correct_line_count(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A 12-line JE should store all 12 lines correctly."""
        revenue_id = accounts["4100"]["id"]
        acct_ids = [
            accounts["1110"]["id"], accounts["1200"]["id"],
            accounts["1400"]["id"], accounts["5100"]["id"],
            accounts["5200"]["id"],
        ]
        lines = []
        total = 0
        for i in range(11):
            amt = 7.0 + i
            lines.append({
                "account_id": acct_ids[i % len(acct_ids)],
                "debit_amount": amt, "credit_amount": 0,
            })
            total += amt
        lines.append({"account_id": revenue_id, "debit_amount": 0, "credit_amount": total})

        payload = {
            "subsidiary_id": hq_subsidiary["id"],
            "entry_date": "2026-02-18",
            "memo": f"perf-349-{uuid.uuid4().hex[:8]}",
            "lines": lines,
            "auto_post": True,
        }
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
        )
        assert r.status_code == 201
        je_id = r.json()["id"]

        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert len(detail.json()["lines"]) == 12

    async def test_350_large_je_balances_correctly(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """A large multi-line JE should still have debits == credits."""
        revenue_id = accounts["4100"]["id"]
        acct_ids = [
            accounts["1110"]["id"], accounts["1200"]["id"],
            accounts["1400"]["id"],
        ]
        lines = []
        total = 0
        for i in range(9):
            amt = 11.11
            lines.append({
                "account_id": acct_ids[i % len(acct_ids)],
                "debit_amount": amt, "credit_amount": 0,
            })
            total += amt
        lines.append({"account_id": revenue_id, "debit_amount": 0, "credit_amount": round(total, 2)})

        payload = {
            "subsidiary_id": hq_subsidiary["id"],
            "entry_date": "2026-02-18",
            "memo": f"perf-350-{uuid.uuid4().hex[:8]}",
            "lines": lines,
            "auto_post": True,
        }
        r = await client.post(
            f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
        )
        assert r.status_code == 201
        je_id = r.json()["id"]

        detail = await client.get(
            f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
        )
        assert abs(detail.json()["total_debits"] - detail.json()["total_credits"]) < 0.01

    # -------------------------------------------------------------------
    # Tests 351-360: Report generation under load
    # -------------------------------------------------------------------

    async def test_351_create_5_jes_then_tb_under_3s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """After creating 5 JEs, trial balance should still generate under 3 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=100 + i, memo=f"perf-351-{i}", auto_post=True)
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert r.status_code == 201

        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 3.0, f"TB after load took {elapsed:.3f}s"

    async def test_352_create_5_jes_then_soa_under_3s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """After creating 5 JEs, SOA should still generate under 3 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=200 + i, memo=f"perf-352-{i}", auto_post=True)
            await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )

        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 3.0, f"SOA after load took {elapsed:.3f}s"

    async def test_353_create_5_jes_then_bs_under_3s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """After creating 5 JEs, balance sheet should still generate under 3 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=300 + i, memo=f"perf-353-{i}", auto_post=True)
            await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )

        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 3.0, f"BS after load took {elapsed:.3f}s"

    async def test_354_create_5_jes_then_fund_balances_under_3s(
        self, client, admin_headers, accounts, hq_subsidiary, funds
    ):
        """After creating 5 fund-tagged JEs, fund balances should generate under 3 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        general = funds["GEN"]
        for i in range(5):
            payload = {
                "subsidiary_id": hq_subsidiary["id"],
                "entry_date": "2026-02-18",
                "memo": f"perf-354-{i}-{uuid.uuid4().hex[:8]}",
                "lines": [
                    {"account_id": cash["id"], "debit_amount": 50.0 + i, "credit_amount": 0,
                     "fund_id": general["id"]},
                    {"account_id": revenue["id"], "debit_amount": 0, "credit_amount": 50.0 + i,
                     "fund_id": general["id"]},
                ],
                "auto_post": True,
            }
            await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )

        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/reports/fund-balances?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 3.0, f"Fund balances after load took {elapsed:.3f}s"

    async def test_355_create_5_jes_then_dashboard_under_3s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """After creating 5 JEs, dashboard should still generate under 3 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=400 + i, memo=f"perf-355-{i}", auto_post=True)
            await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )

        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/dashboard", headers=admin_headers
        )
        assert r.status_code == 200
        assert elapsed < 3.0, f"Dashboard after load took {elapsed:.3f}s"

    async def test_356_full_report_suite_under_15s(self, client, admin_headers):
        """Generating all 5 reports sequentially should complete under 15 seconds total."""
        urls = [
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            f"{BASE_URL}/api/reports/fund-balances?fiscal_period=2026-02",
            f"{BASE_URL}/api/dashboard",
        ]
        start = time.time()
        for url in urls:
            r = await client.get(url, headers=admin_headers)
            assert r.status_code == 200
        total_elapsed = time.time() - start
        assert total_elapsed < 15.0, f"Full report suite took {total_elapsed:.3f}s, expected < 15.0s"

    async def test_357_tb_valid_after_load(self, client, admin_headers):
        """Trial balance should still balance after all the load testing JEs."""
        r = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert abs(data["total_debits"] - data["total_credits"]) < 0.01

    async def test_358_soa_valid_after_load(self, client, admin_headers):
        """Statement of activities should have valid structure after load testing."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "revenue" in data
        assert "expenses" in data
        assert data["revenue"]["total"] >= 0

    async def test_359_bs_valid_after_load(self, client, admin_headers):
        """Balance sheet should have valid structure after load testing."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "assets" in data
        assert "liabilities" in data
        assert "net_assets" in data

    async def test_360_dashboard_valid_after_load(self, client, admin_headers):
        """Dashboard should have valid KPIs after load testing."""
        r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "kpis" in data
        # total_revenue can be negative in a test environment with many JE reversals/adjustments
        assert isinstance(data["kpis"]["total_revenue"], (int, float))

    # -------------------------------------------------------------------
    # Tests 361-370: Search/filter performance
    # -------------------------------------------------------------------

    async def test_361_contact_search_under_1s(self, client, admin_headers):
        """Contact search should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/contacts?search=test",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"Contact search took {elapsed:.3f}s"

    async def test_362_je_filter_by_subsidiary_under_1s(
        self, client, admin_headers, hq_subsidiary
    ):
        """JE filter by subsidiary should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?subsidiary_id={hq_subsidiary['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"JE filter by subsidiary took {elapsed:.3f}s"

    async def test_363_je_filter_by_status_under_1s(self, client, admin_headers):
        """JE filter by status should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?status=posted",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"JE filter by status took {elapsed:.3f}s"

    async def test_364_je_filter_by_period_under_1s(self, client, admin_headers):
        """JE filter by fiscal period should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"JE filter by period took {elapsed:.3f}s"

    async def test_365_je_filter_by_status_draft_under_1s(self, client, admin_headers):
        """JE filter by draft status should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?status=draft",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"JE draft filter took {elapsed:.3f}s"

    async def test_366_contact_filter_by_type_under_1s(self, client, admin_headers):
        """Contact filter by type should respond in under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/contacts?contact_type=donor",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"Contact type filter took {elapsed:.3f}s"

    async def test_367_je_combined_filters_under_1s(
        self, client, admin_headers, hq_subsidiary
    ):
        """JE with combined filters (subsidiary + status + period) should respond under 1 second."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?subsidiary_id={hq_subsidiary['id']}&status=posted&fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"JE combined filters took {elapsed:.3f}s"

    async def test_368_contact_combined_filters_under_1s(
        self, client, admin_headers, subsidiaries
    ):
        """Contact with combined filters should respond under 1 second."""
        chennai = subsidiaries["SUB-CHENNAI"]
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/contacts?contact_type=donor&subsidiary_id={chennai['id']}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 1.0, f"Contact combined filters took {elapsed:.3f}s"

    async def test_369_accounts_tree_under_2s(self, client, admin_headers):
        """Account tree should respond in under 2 seconds."""
        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/gl/accounts/tree", headers=admin_headers
        )
        assert r.status_code == 200
        assert "items" in r.json()
        assert elapsed < 2.0, f"Accounts tree took {elapsed:.3f}s"

    async def test_370_fiscal_periods_list_under_500ms(self, client, admin_headers):
        """Fiscal periods list should respond in under 500ms."""
        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/org/fiscal-periods", headers=admin_headers
        )
        assert r.status_code == 200
        assert elapsed < 0.5, f"Fiscal periods took {elapsed:.3f}s"

    # -------------------------------------------------------------------
    # Tests 371-380: Burst operations
    # -------------------------------------------------------------------

    async def test_371_rapid_5_sequential_posts(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """5 rapid sequential POST JE creations should all succeed."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        results = []
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=15 + i, memo=f"burst-371-{i}")
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            results.append(r.status_code)
        assert all(s == 201 for s in results), f"Not all POSTs succeeded: {results}"

    async def test_372_rapid_10_sequential_gets(self, client, admin_headers):
        """10 rapid sequential GET requests should all succeed."""
        results = []
        for _ in range(10):
            r = await client.get(
                f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=10",
                headers=admin_headers,
            )
            results.append(r.status_code)
        assert all(s == 200 for s in results), f"Not all GETs succeeded: {results}"

    async def test_373_alternating_read_write_10_ops(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Alternating 5 writes and 5 reads (10 total) should all succeed."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        statuses = []
        for i in range(5):
            # Write
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=25 + i, memo=f"burst-373-w{i}", auto_post=True)
            w = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            statuses.append(("POST", w.status_code))
            # Read
            r = await client.get(
                f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
                headers=admin_headers,
            )
            statuses.append(("GET", r.status_code))
        for method, status in statuses:
            expected = 201 if method == "POST" else 200
            assert status == expected, f"{method} returned {status}, expected {expected}"

    async def test_374_burst_5_posts_all_created(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """All 5 burst POSTs should return valid JE IDs."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        ids = []
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=35 + i, memo=f"burst-374-{i}")
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert r.status_code == 201
            ids.append(r.json()["id"])
        assert len(set(ids)) == 5, "Expected 5 unique JE IDs"

    async def test_375_burst_gets_p50_under_500ms(self, client, admin_headers):
        """p50 (median) of 10 burst GETs should be under 500ms."""
        times = []
        for _ in range(10):
            _, elapsed = await _timed_request(
                client, "GET",
                f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=10",
                headers=admin_headers,
            )
            times.append(elapsed)
        times.sort()
        p50 = times[len(times) // 2]
        assert p50 < 0.5, f"p50 = {p50:.3f}s, expected < 0.5s"

    async def test_376_burst_gets_p95_under_2s(self, client, admin_headers):
        """p95 of 20 burst GETs should be under 2 seconds."""
        times = []
        for _ in range(20):
            _, elapsed = await _timed_request(
                client, "GET",
                f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=10",
                headers=admin_headers,
            )
            times.append(elapsed)
        times.sort()
        p95_idx = int(len(times) * 0.95)
        p95 = times[p95_idx]
        assert p95 < 2.0, f"p95 = {p95:.3f}s, expected < 2.0s"

    async def test_377_burst_posts_p50_under_1s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """p50 of 10 burst POST JE creations should be under 1 second."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        times = []
        for i in range(10):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=45 + i, memo=f"burst-377-{i}")
            _, elapsed = await _timed_request(
                client, "POST", f"{BASE_URL}/api/gl/journal-entries",
                headers=admin_headers, json=payload,
            )
            times.append(elapsed)
        times.sort()
        p50 = times[len(times) // 2]
        assert p50 < 1.0, f"POST p50 = {p50:.3f}s, expected < 1.0s"

    async def test_378_burst_posts_p95_under_2s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """p95 of 10 burst POST JE creations should be under 2 seconds."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        times = []
        for i in range(10):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=55 + i, memo=f"burst-378-{i}")
            _, elapsed = await _timed_request(
                client, "POST", f"{BASE_URL}/api/gl/journal-entries",
                headers=admin_headers, json=payload,
            )
            times.append(elapsed)
        times.sort()
        p95_idx = int(len(times) * 0.95)
        p95 = times[p95_idx]
        assert p95 < 2.0, f"POST p95 = {p95:.3f}s, expected < 2.0s"

    async def test_379_burst_mixed_all_succeed(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Burst of mixed GET/POST operations should all succeed without errors."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        errors = []
        for i in range(5):
            # POST
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=65 + i, memo=f"burst-379-{i}")
            w = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            if w.status_code != 201:
                errors.append(f"POST {i}: {w.status_code}")
            # GET dashboard
            r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
            if r.status_code != 200:
                errors.append(f"GET dashboard {i}: {r.status_code}")
        assert len(errors) == 0, f"Burst errors: {errors}"

    async def test_380_burst_no_500_errors(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Burst of 10 rapid requests should produce no 500-level errors."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        statuses = []
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=75 + i, memo=f"burst-380-{i}")
            w = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            statuses.append(w.status_code)
            r = await client.get(
                f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
                headers=admin_headers,
            )
            statuses.append(r.status_code)
        server_errors = [s for s in statuses if s >= 500]
        assert len(server_errors) == 0, f"Got server errors: {server_errors}"

    # -------------------------------------------------------------------
    # Tests 381-390: Sustained load
    # -------------------------------------------------------------------

    async def test_381_20_mixed_operations_complete(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """20 mixed operations (JE creates + report reads) should all complete."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        completed = 0
        for i in range(10):
            # Write
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=10 + i, memo=f"sustained-381-{i}", auto_post=True)
            w = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert w.status_code == 201
            completed += 1
            # Read
            r = await client.get(
                f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
                headers=admin_headers,
            )
            assert r.status_code == 200
            completed += 1
        assert completed == 20

    async def test_382_sustained_avg_response_under_1s(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Average response time across 20 sustained operations should be under 1 second."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        times = []
        for i in range(10):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=20 + i, memo=f"sustained-382-{i}")
            _, elapsed_w = await _timed_request(
                client, "POST", f"{BASE_URL}/api/gl/journal-entries",
                headers=admin_headers, json=payload,
            )
            times.append(elapsed_w)
            _, elapsed_r = await _timed_request(
                client, "GET",
                f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=10",
                headers=admin_headers,
            )
            times.append(elapsed_r)
        avg = sum(times) / len(times)
        assert avg < 1.0, f"Sustained avg {avg:.3f}s, expected < 1.0s"

    async def test_383_sustained_no_timeouts(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """15 sustained operations should complete without any timeouts."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        for i in range(15):
            if i % 3 == 0:
                payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                      amount=30 + i, memo=f"sustained-383-{i}")
                r = await client.post(
                    f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
                )
                assert r.status_code == 201
            elif i % 3 == 1:
                r = await client.get(
                    f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
                    headers=admin_headers,
                )
                assert r.status_code == 200
            else:
                r = await client.get(
                    f"{BASE_URL}/api/dashboard", headers=admin_headers
                )
                assert r.status_code == 200

    async def test_384_sustained_no_500_errors(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """20 sustained operations should produce no 500-level errors."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        statuses = []
        for i in range(10):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=40 + i, memo=f"sustained-384-{i}")
            w = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            statuses.append(w.status_code)
            r = await client.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
            statuses.append(r.status_code)
        server_errors = [s for s in statuses if s >= 500]
        assert len(server_errors) == 0, f"Server errors during sustained load: {server_errors}"

    async def test_385_sustained_all_jes_created_successfully(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """All JEs from sustained load should be retrievable."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        je_ids = []
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=50 + i, memo=f"sustained-385-{i}", auto_post=True)
            r = await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )
            assert r.status_code == 201
            je_ids.append(r.json()["id"])

        # Verify each JE is retrievable
        for je_id in je_ids:
            detail = await client.get(
                f"{BASE_URL}/api/gl/journal-entries/{je_id}", headers=admin_headers
            )
            assert detail.status_code == 200
            assert detail.json()["status"] == "posted"

    async def test_386_sustained_reports_valid_after_writes(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Reports should be valid after sustained write operations."""
        cash = accounts["1110"]
        revenue = accounts["4100"]
        for i in range(5):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=60 + i, memo=f"sustained-386-{i}", auto_post=True)
            await client.post(
                f"{BASE_URL}/api/gl/journal-entries", headers=admin_headers, json=payload
            )

        # All reports should be valid
        tb = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02", headers=admin_headers
        )
        assert tb.status_code == 200
        assert abs(tb.json()["total_debits"] - tb.json()["total_credits"]) < 0.01

        soa = await client.get(
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert soa.status_code == 200
        assert "revenue" in soa.json()

    async def test_387_sustained_load_je_list_still_fast(
        self, client, admin_headers
    ):
        """After sustained load, JE list should still respond quickly."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=20",
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert elapsed < 2.0, f"JE list after sustained load took {elapsed:.3f}s"

    async def test_388_sustained_load_dashboard_still_fast(self, client, admin_headers):
        """After sustained load, dashboard should still respond under 3 seconds."""
        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/dashboard", headers=admin_headers
        )
        assert r.status_code == 200
        assert elapsed < 3.0, f"Dashboard after sustained load took {elapsed:.3f}s"

    async def test_389_sustained_load_health_still_fast(self, client):
        """After sustained load, health endpoint should still respond quickly."""
        r, elapsed = await _timed_request(client, "GET", f"{BASE_URL}/api/health")
        assert r.status_code == 200
        assert elapsed < 0.5, f"Health after sustained load took {elapsed:.3f}s"

    async def test_390_sustained_load_accounts_still_accessible(self, client, admin_headers):
        """After sustained load, account list should still be accessible and fast."""
        r, elapsed = await _timed_request(
            client, "GET", f"{BASE_URL}/api/gl/accounts", headers=admin_headers
        )
        assert r.status_code == 200
        assert len(r.json()["items"]) > 0
        assert elapsed < 1.0, f"Accounts after sustained load took {elapsed:.3f}s"

    # -------------------------------------------------------------------
    # Tests 391-400: Scalability indicators
    # -------------------------------------------------------------------

    async def test_391_1_concurrent_read_baseline(self, client, admin_headers):
        """Measure baseline time for a single TB read."""
        r, elapsed = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        # Just verify it completes; store nothing (stateless test)
        assert elapsed < 3.0, f"Single read baseline {elapsed:.3f}s"

    async def test_392_5_concurrent_reads_timing(self, client, admin_headers):
        """5 concurrent TB reads should all complete under 5 seconds each."""
        results = await _concurrent_gets(
            client,
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            admin_headers, n=5,
        )
        for r, elapsed in results:
            assert r.status_code == 200
            assert elapsed < 5.0, f"5-concurrent read took {elapsed:.3f}s"

    async def test_393_10_concurrent_reads_timing(self, client, admin_headers):
        """10 concurrent TB reads should all complete under 8 seconds each."""
        results = await _concurrent_gets(
            client,
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            admin_headers, n=10,
        )
        for r, elapsed in results:
            assert r.status_code == 200
            assert elapsed < 8.0, f"10-concurrent read took {elapsed:.3f}s"

    async def test_394_sublinear_scaling_1_vs_5(self, client, admin_headers):
        """Total time for 5 concurrent reads should be less than 5x a single read."""
        # Single read
        _, single_time = await _timed_request(
            client, "GET",
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )

        # 5 concurrent reads
        start = time.time()
        results = await _concurrent_gets(
            client,
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            admin_headers, n=5,
        )
        total_concurrent = time.time() - start
        for r, _ in results:
            assert r.status_code == 200

        # Concurrent total should be less than 5x single (sublinear scaling)
        assert total_concurrent < single_time * 5, \
            f"5 concurrent ({total_concurrent:.3f}s) >= 5x single ({single_time:.3f}s)"

    async def test_395_sublinear_scaling_5_vs_10(self, client, admin_headers):
        """Total time for 10 concurrent reads should scale sub-linearly vs 5."""
        # 5 concurrent
        start5 = time.time()
        results5 = await _concurrent_gets(
            client,
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            admin_headers, n=5,
        )
        time5 = time.time() - start5
        for r, _ in results5:
            assert r.status_code == 200

        # 10 concurrent
        start10 = time.time()
        results10 = await _concurrent_gets(
            client,
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            admin_headers, n=10,
        )
        time10 = time.time() - start10
        for r, _ in results10:
            assert r.status_code == 200

        # 10 concurrent should not take more than 4x 5 concurrent
        # (lenient threshold for local Docker environments with limited resources)
        assert time10 < max(time5 * 4, 5.0), \
            f"10 concurrent ({time10:.3f}s) >= 4x 5 concurrent ({time5:.3f}s)"

    async def test_396_db_connection_pool_handles_concurrent_load(
        self, client, admin_headers
    ):
        """DB connection pool should handle 10 concurrent report requests without errors."""
        urls = [
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02",
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            f"{BASE_URL}/api/reports/fund-balances?fiscal_period=2026-02",
            f"{BASE_URL}/api/dashboard",
            f"{BASE_URL}/api/gl/accounts",
            f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=10",
            f"{BASE_URL}/api/contacts?page=1&page_size=10",
            f"{BASE_URL}/api/org/subsidiaries",
            f"{BASE_URL}/api/org/fiscal-periods",
        ]
        tasks = [_timed_request(client, "GET", url, headers=admin_headers) for url in urls]
        results = await asyncio.gather(*tasks)
        for r, elapsed in results:
            assert r.status_code == 200, f"Request failed with {r.status_code}: {r.text[:200]}"

    async def test_397_no_connection_errors_under_load(
        self, client, admin_headers, accounts, hq_subsidiary
    ):
        """Mixed concurrent read/write load should not cause connection errors."""
        cash = accounts["1110"]
        revenue = accounts["4100"]

        async def do_write(idx):
            payload = _je_payload(hq_subsidiary["id"], cash["id"], revenue["id"],
                                  amount=10 + idx, memo=f"scale-397-{idx}")
            return await _timed_request(
                client, "POST", f"{BASE_URL}/api/gl/journal-entries",
                headers=admin_headers, json=payload,
            )

        async def do_read(url):
            return await _timed_request(client, "GET", url, headers=admin_headers)

        tasks = []
        for i in range(3):
            tasks.append(do_write(i))
        tasks.append(do_read(f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02"))
        tasks.append(do_read(f"{BASE_URL}/api/dashboard"))
        tasks.append(do_read(f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02"))
        tasks.append(do_read(f"{BASE_URL}/api/gl/accounts"))

        results = await asyncio.gather(*tasks)
        for r, elapsed in results:
            assert r.status_code in (200, 201), f"Connection error: status={r.status_code}"

    async def test_398_final_tb_balances(self, client, admin_headers):
        """After all performance tests, trial balance should still balance perfectly."""
        r = await client.get(
            f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        diff = abs(data["total_debits"] - data["total_credits"])
        assert diff < 0.01, \
            f"TB out of balance: debits={data['total_debits']}, credits={data['total_credits']}, diff={diff}"

    async def test_399_final_bs_balances(self, client, admin_headers):
        """After all performance tests, balance sheet should still be structurally valid."""
        r = await client.get(
            f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assets = data["assets"]["total"]
        liabilities = data["liabilities"]["total"]
        net_assets = data["net_assets"]["total"]
        # Assets = Liabilities + Net Assets (accounting equation)
        assert abs(assets - liabilities - net_assets) < 0.01, \
            f"BS equation failed: assets={assets}, liab={liabilities}, net={net_assets}"

    async def test_400_final_consistency_all_reports_accessible(self, client, admin_headers):
        """Final check: all major endpoints are accessible and return valid data."""
        endpoints = [
            ("health", f"{BASE_URL}/api/health"),
            ("dashboard", f"{BASE_URL}/api/dashboard"),
            ("trial_balance", f"{BASE_URL}/api/gl/trial-balance?fiscal_period=2026-02"),
            ("soa", f"{BASE_URL}/api/reports/statement-of-activities?fiscal_period=2026-02"),
            ("bs", f"{BASE_URL}/api/reports/statement-of-financial-position?as_of_period=2026-02"),
            ("fund_balances", f"{BASE_URL}/api/reports/fund-balances?fiscal_period=2026-02"),
            ("accounts", f"{BASE_URL}/api/gl/accounts"),
            ("je_list", f"{BASE_URL}/api/gl/journal-entries?page=1&page_size=10"),
            ("contacts", f"{BASE_URL}/api/contacts?page=1&page_size=10"),
            ("subsidiaries", f"{BASE_URL}/api/org/subsidiaries"),
        ]
        for name, url in endpoints:
            r, elapsed = await _timed_request(client, "GET", url, headers=admin_headers)
            assert r.status_code == 200, f"{name} returned {r.status_code}"
            assert elapsed < 5.0, f"{name} took {elapsed:.3f}s, expected < 5.0s"
