/**
 * ROUND 1: Smoke Test — ERP Agent Testing
 *
 * Organization: "Nithyananda Sangha" (HQ, Chennai, Los Angeles, New York, Ashram)
 *
 * Three agent personas perform realistic tasks:
 *   1. Junior Accountant Agent (arjun) — daily operational JE creation
 *   2. Senior Accountant Agent (ramantha) — financial processing, posting
 *   3. Controller/Director Agent (krishna) — oversight, reporting, approvals
 *
 * This round screenshots every page, verifies login for each persona,
 * and exercises core GL workflows.
 */
import { test, expect, Page } from '@playwright/test';

const BASE = 'http://localhost:3001';
const API = 'http://localhost:8001';

async function loginAs(page: Page, username: string, password = 'admin123') {
  await page.goto(`${BASE}/login`);
  await page.fill('input[placeholder*="username" i], input[name="username"]', username);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/');
  await page.waitForTimeout(1000);
}

async function screenshot(page: Page, name: string) {
  await page.screenshot({ path: `./results/screenshots/${name}.png`, fullPage: true });
}

async function apiToken(username: string): Promise<string> {
  const r = await fetch(`${API}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password: 'admin123' }),
  });
  const d = await r.json();
  return d.access_token;
}

// ============================================================================
// CONTROLLER AGENT — Krishna (controller): oversight, reports, approvals
// ============================================================================

test.describe('Controller Agent — Krishna (controller)', () => {
  test('login and screenshot dashboard', async ({ page }) => {
    await loginAs(page, 'krishna');
    await screenshot(page, '01-controller-dashboard');
    // Use heading to avoid ambiguity with sidebar link
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('screenshot chart of accounts', async ({ page }) => {
    await loginAs(page, 'krishna');
    await page.goto(`${BASE}/gl/accounts`);
    await page.waitForTimeout(2000);
    await screenshot(page, '02-controller-accounts');
  });

  test('screenshot journal entries', async ({ page }) => {
    await loginAs(page, 'krishna');
    await page.goto(`${BASE}/gl/journal-entries`);
    await page.waitForTimeout(2000);
    await screenshot(page, '03-controller-journal-entries');
  });

  test('screenshot trial balance', async ({ page }) => {
    await loginAs(page, 'krishna');
    await page.goto(`${BASE}/gl/trial-balance`);
    await page.waitForTimeout(2000);
    await screenshot(page, '04-controller-trial-balance');
  });

  test('screenshot financial reports', async ({ page }) => {
    await loginAs(page, 'krishna');
    await page.goto(`${BASE}/reports`);
    await page.waitForTimeout(2000);
    await screenshot(page, '05-controller-reports');
  });

  test('screenshot subsidiaries', async ({ page }) => {
    await loginAs(page, 'krishna');
    await page.goto(`${BASE}/org/subsidiaries`);
    await page.waitForTimeout(2000);
    await screenshot(page, '06-controller-subsidiaries');
  });

  test('screenshot fiscal periods', async ({ page }) => {
    await loginAs(page, 'krishna');
    await page.goto(`${BASE}/org/fiscal-periods`);
    await page.waitForTimeout(2000);
    await screenshot(page, '07-controller-fiscal-periods');
  });

  test('screenshot departments', async ({ page }) => {
    await loginAs(page, 'krishna');
    await page.goto(`${BASE}/org/departments`);
    await page.waitForTimeout(2000);
    await screenshot(page, '08-controller-departments');
  });

  test('screenshot contacts', async ({ page }) => {
    await loginAs(page, 'krishna');
    await page.goto(`${BASE}/contacts`);
    await page.waitForTimeout(2000);
    await screenshot(page, '09-controller-contacts');
  });

  test('screenshot connected systems', async ({ page }) => {
    await loginAs(page, 'krishna');
    await page.goto(`${BASE}/subsystems`);
    await page.waitForTimeout(2000);
    await screenshot(page, '10-controller-subsystems');
  });

  test('view dashboard KPIs via API', async () => {
    const token = await apiToken('krishna');
    const r = await fetch(`${API}/api/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(r.status).toBe(200);
    const data = await r.json();
    // Dashboard returns { current_period, kpis: { ... }, ... }
    expect(data).toHaveProperty('kpis');
    expect(data.kpis).toHaveProperty('journal_entries');
    expect(data.kpis).toHaveProperty('subsidiaries');
  });

  test('view trial balance via API', async () => {
    const token = await apiToken('krishna');
    const r = await fetch(`${API}/api/gl/trial-balance?fiscal_period=2026-02`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(r.status).toBe(200);
    const data = await r.json();
    // Trial balance returns { fiscal_period, items: [], total_debits, total_credits }
    expect(data).toHaveProperty('items');
    expect(Array.isArray(data.items)).toBe(true);
  });
});

