import { useState, useEffect } from 'react';
import {
  getFiscalPeriods,
  getFiscalYears,
  closePeriod,
  reopenPeriod,
  getDepartments,
  createDepartment,
  getSubsidiaries,
} from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import {
  Calendar,
  Building,
  Lock,
  Unlock,
  Plus,
  X,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';

type Tab = 'periods' | 'departments';

export default function Settings() {
  const { can } = useAuth();
  const [tab, setTab] = useState<Tab>('periods');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Periods
  const [periods, setPeriods] = useState<any[]>([]);
  const [years, setYears] = useState<any[]>([]);
  const [yearFilter, setYearFilter] = useState('');

  // Departments
  const [departments, setDepartments] = useState<any[]>([]);
  const [subsidiaries, setSubsidiaries] = useState<any[]>([]);
  const [showDeptModal, setShowDeptModal] = useState(false);
  const [deptForm, setDeptForm] = useState({ code: '', name: '', subsidiary_id: '' });

  const loadPeriods = async () => {
    setLoading(true);
    try {
      const [pRes, yRes] = await Promise.all([getFiscalPeriods(), getFiscalYears()]);
      setPeriods(pRes.data.items || []);
      setYears(yRes.data.items || []);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed');
    } finally {
      setLoading(false);
    }
  };

  const loadDepartments = async () => {
    setLoading(true);
    try {
      const [dRes, sRes] = await Promise.all([getDepartments(), getSubsidiaries()]);
      setDepartments(dRes.data.items || []);
      setSubsidiaries(sRes.data.items || []);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tab === 'periods') loadPeriods();
    else loadDepartments();
  }, [tab]);

  const handleClosePeriod = async (id: string) => {
    setError('');
    setSuccess('');
    try {
      await closePeriod(id);
      setSuccess('Period closed');
      loadPeriods();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed');
    }
  };

  const handleReopenPeriod = async (id: string) => {
    setError('');
    setSuccess('');
    try {
      await reopenPeriod(id);
      setSuccess('Period reopened');
      loadPeriods();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed');
    }
  };

  const handleCreateDept = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createDepartment({
        code: deptForm.code,
        name: deptForm.name,
        subsidiary_id: deptForm.subsidiary_id || undefined,
      });
      setShowDeptModal(false);
      loadDepartments();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed');
    }
  };

  const filteredPeriods = yearFilter
    ? periods.filter((p: any) => p.fiscal_year_id === yearFilter)
    : periods;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-kailasa-text">Settings</h1>
        <p className="text-kailasa-muted text-sm mt-0.5">Fiscal periods & departments</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setTab('periods')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'periods'
              ? 'bg-primary-600/20 text-primary-400 border border-primary-600/30'
              : 'bg-kailasa-surface text-kailasa-muted hover:text-kailasa-text border border-kailasa-border'
          }`}
        >
          <Calendar size={16} /> Fiscal Periods
        </button>
        <button
          onClick={() => setTab('departments')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === 'departments'
              ? 'bg-primary-600/20 text-primary-400 border border-primary-600/30'
              : 'bg-kailasa-surface text-kailasa-muted hover:text-kailasa-text border border-kailasa-border'
          }`}
        >
          <Building size={16} /> Departments
        </button>
      </div>

      {(error || success) && (
        <div className={`card flex items-center gap-2 text-sm ${error ? 'text-red-400 bg-red-900/20 border-red-700/30' : 'text-green-400 bg-green-900/20 border-green-700/30'}`}>
          <AlertCircle size={16} /> <span>{error || success}</span>
          <button onClick={() => { setError(''); setSuccess(''); }} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><RefreshCw className="w-6 h-6 text-primary-400 animate-spin" /></div>
      ) : tab === 'periods' ? (
        <div className="space-y-4">
          {/* Year filter */}
          <div className="flex gap-3">
            <select className="select w-auto" value={yearFilter} onChange={(e) => setYearFilter(e.target.value)}>
              <option value="">All Fiscal Years</option>
              {years.map((y: any) => (
                <option key={y.id} value={y.id}>{y.name}</option>
              ))}
            </select>
          </div>

          <div className="card !p-0 overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-kailasa-border text-left">
                  <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Period Code</th>
                  <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Name</th>
                  <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Start</th>
                  <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">End</th>
                  <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Status</th>
                  {can('org.fiscal_periods.close') && <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase w-24">Action</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-kailasa-border/50">
                {filteredPeriods.map((p: any) => (
                  <tr key={p.id} className="hover:bg-kailasa-surfaceLight">
                    <td className="py-2.5 px-3 text-sm font-mono text-primary-300">{p.period_code}</td>
                    <td className="py-2.5 px-3 text-sm text-kailasa-text">{p.period_name}</td>
                    <td className="py-2.5 px-3 text-sm text-kailasa-muted">{p.start_date}</td>
                    <td className="py-2.5 px-3 text-sm text-kailasa-muted">{p.end_date}</td>
                    <td className="py-2.5 px-3"><span className={`badge-${p.status}`}>{p.status}</span></td>
                    {can('org.fiscal_periods.close') && (
                      <td className="py-2.5 px-3">
                        {p.status === 'open' ? (
                          <button onClick={() => handleClosePeriod(p.id)} className="btn-secondary btn-sm flex items-center gap-1 text-xs">
                            <Lock size={12} /> Close
                          </button>
                        ) : p.status === 'closed' ? (
                          <button onClick={() => handleReopenPeriod(p.id)} className="btn-secondary btn-sm flex items-center gap-1 text-xs">
                            <Unlock size={12} /> Reopen
                          </button>
                        ) : null}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-end">
            {can('org.fiscal_periods.close') && (
              <button onClick={() => setShowDeptModal(true)} className="btn-primary flex items-center gap-2">
                <Plus size={16} /> New Department
              </button>
            )}
          </div>

          <div className="card !p-0 overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-kailasa-border text-left">
                  <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Code</th>
                  <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Name</th>
                  <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Subsidiary</th>
                  <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-kailasa-border/50">
                {departments.map((d: any) => (
                  <tr key={d.id} className="hover:bg-kailasa-surfaceLight">
                    <td className="py-2.5 px-3 text-sm font-mono text-primary-300">{d.code}</td>
                    <td className="py-2.5 px-3 text-sm text-kailasa-text">{d.name}</td>
                    <td className="py-2.5 px-3 text-sm text-kailasa-muted">{d.subsidiary_name || '—'}</td>
                    <td className="py-2.5 px-3"><span className={d.is_active ? 'badge-active' : 'badge-inactive'}>{d.is_active ? 'Active' : 'Inactive'}</span></td>
                  </tr>
                ))}
                {departments.length === 0 && (
                  <tr><td colSpan={4} className="py-12 text-center text-kailasa-muted">No departments</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Dept Modal */}
          {showDeptModal && (
            <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
              <div className="card w-full max-w-md">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold text-kailasa-text">New Department</h2>
                  <button onClick={() => setShowDeptModal(false)} className="text-kailasa-muted hover:text-kailasa-text"><X size={20} /></button>
                </div>
                <form onSubmit={handleCreateDept} className="space-y-4">
                  <div>
                    <label className="label">Code</label>
                    <input className="input" value={deptForm.code} onChange={(e) => setDeptForm({ ...deptForm, code: e.target.value })} placeholder="e.g. HR" required />
                  </div>
                  <div>
                    <label className="label">Name</label>
                    <input className="input" value={deptForm.name} onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })} placeholder="Department name" required />
                  </div>
                  <div>
                    <label className="label">Subsidiary</label>
                    <select className="select" value={deptForm.subsidiary_id} onChange={(e) => setDeptForm({ ...deptForm, subsidiary_id: e.target.value })}>
                      <option value="">— Select —</option>
                      {subsidiaries.map((s: any) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
                    </select>
                  </div>
                  <div className="flex justify-end gap-3">
                    <button type="button" onClick={() => setShowDeptModal(false)} className="btn-secondary">Cancel</button>
                    <button type="submit" className="btn-primary">Create</button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
