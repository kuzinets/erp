import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const login = (username: string, password: string) =>
  api.post('/auth/login', { username, password });

export const getMe = () => api.get('/auth/me');

export const refreshToken = () => api.post('/auth/refresh');

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const getDashboard = () => api.get('/dashboard');

// ── General Ledger (GL) ───────────────────────────────────────────────────────

// Chart of Accounts
export const getAccounts = (params?: Record<string, any>) =>
  api.get('/gl/accounts', { params });

export const getAccountsTree = (params?: Record<string, any>) =>
  api.get('/gl/accounts/tree', { params });

export const getAccount = (id: string | number) =>
  api.get(`/gl/accounts/${id}`);

export const createAccount = (data: any) =>
  api.post('/gl/accounts', data);

export const updateAccount = (id: string | number, data: any) =>
  api.put(`/gl/accounts/${id}`, data);

// Journal Entries
export const getJournalEntries = (params?: Record<string, any>) =>
  api.get('/gl/journal-entries', { params });

export const getJournalEntry = (id: string | number) =>
  api.get(`/gl/journal-entries/${id}`);

export const createJournalEntry = (data: any) =>
  api.post('/gl/journal-entries', data);

export const postJournalEntry = (id: string | number) =>
  api.post(`/gl/journal-entries/${id}/post`);

export const reverseJournalEntry = (id: string | number) =>
  api.post(`/gl/journal-entries/${id}/reverse`);

// Trial Balance
export const getTrialBalance = (params?: Record<string, any>) =>
  api.get('/gl/trial-balance', { params });

// Funds
export const getFunds = (params?: Record<string, any>) =>
  api.get('/gl/funds', { params });

// ── Financial Reports ─────────────────────────────────────────────────────────
export const getStatementOfActivities = (params?: Record<string, any>) =>
  api.get('/reports/statement-of-activities', { params });

export const getStatementOfFinancialPosition = (params?: Record<string, any>) =>
  api.get('/reports/statement-of-financial-position', { params });

export const getFundBalances = (params?: Record<string, any>) =>
  api.get('/reports/fund-balances', { params });

// ── Organization ──────────────────────────────────────────────────────────────

// Subsidiaries
export const getSubsidiaries = (params?: Record<string, any>) =>
  api.get('/org/subsidiaries', { params });

export const getSubsidiary = (id: string | number) =>
  api.get(`/org/subsidiaries/${id}`);

export const createSubsidiary = (data: any) =>
  api.post('/org/subsidiaries', data);

export const updateSubsidiary = (id: string | number, data: any) =>
  api.put(`/org/subsidiaries/${id}`, data);

// Fiscal Years
export const getFiscalYears = (params?: Record<string, any>) =>
  api.get('/org/fiscal-years', { params });

export const getFiscalYear = (id: string | number) =>
  api.get(`/org/fiscal-years/${id}`);

export const createFiscalYear = (data: any) =>
  api.post('/org/fiscal-years', data);

// Fiscal Periods
export const getFiscalPeriods = (params?: Record<string, any>) =>
  api.get('/org/fiscal-periods', { params });

export const getFiscalPeriod = (id: string | number) =>
  api.get(`/org/fiscal-periods/${id}`);

export const closePeriod = (id: string | number) =>
  api.post(`/org/fiscal-periods/${id}/close`);

export const reopenPeriod = (id: string | number) =>
  api.post(`/org/fiscal-periods/${id}/reopen`);

// Departments
export const getDepartments = (params?: Record<string, any>) =>
  api.get('/org/departments', { params });

export const getDepartment = (id: string | number) =>
  api.get(`/org/departments/${id}`);

export const createDepartment = (data: any) =>
  api.post('/org/departments', data);

export const updateDepartment = (id: string | number, data: any) =>
  api.put(`/org/departments/${id}`, data);

// ── Contacts ──────────────────────────────────────────────────────────────────
export const getContacts = (params?: Record<string, any>) =>
  api.get('/contacts', { params });

export const getContact = (id: string | number) =>
  api.get(`/contacts/${id}`);

export const createContact = (data: any) =>
  api.post('/contacts', data);

export const updateContact = (id: string | number, data: any) =>
  api.put(`/contacts/${id}`, data);

// ── Subsystems ────────────────────────────────────────────────────────────────
export const getSubsystems = (params?: Record<string, any>) =>
  api.get('/subsystems', { params });

export const getSubsystem = (id: string | number) =>
  api.get(`/subsystems/${id}`);

export const createSubsystemConfig = (data: any) =>
  api.post('/subsystems/', data);

export const updateSubsystemConfig = (id: string | number, data: any) =>
  api.put(`/subsystems/${id}`, data);

export const getSubsystemMappings = (configId: string | number) =>
  api.get(`/subsystems/${configId}/mappings`);

export const createSubsystemMapping = (configId: string | number, data: any) =>
  api.post(`/subsystems/${configId}/mappings`, data);

export const triggerSync = (id: string | number, fiscalPeriod: string) =>
  api.post(`/subsystems/${id}/sync`, null, { params: { fiscal_period: fiscalPeriod } });

export const getSyncLogs = (configId: string | number, params?: Record<string, any>) =>
  api.get(`/subsystems/${configId}/sync-logs`, { params });

// ── Admin ───────────────────────────────────────────────────────────────────
export const getUsers = (params?: Record<string, any>) =>
  api.get('/admin/users', { params });

export const getUser = (id: string) =>
  api.get(`/admin/users/${id}`);

export const createUser = (data: any) =>
  api.post('/admin/users', data);

export const updateUser = (id: string, data: any) =>
  api.put(`/admin/users/${id}`, data);

export const setPermissionOverride = (userId: string, data: any) =>
  api.post(`/admin/users/${userId}/permissions`, data);

export const deletePermissionOverride = (userId: string, permission: string) =>
  api.delete(`/admin/users/${userId}/permissions/${encodeURIComponent(permission)}`);

export const getRoles = () =>
  api.get('/admin/roles');

export const getAuditLog = (params?: Record<string, any>) =>
  api.get('/admin/audit-log', { params });

export default api;
