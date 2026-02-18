import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getUsers, createUser, updateUser, getRoles } from '../services/api';
import { UserPlus, Edit2, Shield, ChevronDown, ChevronUp, Check, X } from 'lucide-react';

interface UserRow {
  id: string;
  username: string;
  display_name: string;
  email: string | null;
  role: string;
  subsidiary_id: string | null;
  subsidiary_name: string | null;
  is_active: boolean;
  created_at: string;
}

interface RoleInfo {
  code: string;
  permissions: string[];
  scope: string;
}

const ROLE_LABELS: Record<string, string> = {
  system_admin: 'System Admin',
  controller: 'Controller (CFO)',
  senior_accountant: 'Senior Accountant',
  junior_accountant: 'Junior Accountant',
  program_manager: 'Program Manager',
  auditor: 'Auditor',
  viewer: 'Viewer',
};

const ROLE_COLORS: Record<string, string> = {
  system_admin: 'bg-red-900/30 text-red-400 border-red-800/50',
  controller: 'bg-purple-900/30 text-purple-400 border-purple-800/50',
  senior_accountant: 'bg-blue-900/30 text-blue-400 border-blue-800/50',
  junior_accountant: 'bg-cyan-900/30 text-cyan-400 border-cyan-800/50',
  program_manager: 'bg-teal-900/30 text-teal-400 border-teal-800/50',
  auditor: 'bg-yellow-900/30 text-yellow-400 border-yellow-800/50',
  viewer: 'bg-gray-700/30 text-gray-400 border-gray-600/50',
};

