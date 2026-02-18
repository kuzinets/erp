import { useState, useEffect } from 'react';
import { getAuditLog } from '../services/api';
import { ClipboardList, Search, ChevronLeft, ChevronRight } from 'lucide-react';

interface AuditEntry {
  id: string;
  username: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, any> | null;
  ip_address: string | null;
  created_at: string;
}

const ACTION_COLORS: Record<string, string> = {
  create: 'bg-green-900/30 text-green-400',
  update: 'bg-blue-900/30 text-blue-400',
  delete: 'bg-red-900/30 text-red-400',
  post: 'bg-purple-900/30 text-purple-400',
  reverse: 'bg-yellow-900/30 text-yellow-400',
  close: 'bg-orange-900/30 text-orange-400',
  reopen: 'bg-teal-900/30 text-teal-400',
  login: 'bg-gray-700/30 text-gray-400',
  sync: 'bg-cyan-900/30 text-cyan-400',
};

function getActionColor(action: string): string {
  for (const [key, color] of Object.entries(ACTION_COLORS)) {
    if (action.toLowerCase().includes(key)) return color;
  }
  return 'bg-gray-700/30 text-gray-400';
}

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ username: '', action: '', resource_type: '' });

  const pageSize = 25;

  useEffect(() => {
    loadEntries();
  }, [page]);

  const loadEntries = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, page_size: pageSize };
      if (filters.username) params.username = filters.username;
      if (filters.action) params.action = filters.action;
      if (filters.resource_type) params.resource_type = filters.resource_type;
      const res = await getAuditLog(params);
      setEntries(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error('Failed to load audit log', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadEntries();
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-kailasa-text flex items-center gap-2">
          <ClipboardList size={24} className="text-primary-400" />
          Audit Log
        </h1>
        <p className="text-sm text-kailasa-muted mt-1">
          Complete trail of all system actions ({total} entries)
        </p>
      </div>

      {/* Filters */}
      <form onSubmit={handleSearch} className="flex items-center gap-3 flex-wrap">
        <input
          placeholder="Filter by username..."
          value={filters.username}
          onChange={(e) => setFilters({ ...filters, username: e.target.value })}
          className="bg-kailasa-bg border border-kailasa-border rounded-lg px-3 py-2 text-sm text-kailasa-text placeholder-kailasa-muted focus:outline-none focus:border-primary-500 w-40"
        />
        <input
          placeholder="Filter by action..."
          value={filters.action}
          onChange={(e) => setFilters({ ...filters, action: e.target.value })}
          className="bg-kailasa-bg border border-kailasa-border rounded-lg px-3 py-2 text-sm text-kailasa-text placeholder-kailasa-muted focus:outline-none focus:border-primary-500 w-40"
        />
        <input
          placeholder="Filter by resource type..."
          value={filters.resource_type}
          onChange={(e) => setFilters({ ...filters, resource_type: e.target.value })}
          className="bg-kailasa-bg border border-kailasa-border rounded-lg px-3 py-2 text-sm text-kailasa-text placeholder-kailasa-muted focus:outline-none focus:border-primary-500 w-40"
        />
        <button
          type="submit"
          className="flex items-center gap-1.5 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Search size={14} />
          Search
        </button>
      </form>

      {/* Table */}
      <div className="bg-kailasa-surface border border-kailasa-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-6 h-6 border-3 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-12 text-kailasa-muted">No audit entries found</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-kailasa-border bg-kailasa-bg/50">
                <th className="text-left px-4 py-3 text-kailasa-muted font-medium">Time</th>
                <th className="text-left px-4 py-3 text-kailasa-muted font-medium">User</th>
                <th className="text-left px-4 py-3 text-kailasa-muted font-medium">Action</th>
                <th className="text-left px-4 py-3 text-kailasa-muted font-medium">Resource</th>
                <th className="text-left px-4 py-3 text-kailasa-muted font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-b border-kailasa-border/50 hover:bg-kailasa-bg/30">
                  <td className="px-4 py-2.5 text-kailasa-muted text-xs whitespace-nowrap">
                    {entry.created_at ? new Date(entry.created_at).toLocaleString() : '-'}
                  </td>
                  <td className="px-4 py-2.5 text-kailasa-text font-medium">
                    {entry.username || '-'}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${getActionColor(entry.action)}`}>
                      {entry.action}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-kailasa-textSecondary text-xs">
                    {entry.resource_type && (
                      <span>
                        {entry.resource_type}
                        {entry.resource_id && <span className="text-kailasa-muted"> #{entry.resource_id.slice(0, 8)}</span>}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-kailasa-muted text-xs max-w-xs truncate">
                    {entry.details ? JSON.stringify(entry.details) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-kailasa-muted">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg bg-kailasa-surface border border-kailasa-border text-kailasa-muted hover:text-kailasa-text disabled:opacity-50 transition-colors"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-lg bg-kailasa-surface border border-kailasa-border text-kailasa-muted hover:text-kailasa-text disabled:opacity-50 transition-colors"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
