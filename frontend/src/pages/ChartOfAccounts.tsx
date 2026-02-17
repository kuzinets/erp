import { useState, useEffect } from 'react';
import { getAccountsTree, getAccounts, createAccount, updateAccount } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import {
  ChevronRight,
  ChevronDown,
  Plus,
  X,
  Search,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';

interface Account {
  id: string;
  account_number: string;
  name: string;
  account_type: string;
  normal_balance: string;
  is_active: boolean;
  description?: string;
  children?: Account[];
}

function AccountRow({
  account,
  depth = 0,
  expanded,
  toggleExpand,
  onEdit,
}: {
  account: Account;
  depth?: number;
  expanded: Set<string>;
  toggleExpand: (id: string) => void;
  onEdit: (a: Account) => void;
}) {
  const hasChildren = account.children && account.children.length > 0;
  const isExpanded = expanded.has(account.id);

  const typeColors: Record<string, string> = {
    asset: 'text-blue-400',
    liability: 'text-red-400',
    equity: 'text-purple-400',
    revenue: 'text-green-400',
    expense: 'text-orange-400',
  };

  return (
    <>
      <tr className="hover:bg-kailasa-surfaceLight transition-colors group">
        <td className="py-2.5 px-3">
          <div className="flex items-center" style={{ paddingLeft: `${depth * 24}px` }}>
            {hasChildren ? (
              <button
                onClick={() => toggleExpand(account.id)}
                className="w-5 h-5 flex items-center justify-center text-kailasa-muted hover:text-kailasa-text mr-1.5"
              >
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </button>
            ) : (
              <span className="w-5 mr-1.5" />
            )}
            <span className="font-mono text-primary-300 text-sm mr-3">{account.account_number}</span>
            <span className="text-sm text-kailasa-text">{account.name}</span>
          </div>
        </td>
        <td className={`py-2.5 px-3 text-sm capitalize ${typeColors[account.account_type] || 'text-kailasa-muted'}`}>
          {account.account_type}
        </td>
        <td className="py-2.5 px-3 text-sm text-kailasa-muted capitalize">{account.normal_balance}</td>
        <td className="py-2.5 px-3">
          <span className={account.is_active ? 'badge-active' : 'badge-inactive'}>
            {account.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td className="py-2.5 px-3">
          <button
            onClick={() => onEdit(account)}
            className="text-xs text-kailasa-muted hover:text-primary-400 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            Edit
          </button>
        </td>
      </tr>
      {isExpanded &&
        hasChildren &&
        account.children!.map((child) => (
          <AccountRow
            key={child.id}
            account={child}
            depth={depth + 1}
            expanded={expanded}
            toggleExpand={toggleExpand}
            onEdit={onEdit}
          />
        ))}
    </>
  );
}

export default function ChartOfAccounts() {
  const { isAdmin } = useAuth();
  const [tree, setTree] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [flatAccounts, setFlatAccounts] = useState<Account[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showModal, setShowModal] = useState(false);
  const [editAccount, setEditAccount] = useState<Account | null>(null);

  const [form, setForm] = useState({
    account_number: '',
    name: '',
    account_type: 'asset',
    normal_balance: 'debit',
    parent_id: '',
    description: '',
  });

  const loadData = () => {
    setLoading(true);
    Promise.all([getAccountsTree(), getAccounts()])
      .then(([treeRes, flatRes]) => {
        setTree(treeRes.data.items || []);
        setFlatAccounts(flatRes.data.items || []);
        // Auto-expand top level
        const topIds = new Set((treeRes.data.items || []).map((a: Account) => a.id));
        setExpanded(topIds);
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load accounts'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleEdit = (account: Account) => {
    setEditAccount(account);
    setForm({
      account_number: account.account_number,
      name: account.name,
      account_type: account.account_type,
      normal_balance: account.normal_balance,
      parent_id: '',
      description: account.description || '',
    });
    setShowModal(true);
  };

  const handleCreate = () => {
    setEditAccount(null);
    setForm({
      account_number: '',
      name: '',
      account_type: 'asset',
      normal_balance: 'debit',
      parent_id: '',
      description: '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        account_number: form.account_number,
        name: form.name,
        account_type: form.account_type,
        normal_balance: form.normal_balance,
        description: form.description || undefined,
      };
      if (form.parent_id) payload.parent_id = form.parent_id;

      if (editAccount) {
        await updateAccount(editAccount.id, payload);
      } else {
        await createAccount(payload);
      }
      setShowModal(false);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Save failed');
    }
  };

  const filteredTree = search
    ? flatAccounts.filter(
        (a) =>
          a.account_number.includes(search) ||
          a.name.toLowerCase().includes(search.toLowerCase())
      )
    : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-kailasa-text">Chart of Accounts</h1>
          <p className="text-kailasa-muted text-sm mt-0.5">{flatAccounts.length} accounts</p>
        </div>
        {isAdmin && (
          <button onClick={handleCreate} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> New Account
          </button>
        )}
      </div>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} />
          <span className="text-sm">{error}</span>
          <button onClick={() => setError('')} className="ml-auto">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-kailasa-muted" />
        <input
          type="text"
          className="input pl-9"
          placeholder="Search by account number or name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Table */}
      <div className="card !p-0 overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-kailasa-border text-left">
              <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Account</th>
              <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Type</th>
              <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Normal Balance</th>
              <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Status</th>
              <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase w-16"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-kailasa-border/50">
            {filteredTree
              ? filteredTree.map((a) => (
                  <AccountRow key={a.id} account={a} expanded={expanded} toggleExpand={toggleExpand} onEdit={handleEdit} />
                ))
              : tree.map((a) => (
                  <AccountRow key={a.id} account={a} expanded={expanded} toggleExpand={toggleExpand} onEdit={handleEdit} />
                ))}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-kailasa-text">
                {editAccount ? 'Edit Account' : 'New Account'}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-kailasa-muted hover:text-kailasa-text">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Account Number</label>
                  <input
                    className="input"
                    value={form.account_number}
                    onChange={(e) => setForm({ ...form, account_number: e.target.value })}
                    placeholder="e.g. 1000"
                    required
                  />
                </div>
                <div>
                  <label className="label">Name</label>
                  <input
                    className="input"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Account name"
                    required
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Type</label>
                  <select
                    className="select"
                    value={form.account_type}
                    onChange={(e) => setForm({ ...form, account_type: e.target.value })}
                  >
                    <option value="asset">Asset</option>
                    <option value="liability">Liability</option>
                    <option value="equity">Equity</option>
                    <option value="revenue">Revenue</option>
                    <option value="expense">Expense</option>
                  </select>
                </div>
                <div>
                  <label className="label">Normal Balance</label>
                  <select
                    className="select"
                    value={form.normal_balance}
                    onChange={(e) => setForm({ ...form, normal_balance: e.target.value })}
                  >
                    <option value="debit">Debit</option>
                    <option value="credit">Credit</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Parent Account (optional)</label>
                <select
                  className="select"
                  value={form.parent_id}
                  onChange={(e) => setForm({ ...form, parent_id: e.target.value })}
                >
                  <option value="">None (top-level)</option>
                  {flatAccounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.account_number} — {a.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Description</label>
                <input
                  className="input"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Optional description"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  {editAccount ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