export default function UserManagement() {
  const { can } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [expandedRole, setExpandedRole] = useState<string | null>(null);

  // Create form state
  const [form, setForm] = useState({
    username: '', password: '', display_name: '', email: '', role: 'viewer', subsidiary_id: '',
  });
  const [editForm, setEditForm] = useState({
    display_name: '', email: '', role: '', is_active: true,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [usersRes, rolesRes] = await Promise.all([getUsers(), getRoles()]);
      setUsers(usersRes.data.items || []);
      setRoles(rolesRes.data.roles || []);
    } catch (err) {
      console.error('Failed to load users', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createUser({
        ...form,
        subsidiary_id: form.subsidiary_id || null,
      });
      setShowCreate(false);
      setForm({ username: '', password: '', display_name: '', email: '', role: 'viewer', subsidiary_id: '' });
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleUpdate = async (id: string) => {
    try {
      await updateUser(id, editForm);
      setEditingId(null);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update user');
    }
  };

  const startEdit = (user: UserRow) => {
    setEditingId(user.id);
    setEditForm({
      display_name: user.display_name,
      email: user.email || '',
      role: user.role,
      is_active: user.is_active,
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-kailasa-text">User Management</h1>
          <p className="text-sm text-kailasa-muted mt-1">Manage system users and their roles</p>
        </div>
        {can('admin.users.create') && (
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <UserPlus size={16} />
            New User
          </button>
        )}
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-kailasa-surface border border-kailasa-border rounded-xl p-6">
          <h2 className="text-lg font-semibold text-kailasa-text mb-4">Create New User</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              placeholder="Username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
              className="bg-kailasa-bg border border-kailasa-border rounded-lg px-3 py-2 text-sm text-kailasa-text placeholder-kailasa-muted focus:outline-none focus:border-primary-500"
            />
            <input
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              className="bg-kailasa-bg border border-kailasa-border rounded-lg px-3 py-2 text-sm text-kailasa-text placeholder-kailasa-muted focus:outline-none focus:border-primary-500"
            />
            <input
              placeholder="Display Name"
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              required
              className="bg-kailasa-bg border border-kailasa-border rounded-lg px-3 py-2 text-sm text-kailasa-text placeholder-kailasa-muted focus:outline-none focus:border-primary-500"
            />
            <input
              type="email"
              placeholder="Email (optional)"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="bg-kailasa-bg border border-kailasa-border rounded-lg px-3 py-2 text-sm text-kailasa-text placeholder-kailasa-muted focus:outline-none focus:border-primary-500"
            />
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="bg-kailasa-bg border border-kailasa-border rounded-lg px-3 py-2 text-sm text-kailasa-text focus:outline-none focus:border-primary-500"
            >
              {Object.entries(ROLE_LABELS).map(([code, label]) => (
                <option key={code} value={code}>{label}</option>
              ))}
            </select>
            <div className="flex items-center gap-3">
              <button
                type="submit"
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Create User
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 bg-kailasa-bg hover:bg-kailasa-surfaceLight text-kailasa-muted rounded-lg text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-kailasa-surface border border-kailasa-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-kailasa-border bg-kailasa-bg/50">
              <th className="text-left px-4 py-3 text-kailasa-muted font-medium">User</th>
              <th className="text-left px-4 py-3 text-kailasa-muted font-medium">Role</th>
              <th className="text-left px-4 py-3 text-kailasa-muted font-medium">Subsidiary</th>
              <th className="text-left px-4 py-3 text-kailasa-muted font-medium">Status</th>
              <th className="text-right px-4 py-3 text-kailasa-muted font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-kailasa-border/50 hover:bg-kailasa-bg/30">
                <td className="px-4 py-3">
                  {editingId === u.id ? (
                    <input
                      value={editForm.display_name}
                      onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                      className="bg-kailasa-bg border border-kailasa-border rounded px-2 py-1 text-sm text-kailasa-text w-full"
                    />
                  ) : (
                    <div>
                      <p className="text-kailasa-text font-medium">{u.display_name}</p>
                      <p className="text-kailasa-muted text-xs">{u.username} {u.email ? `| ${u.email}` : ''}</p>
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  {editingId === u.id ? (
                    <select
                      value={editForm.role}
                      onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                      className="bg-kailasa-bg border border-kailasa-border rounded px-2 py-1 text-sm text-kailasa-text"
                    >
                      {Object.entries(ROLE_LABELS).map(([code, label]) => (
                        <option key={code} value={code}>{label}</option>
                      ))}
                    </select>
                  ) : (
                    <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold border ${ROLE_COLORS[u.role] || ROLE_COLORS.viewer}`}>
                      {ROLE_LABELS[u.role] || u.role}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-kailasa-textSecondary">
                  {u.subsidiary_name || (u.subsidiary_id ? u.subsidiary_id.slice(0, 8) : 'Global')}
                </td>
                <td className="px-4 py-3">
                  {editingId === u.id ? (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editForm.is_active}
                        onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                        className="rounded"
                      />
                      <span className="text-xs text-kailasa-muted">Active</span>
                    </label>
                  ) : (
                    <span className={`inline-block w-2 h-2 rounded-full ${u.is_active ? 'bg-green-500' : 'bg-red-500'}`} />
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {editingId === u.id ? (
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleUpdate(u.id)}
                        className="p-1.5 rounded-lg bg-green-900/30 text-green-400 hover:bg-green-900/50 transition-colors"
                      >
                        <Check size={14} />
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="p-1.5 rounded-lg bg-red-900/30 text-red-400 hover:bg-red-900/50 transition-colors"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ) : (
                    can('admin.users.update') && (
                      <button
                        onClick={() => startEdit(u)}
                        className="p-1.5 rounded-lg text-kailasa-muted hover:text-primary-400 hover:bg-kailasa-bg transition-colors"
                      >
                        <Edit2 size={14} />
                      </button>
                    )
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Role Summary */}
      <div className="bg-kailasa-surface border border-kailasa-border rounded-xl p-6">
        <h2 className="text-lg font-semibold text-kailasa-text mb-4 flex items-center gap-2">
          <Shield size={18} className="text-primary-400" />
          Role Permissions Reference
        </h2>
        <div className="space-y-2">
          {roles.map((role) => (
            <div key={role.code} className="border border-kailasa-border/50 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedRole(expandedRole === role.code ? null : role.code)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-kailasa-bg/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${ROLE_COLORS[role.code] || ROLE_COLORS.viewer}`}>
                    {ROLE_LABELS[role.code] || role.code}
                  </span>
                  <span className="text-xs text-kailasa-muted">
                    {role.permissions.length} permissions | Scope: {role.scope}
                  </span>
                </div>
                {expandedRole === role.code ? <ChevronUp size={16} className="text-kailasa-muted" /> : <ChevronDown size={16} className="text-kailasa-muted" />}
              </button>
              {expandedRole === role.code && (
                <div className="px-4 pb-3 grid grid-cols-2 md:grid-cols-3 gap-1">
                  {role.permissions.map((perm) => (
                    <span key={perm} className="text-xs text-kailasa-muted font-mono bg-kailasa-bg/50 px-2 py-1 rounded">
                      {perm}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