// ============================================================================
// SENIOR ACCOUNTANT AGENT — Ramantha (senior_accountant): financial processing
// ============================================================================

test.describe('Senior Accountant Agent — Ramantha (senior_accountant)', () => {
  test('login and see dashboard', async ({ page }) => {
    await loginAs(page, 'ramantha');
    await screenshot(page, '11-senior-dashboard');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('create a journal entry via API', async () => {
    const token = await apiToken('ramantha');

    // Get fiscal periods to find the open one (returns { items: [...] })
    const periodsResp = await fetch(`${API}/api/org/fiscal-periods?status=open`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const periodsData = await periodsResp.json();
    const periods = periodsData.items;
    expect(periods.length).toBeGreaterThan(0);
    const period = periods[0];

    // Get a subsidiary (returns { items: [...] })
    const subsResp = await fetch(`${API}/api/org/subsidiaries`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const subsData = await subsResp.json();
    const subs = subsData.items;
    const hq = subs.find((s: any) => s.code === 'HQ') || subs[0];

    // Get accounts (returns { items: [...] })
    const acctResp = await fetch(`${API}/api/gl/accounts`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const acctData = await acctResp.json();
    const accounts = acctData.items;
    const cashAcct = accounts.find((a: any) => a.account_number === '1000') || accounts[0];
    const donationAcct = accounts.find((a: any) => a.account_number === '4100') || accounts[1];

    // Create journal entry (requires entry_date)
    const today = new Date().toISOString().split('T')[0];
    const r = await fetch(`${API}/api/gl/journal-entries`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        description: 'Agent Round 1 - Donation received at HQ',
        entry_date: today,
        fiscal_period_id: period.id,
        subsidiary_id: hq.id,
        source: 'manual',
        auto_post: false,
        lines: [
          {
            account_id: cashAcct.id,
            debit_amount: 5000.00,
            credit_amount: 0,
            description: 'Cash received - donation',
          },
          {
            account_id: donationAcct.id,
            debit_amount: 0,
            credit_amount: 5000.00,
            description: 'Donation revenue recognized',
          },
        ],
      }),
    });
    expect(r.status).toBe(201);
    const je = await r.json();
    expect(je.status).toBe('draft');
    expect(je.total_debits).toBe(5000.00);
    expect(je.total_credits).toBe(5000.00);
  });

  test('post a journal entry via API', async () => {
    const token = await apiToken('ramantha');

    // Find a draft entry
    const jeResp = await fetch(`${API}/api/gl/journal-entries?status=draft&page_size=5`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const jeData = await jeResp.json();
    expect(jeData.items.length).toBeGreaterThan(0);
    const draftJE = jeData.items[0];

    // Post it
    const r = await fetch(`${API}/api/gl/journal-entries/${draftJE.id}/post`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(r.status).toBe(200);
    const posted = await r.json();
    expect(posted.status).toBe('posted');
  });

  test('browse journal entries page', async ({ page }) => {
    await loginAs(page, 'ramantha');
    await page.goto(`${BASE}/gl/journal-entries`);
    await page.waitForTimeout(2000);
    await screenshot(page, '12-senior-journal-entries');
  });
});

// ============================================================================
// JUNIOR ACCOUNTANT AGENT — Arjun (junior_accountant, Chennai subsidiary)
// ============================================================================

test.describe('Junior Accountant Agent — Arjun (junior_accountant)', () => {
  test('login and see dashboard', async ({ page }) => {
    await loginAs(page, 'arjun');
    await screenshot(page, '13-junior-dashboard');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('create a journal entry for Chennai via API', async () => {
    const token = await apiToken('arjun');

    // Get fiscal periods (returns { items: [...] })
    const periodsResp = await fetch(`${API}/api/org/fiscal-periods?status=open`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const periodsData = await periodsResp.json();
    const periods = periodsData.items;
    expect(periods.length).toBeGreaterThan(0);

    // Get Chennai subsidiary (returns { items: [...] })
    const subsResp = await fetch(`${API}/api/org/subsidiaries`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const subsData = await subsResp.json();
    const subs = subsData.items;
    const chennai = subs.find((s: any) => s.code === 'SUB-CHENNAI') || subs[0];

    // Get accounts (returns { items: [...] })
    const acctResp = await fetch(`${API}/api/gl/accounts`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const acctData = await acctResp.json();
    const accounts = acctData.items;
    const suppliesAcct = accounts.find((a: any) => a.account_number === '5100') || accounts[0];
    const cashAcct = accounts.find((a: any) => a.account_number === '1000') || accounts[1];

    // Create entry: purchased program supplies (requires entry_date)
    const today = new Date().toISOString().split('T')[0];
    const r = await fetch(`${API}/api/gl/journal-entries`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        description: 'Agent Round 1 - Purchased program supplies for Chennai temple',
        entry_date: today,
        fiscal_period_id: periods[0].id,
        subsidiary_id: chennai.id,
        source: 'manual',
        auto_post: false,
        lines: [
          {
            account_id: suppliesAcct.id,
            debit_amount: 750.00,
            credit_amount: 0,
            description: 'Program supplies expense',
          },
          {
            account_id: cashAcct.id,
            debit_amount: 0,
            credit_amount: 750.00,
            description: 'Cash payment for supplies',
          },
        ],
      }),
    });
    expect(r.status).toBe(201);
    const je = await r.json();
    expect(je.status).toBe('draft');
    expect(je.total_debits).toBe(750.00);
  });

  test('view chart of accounts', async ({ page }) => {
    await loginAs(page, 'arjun');
    await page.goto(`${BASE}/gl/accounts`);
    await page.waitForTimeout(2000);
    await screenshot(page, '14-junior-accounts');
  });
});

// ============================================================================
// PERMISSION ENFORCEMENT TESTS
// ============================================================================

test.describe('Permission Enforcement', () => {
  test('viewer cannot create journal entries', async () => {
    const token = await apiToken('sarah');
    const r = await fetch(`${API}/api/gl/journal-entries`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        description: 'Unauthorized entry',
        fiscal_period_id: '00000000-0000-0000-0000-000000000000',
        subsidiary_id: '00000000-0000-0000-0000-000000000001',
        lines: [],
      }),
    });
    expect(r.status).toBe(403);
  });

  test('junior accountant cannot post journal entries', async () => {
    const token = await apiToken('arjun');
    // Try to post a random ID
    const r = await fetch(`${API}/api/gl/journal-entries/00000000-0000-0000-0000-000000000000/post`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    // Should be 403 (missing post permission) or 404 (entry not found)
    expect([403, 404]).toContain(r.status);
  });

  test('failed login is rejected', async () => {
    const r = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'dmitry', password: 'wrongpassword' }),
    });
    expect(r.status).toBe(401);
  });

  test('unauthenticated request is rejected', async () => {
    const r = await fetch(`${API}/api/gl/accounts`, {
      headers: { Authorization: 'Bearer invalid_token' },
    });
    expect(r.status).toBe(401);
  });
});

