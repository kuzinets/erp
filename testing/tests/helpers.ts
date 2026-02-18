/**
 * Shared test helpers for ERP agent testing.
 */
import { Page, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3001';
const API_URL = 'http://localhost:8001';

export interface TestUser {
  username: string;
  password: string;
  role: string;
  displayName: string;
}

export const USERS: Record<string, TestUser> = {
  admin: { username: 'dmitry', password: 'admin123', role: 'system_admin', displayName: 'Dmitry Kuzinets' },
  controller: { username: 'krishna', password: 'admin123', role: 'controller', displayName: 'Krishna Murthy' },
  seniorAccountant: { username: 'ramantha', password: 'admin123', role: 'senior_accountant', displayName: 'Ramantha Swami' },
  juniorAccountant: { username: 'arjun', password: 'admin123', role: 'junior_accountant', displayName: 'Arjun Sharma' },
  programManager: { username: 'priya', password: 'admin123', role: 'program_manager', displayName: 'Priya Devi' },
  auditor: { username: 'meera', password: 'admin123', role: 'auditor', displayName: 'Meera Patel' },
  viewer: { username: 'sarah', password: 'admin123', role: 'viewer', displayName: 'Sarah Chen' },
};

export async function login(page: Page, user: TestUser): Promise<void> {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[placeholder*="username" i], input[name="username"]', user.username);
  await page.fill('input[type="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/');
  await page.waitForTimeout(1000);
}

export async function apiToken(username: string, password = 'admin123'): Promise<string> {
  const r = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const d = await r.json();
  return d.access_token;
}

export async function apiGet(token: string, path: string): Promise<any> {
  const r = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return r.json();
}

export async function apiPost(token: string, path: string, body: any): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function screenshot(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: `./results/screenshots/${name}.png`, fullPage: true });
}
