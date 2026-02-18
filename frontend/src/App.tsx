import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import PermissionGuard from './components/PermissionGuard';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ChartOfAccounts from './pages/ChartOfAccounts';
import JournalEntries from './pages/JournalEntries';
import TrialBalance from './pages/TrialBalance';
import FinancialStatements from './pages/FinancialStatements';
import Subsidiaries from './pages/Subsidiaries';
import FiscalPeriods from './pages/FiscalPeriods';
import Departments from './pages/Departments';
import Contacts from './pages/Contacts';
import Subsystems from './pages/Subsystems';
import Settings from './pages/Settings';
import UserManagement from './pages/UserManagement';
import AuditLog from './pages/AuditLog';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-kailasa-bg">
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Protected routes with sidebar layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/gl/accounts" element={<ChartOfAccounts />} />
        <Route path="/gl/journal-entries" element={<JournalEntries />} />
        <Route path="/gl/trial-balance" element={<TrialBalance />} />
        <Route path="/reports" element={<FinancialStatements />} />
        <Route path="/org/subsidiaries" element={<Subsidiaries />} />
        <Route path="/org/fiscal-periods" element={<FiscalPeriods />} />
        <Route path="/org/departments" element={<Departments />} />
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/subsystems" element={<Subsystems />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/admin/users" element={<PermissionGuard permission="admin.users.view"><UserManagement /></PermissionGuard>} />
        <Route path="/admin/audit" element={<PermissionGuard permission="admin.audit_log.view"><AuditLog /></PermissionGuard>} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
