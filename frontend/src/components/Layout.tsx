import { useState } from 'react';
import { Link, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  LayoutDashboard,
  BookOpen,
  FileText,
  Scale,
  BarChart3,
  Building2,
  Users,
  Plug,
  Settings,
  LogOut,
  ChevronDown,
  ChevronRight,
  Menu,
  X,
  Shield,
  ClipboardList,
} from 'lucide-react';

interface NavChild {
  label: string;
  path: string;
  permission?: string;
}

interface NavItem {
  label: string;
  path?: string;
  icon: React.ReactNode;
  children?: NavChild[];
  permission?: string;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/', icon: <LayoutDashboard size={20} />, permission: 'reports.dashboard.view' },
  {
    label: 'General Ledger',
    icon: <BookOpen size={20} />,
    children: [
      { label: 'Chart of Accounts', path: '/gl/accounts', permission: 'gl.accounts.view' },
      { label: 'Journal Entries', path: '/gl/journal-entries', permission: 'gl.journal_entries.view' },
      { label: 'Trial Balance', path: '/gl/trial-balance', permission: 'gl.trial_balance.view' },
    ],
  },
  { label: 'Financial Reports', path: '/reports', icon: <BarChart3 size={20} />, permission: 'reports.financial.view' },
  {
    label: 'Organization',
    icon: <Building2 size={20} />,
    children: [
      { label: 'Subsidiaries', path: '/org/subsidiaries', permission: 'org.subsidiaries.view' },
      { label: 'Fiscal Periods', path: '/org/fiscal-periods', permission: 'org.fiscal_periods.view' },
      { label: 'Departments', path: '/org/departments', permission: 'org.departments.view' },
    ],
  },
  { label: 'Contacts', path: '/contacts', icon: <Users size={20} />, permission: 'contacts.view' },
  { label: 'Connected Systems', path: '/subsystems', icon: <Plug size={20} />, permission: 'subsystems.view' },
  {
    label: 'Administration',
    icon: <Shield size={20} />,
    children: [
      { label: 'User Management', path: '/admin/users', permission: 'admin.users.view' },
      { label: 'Audit Log', path: '/admin/audit', permission: 'admin.audit_log.view' },
    ],
  },
  { label: 'Settings', path: '/settings', icon: <Settings size={20} />, permission: 'admin.users.view' },
];

export default function Layout() {
  const { user, logout, can } = useAuth();
  const location = useLocation();
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(['General Ledger', 'Organization'])
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleGroup = (label: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  const isActive = (path: string) => location.pathname === path;

  const isGroupActive = (item: NavItem) =>
    item.children?.some((c) => location.pathname === c.path) ?? false;

  const roleBadge = (role: string) => {
    const colors: Record<string, string> = {
      system_admin: 'bg-red-900/40 text-red-400',
      controller: 'bg-purple-900/40 text-purple-400',
      senior_accountant: 'bg-primary-600/30 text-primary-300',
      junior_accountant: 'bg-blue-900/40 text-blue-400',
      program_manager: 'bg-teal-900/40 text-teal-400',
      auditor: 'bg-yellow-900/40 text-yellow-400',
      viewer: 'bg-gray-700/60 text-gray-400',
    };
    return colors[role] || colors.viewer;
  };

  const roleLabel = (role: string) => {
    const labels: Record<string, string> = {
      system_admin: 'System Admin',
      controller: 'Controller',
      senior_accountant: 'Sr. Accountant',
      junior_accountant: 'Jr. Accountant',
      program_manager: 'Program Mgr',
      auditor: 'Auditor',
      viewer: 'Viewer',
    };
    return labels[role] || role.replace(/_/g, ' ');
  };

  /** Check if a nav item (or any of its children) should be visible */
  const isVisible = (item: NavItem): boolean => {
    if (item.children) {
      return item.children.some((child) => !child.permission || can(child.permission));
    }
    return !item.permission || can(item.permission);
  };

  const sidebar = (
    <div className="flex flex-col h-full bg-kailasa-sidebar">
      {/* Header */}
      <div className="px-4 py-5 border-b border-kailasa-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary-600/30 flex items-center justify-center">
            <Scale size={20} className="text-primary-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-kailasa-text leading-tight">KAILASA ERP</h1>
            <p className="text-xs text-kailasa-muted">Financial Management</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {navItems.filter(isVisible).map((item) => {
          if (item.children) {
            const visibleChildren = item.children.filter(
              (child) => !child.permission || can(child.permission)
            );
            if (visibleChildren.length === 0) return null;

            const expanded = expandedGroups.has(item.label);
            const groupActive = isGroupActive(item);
            return (
              <div key={item.label}>
                <button
                  onClick={() => toggleGroup(item.label)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    groupActive
                      ? 'text-primary-400 bg-kailasa-surfaceLight'
                      : 'text-kailasa-textSecondary hover:text-kailasa-text hover:bg-kailasa-surface'
                  }`}
                >
                  {item.icon}
                  <span className="flex-1 text-left font-medium">{item.label}</span>
                  {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>
                {expanded && (
                  <div className="ml-8 mt-0.5 space-y-0.5">
                    {visibleChildren.map((child) => (
                      <Link
                        key={child.path}
                        to={child.path}
                        onClick={() => setSidebarOpen(false)}
                        className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                          isActive(child.path)
                            ? 'text-primary-400 bg-primary-600/15 font-medium'
                            : 'text-kailasa-muted hover:text-kailasa-text hover:bg-kailasa-surface'
                        }`}
                      >
                        {child.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          }

          return (
            <Link
              key={item.path}
              to={item.path!}
              onClick={() => setSidebarOpen(false)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive(item.path!)
                  ? 'text-primary-400 bg-primary-600/15 font-medium'
                  : 'text-kailasa-textSecondary hover:text-kailasa-text hover:bg-kailasa-surface'
              }`}
            >
              {item.icon}
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* User / Logout */}
      <div className="border-t border-kailasa-border p-3">
        {user && (
          <div className="flex items-center gap-3 px-2 mb-3">
            <div className="w-8 h-8 rounded-full bg-primary-600/30 flex items-center justify-center text-sm font-bold text-primary-300">
              {user.display_name?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-kailasa-text truncate">{user.display_name}</p>
              <span
                className={`inline-block mt-0.5 px-2 py-0.5 rounded-full text-[10px] font-semibold ${roleBadge(user.role)}`}
              >
                {roleLabel(user.role)}
              </span>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-kailasa-muted hover:text-red-400 hover:bg-red-900/20 transition-colors"
        >
          <LogOut size={18} />
          <span>Sign out</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-kailasa-bg">
      {/* Mobile sidebar toggle */}
      <button
        className="lg:hidden fixed top-3 left-3 z-50 p-2 rounded-lg bg-kailasa-surface text-kailasa-text border border-kailasa-border"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 w-64 transform transition-transform lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebar}
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 overflow-auto">
        <div className="p-4 lg:p-6 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
