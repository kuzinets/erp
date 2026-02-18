import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  getJournalEntries,
  getJournalEntry,
  createJournalEntry,
  postJournalEntry,
  reverseJournalEntry,
  getAccounts,
  getFiscalPeriods,
  getSubsidiaries,
  getFunds,
} from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import {
  Plus,
  X,
  Search,
  RefreshCw,
  AlertCircle,
  Eye,
  CheckCircle,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  Trash2,
} from 'lucide-react';

// ── JE List ──────────────────────────────────────────────

function JEList({
  onViewDetail,
  onCreateNew,
}: {
  onViewDetail: (id: string) => void;
  onCreateNew: () => void;
}) {
  const { can } = useAuth();
  const canEdit = can('gl.journal_entries.create');
  const [entries, setEntries] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  const pageSize = 20;

  const loadEntries = () => {
    setLoading(true);
    const params: any = { page, page_size: pageSize };
    if (statusFilter) params.status = statusFilter;
    if (search) params.search = search;
    getJournalEntries(params)
      .then((res) => {
        setEntries(res.data.items || []);
        setTotal(res.data.total || 0);
      })
      .catch((e) => setError(e.response?.data?.detail || 'Failed'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadEntries();
  }, [page, statusFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadEntries();
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-kailasa-text">Journal Entries</h1>
          <p className="text-kailasa-muted text-sm mt-0.5">{total} entries</p>
        </div>
        {canEdit && (
          <button onClick={onCreateNew} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> New Entry
          </button>
        )}
      </div>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} /> <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <form onSubmit={handleSearch} className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-kailasa-muted" />
          <input
            className="input pl-9"
            placeholder="Search by memo or entry number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </form>
        <select className="select w-auto" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="posted">Posted</option>
          <option value="reversed">Reversed</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-12"><RefreshCw className="w-6 h-6 text-primary-400 animate-spin" /></div>
      ) : (
        <div className="card !p-0 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-kailasa-border text-left">
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Entry #</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Date</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Memo</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Source</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Status</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase w-16"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-kailasa-border/50">
              {entries.map((je) => (
                <tr key={je.id} className="hover:bg-kailasa-surfaceLight transition-colors cursor-pointer" onClick={() => onViewDetail(je.id)}>
                  <td className="py-2.5 px-3 text-sm font-mono text-primary-300">JE-{je.entry_number}</td>
                  <td className="py-2.5 px-3 text-sm text-kailasa-text">{je.entry_date}</td>
                  <td className="py-2.5 px-3 text-sm text-kailasa-text truncate max-w-[250px]">{je.memo || '—'}</td>
                  <td className="py-2.5 px-3 text-sm text-kailasa-muted capitalize">{je.source}</td>
                  <td className="py-2.5 px-3"><span className={`badge-${je.status}`}>{je.status}</span></td>
                  <td className="py-2.5 px-3">
                    <button className="text-kailasa-muted hover:text-primary-400"><Eye size={16} /></button>
                  </td>
                </tr>
              ))}
              {entries.length === 0 && (
                <tr><td colSpan={6} className="py-12 text-center text-kailasa-muted">No journal entries found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-kailasa-muted">Page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="btn-secondary btn-sm"><ChevronLeft size={14} /></button>
            <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="btn-secondary btn-sm"><ChevronRight size={14} /></button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── JE Detail ──────────────────────────────────────────────

function JEDetail({ jeId, onBack }: { jeId: string; onBack: () => void }) {
  const { can } = useAuth();
  const canEdit = can('gl.journal_entries.create');
  const canPost = can('gl.journal_entries.post');
  const canReverse = can('gl.journal_entries.reverse');
  const [je, setJE] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const loadDetail = () => {
    setLoading(true);
    getJournalEntry(jeId)
      .then((res) => setJE(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'Failed'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadDetail(); }, [jeId]);

  const handlePost = async () => {
    setActionLoading(true);
    try {
      await postJournalEntry(jeId);
      loadDetail();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Post failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReverse = async () => {
    setActionLoading(true);
    try {
      await reverseJournalEntry(jeId);
      loadDetail();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Reverse failed');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="flex justify-center py-12"><RefreshCw className="w-6 h-6 text-primary-400 animate-spin" /></div>;

  if (!je) return <div className="card text-red-400">Journal entry not found</div>;

  const lines = je.lines || [];
  const totalDebit = lines.reduce((s: number, l: any) => s + (parseFloat(l.debit_amount) || 0), 0);
  const totalCredit = lines.reduce((s: number, l: any) => s + (parseFloat(l.credit_amount) || 0), 0);

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="text-primary-400 hover:text-primary-300 flex items-center gap-1 text-sm">
        <ChevronLeft size={16} /> Back to list
      </button>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} /> <span className="text-sm">{error}</span>
          <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-kailasa-text">JE-{je.entry_number}</h1>
            <p className="text-sm text-kailasa-muted">{je.entry_date} &middot; {je.source}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`badge-${je.status}`}>{je.status}</span>
            {canPost && je.status === 'draft' && (
              <button onClick={handlePost} disabled={actionLoading} className="btn-success btn-sm flex items-center gap-1">
                <CheckCircle size={14} /> Post
              </button>
            )}
            {canReverse && je.status === 'posted' && (
              <button onClick={handleReverse} disabled={actionLoading} className="btn-danger btn-sm flex items-center gap-1">
                <RotateCcw size={14} /> Reverse
              </button>
            )}
          </div>
        </div>

        {je.memo && <p className="text-sm text-kailasa-textSecondary mb-4">{je.memo}</p>}

        {/* Lines */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-kailasa-border text-left">
                <th className="py-2 px-3 text-xs font-semibold text-kailasa-muted uppercase">#</th>
                <th className="py-2 px-3 text-xs font-semibold text-kailasa-muted uppercase">Account</th>
                <th className="py-2 px-3 text-xs font-semibold text-kailasa-muted uppercase">Memo</th>
                <th className="py-2 px-3 text-xs font-semibold text-kailasa-muted uppercase text-right">Debit</th>
                <th className="py-2 px-3 text-xs font-semibold text-kailasa-muted uppercase text-right">Credit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-kailasa-border/50">
              {lines.map((line: any, i: number) => (
                <tr key={line.id || i}>
                  <td className="py-2 px-3 text-sm text-kailasa-muted">{i + 1}</td>
                  <td className="py-2 px-3 text-sm">
                    <span className="font-mono text-primary-300">{line.account_number}</span>
                    <span className="text-kailasa-text ml-2">{line.account_name}</span>
                  </td>
                  <td className="py-2 px-3 text-sm text-kailasa-muted">{line.memo || ''}</td>
                  <td className="py-2 px-3 text-sm text-right text-kailasa-text">
                    {parseFloat(line.debit_amount) > 0 ? `$${parseFloat(line.debit_amount).toFixed(2)}` : ''}
                  </td>
                  <td className="py-2 px-3 text-sm text-right text-kailasa-text">
                    {parseFloat(line.credit_amount) > 0 ? `$${parseFloat(line.credit_amount).toFixed(2)}` : ''}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-kailasa-border font-bold">
                <td colSpan={3} className="py-2 px-3 text-sm text-kailasa-text text-right">Totals</td>
                <td className="py-2 px-3 text-sm text-right text-kailasa-text">${totalDebit.toFixed(2)}</td>
                <td className="py-2 px-3 text-sm text-right text-kailasa-text">${totalCredit.toFixed(2)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Metadata */}
      <div className="card">
        <h3 className="text-sm font-semibold text-kailasa-muted mb-3 uppercase">Details</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-kailasa-muted">Source</p>
            <p className="text-kailasa-text capitalize">{je.source}</p>
          </div>
          <div>
            <p className="text-kailasa-muted">Source Reference</p>
            <p className="text-kailasa-text">{je.source_reference || '—'}</p>
          </div>
          <div>
            <p className="text-kailasa-muted">Created</p>
            <p className="text-kailasa-text">{je.created_at ? new Date(je.created_at).toLocaleString() : '—'}</p>
          </div>
          <div>
            <p className="text-kailasa-muted">Posted</p>
            <p className="text-kailasa-text">{je.posted_at ? new Date(je.posted_at).toLocaleString() : '—'}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── JE Create ──────────────────────────────────────────────

function JECreate({ onBack, onCreated }: { onBack: () => void; onCreated: (id: string) => void }) {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [periods, setPeriods] = useState<any[]>([]);
  const [subsidiaries, setSubsidiaries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    entry_date: new Date().toISOString().slice(0, 10),
    memo: '',
    subsidiary_id: '',
    fiscal_period_id: '',
    auto_post: false,
  });

  const [lines, setLines] = useState([
    { account_id: '', debit_amount: '', credit_amount: '', memo: '' },
    { account_id: '', debit_amount: '', credit_amount: '', memo: '' },
  ]);

  useEffect(() => {
    Promise.all([getAccounts(), getFiscalPeriods(), getSubsidiaries()])
      .then(([accts, fps, subs]) => {
        setAccounts(accts.data.items || []);
        setPeriods(fps.data.items || []);
        setSubsidiaries(subs.data.items || []);
      })
      .finally(() => setLoading(false));
  }, []);

  const addLine = () => setLines([...lines, { account_id: '', debit_amount: '', credit_amount: '', memo: '' }]);

  const removeLine = (i: number) => {
    if (lines.length <= 2) return;
    setLines(lines.filter((_, idx) => idx !== i));
  };

  const updateLine = (i: number, field: string, value: string) => {
    const newLines = [...lines];
    (newLines[i] as any)[field] = value;
    setLines(newLines);
  };

  const totalDebit = lines.reduce((s, l) => s + (parseFloat(l.debit_amount) || 0), 0);
  const totalCredit = lines.reduce((s, l) => s + (parseFloat(l.credit_amount) || 0), 0);
  const balanced = Math.abs(totalDebit - totalCredit) < 0.01 && totalDebit > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!balanced) {
      setError('Debits must equal credits');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const payload = {
        entry_date: form.entry_date,
        memo: form.memo,
        subsidiary_id: form.subsidiary_id || undefined,
        fiscal_period_id: form.fiscal_period_id || undefined,
        auto_post: form.auto_post,
        lines: lines
          .filter((l) => l.account_id)
          .map((l) => ({
            account_id: l.account_id,
            debit_amount: parseFloat(l.debit_amount) || 0,
            credit_amount: parseFloat(l.credit_amount) || 0,
            memo: l.memo || undefined,
          })),
      };
      const res = await createJournalEntry(payload);
      onCreated(res.data.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Create failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex justify-center py-12"><RefreshCw className="w-6 h-6 text-primary-400 animate-spin" /></div>;

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="text-primary-400 hover:text-primary-300 flex items-center gap-1 text-sm">
        <ChevronLeft size={16} /> Back to list
      </button>

      <h1 className="text-2xl font-bold text-kailasa-text">New Journal Entry</h1>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} /> <span className="text-sm">{error}</span>
          <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Header fields */}
        <div className="card">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label">Date</label>
              <input type="date" className="input" value={form.entry_date} onChange={(e) => setForm({ ...form, entry_date: e.target.value })} required />
            </div>
            <div>
              <label className="label">Subsidiary</label>
              <select className="select" value={form.subsidiary_id} onChange={(e) => setForm({ ...form, subsidiary_id: e.target.value })}>
                <option value="">— Select —</option>
                {subsidiaries.map((s: any) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Fiscal Period</label>
              <select className="select" value={form.fiscal_period_id} onChange={(e) => setForm({ ...form, fiscal_period_id: e.target.value })}>
                <option value="">— Auto-detect —</option>
                {periods.filter((p: any) => p.status === 'open').map((p: any) => <option key={p.id} value={p.id}>{p.period_code}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="label">Memo</label>
            <input className="input" value={form.memo} onChange={(e) => setForm({ ...form, memo: e.target.value })} placeholder="Journal entry description..." />
          </div>
        </div>

        {/* Lines */}
        <div className="card !p-0">
          <div className="p-4 border-b border-kailasa-border flex items-center justify-between">
            <h3 className="font-semibold text-kailasa-text">Lines</h3>
            <button type="button" onClick={addLine} className="btn-secondary btn-sm flex items-center gap-1">
              <Plus size={14} /> Add Line
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-kailasa-border text-left">
                  <th className="py-2 px-3 text-xs font-semibold text-kailasa-muted uppercase">Account</th>
                  <th className="py-2 px-3 text-xs font-semibold text-kailasa-muted uppercase">Memo</th>
                  <th className="py-2 px-3 text-xs font-semibold text-kailasa-muted uppercase w-32">Debit</th>
                  <th className="py-2 px-3 text-xs font-semibold text-kailasa-muted uppercase w-32">Credit</th>
                  <th className="py-2 px-3 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line, i) => (
                  <tr key={i} className="border-b border-kailasa-border/30">
                    <td className="py-2 px-2">
                      <select className="select text-sm" value={line.account_id} onChange={(e) => updateLine(i, 'account_id', e.target.value)}>
                        <option value="">Select account</option>
                        {accounts.map((a: any) => <option key={a.id} value={a.id}>{a.account_number} — {a.name}</option>)}
                      </select>
                    </td>
                    <td className="py-2 px-2">
                      <input className="input text-sm" value={line.memo} onChange={(e) => updateLine(i, 'memo', e.target.value)} placeholder="Line memo" />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="number" step="0.01" min="0" className="input text-sm text-right"
                        value={line.debit_amount} onChange={(e) => updateLine(i, 'debit_amount', e.target.value)} placeholder="0.00"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="number" step="0.01" min="0" className="input text-sm text-right"
                        value={line.credit_amount} onChange={(e) => updateLine(i, 'credit_amount', e.target.value)} placeholder="0.00"
                      />
                    </td>
                    <td className="py-2 px-2">
                      {lines.length > 2 && (
                        <button type="button" onClick={() => removeLine(i)} className="text-kailasa-muted hover:text-red-400">
                          <Trash2 size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-kailasa-border">
                  <td colSpan={2} className="py-2 px-3 text-sm font-bold text-kailasa-text text-right">Totals</td>
                  <td className={`py-2 px-3 text-sm font-bold text-right ${balanced ? 'text-green-400' : 'text-red-400'}`}>${totalDebit.toFixed(2)}</td>
                  <td className={`py-2 px-3 text-sm font-bold text-right ${balanced ? 'text-green-400' : 'text-red-400'}`}>${totalCredit.toFixed(2)}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm text-kailasa-textSecondary cursor-pointer">
            <input type="checkbox" checked={form.auto_post} onChange={(e) => setForm({ ...form, auto_post: e.target.checked })} className="rounded" />
            Post immediately
          </label>
          <div className="flex gap-3">
            <button type="button" onClick={onBack} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving || !balanced} className="btn-primary">
              {saving ? 'Creating...' : 'Create Journal Entry'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────

export default function JournalEntries() {
  const [view, setView] = useState<'list' | 'detail' | 'create'>('list');
  const [selectedId, setSelectedId] = useState('');

  return (
    <>
      {view === 'list' && (
        <JEList
          onViewDetail={(id) => { setSelectedId(id); setView('detail'); }}
          onCreateNew={() => setView('create')}
        />
      )}
      {view === 'detail' && (
        <JEDetail
          jeId={selectedId}
          onBack={() => setView('list')}
        />
      )}
      {view === 'create' && (
        <JECreate
          onBack={() => setView('list')}
          onCreated={(id) => { setSelectedId(id); setView('detail'); }}
        />
      )}
    </>
  );
}