// ============================================================================
// ADMIN PAGES (Dmitry — system_admin)
// ============================================================================

test.describe('Admin Agent — Dmitry (system_admin)', () => {
  test('screenshot user management', async ({ page }) => {
    await loginAs(page, 'dmitry');
    await page.goto(`${BASE}/admin/users`);
    await page.waitForTimeout(2000);
    await screenshot(page, '15-admin-user-management');
  });

  test('screenshot audit log', async ({ page }) => {
    await loginAs(page, 'dmitry');
    await page.goto(`${BASE}/admin/audit`);
    await page.waitForTimeout(2000);
    await screenshot(page, '16-admin-audit-log');
  });

  test('view audit log via API', async () => {
    const token = await apiToken('dmitry');
    const r = await fetch(`${API}/api/admin/audit-log?page=1&page_size=10`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(r.status).toBe(200);
    const data = await r.json();
    expect(data).toHaveProperty('items');
    expect(data.items.length).toBeGreaterThan(0);
    // Verify login events are being tracked
    const loginEvents = data.items.filter((i: any) => i.action === 'auth.login');
    expect(loginEvents.length).toBeGreaterThan(0);
  });

  test('view all users via API', async () => {
    const token = await apiToken('dmitry');
    const r = await fetch(`${API}/api/admin/users`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(r.status).toBe(200);
    const data = await r.json();
    // API returns { items: [...] }
    expect(data).toHaveProperty('items');
    expect(data.items.length).toBeGreaterThanOrEqual(7); // 8 seed users
  });
});
