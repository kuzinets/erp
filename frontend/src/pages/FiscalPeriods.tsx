import { useState, useEffect } from 'react';
import { getFiscalPeriods, getFiscalYears, closePeriod, reopenPeriod } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { Calendar, Lock, Unlock, RefreshCw, AlertCircle, X } from 'lucide-react';

export default function FiscalPeriods() {
  const { isAdmin } = useAuth();
  const [periods, setPeriods] = useState<any[]>([]);
  const [years, setYears] = useState<any[]>([]);
  const [yearFilter, setYearFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadData = async () => {
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

  useEffect(() => { loadData(); }, []);

  const handleClose = async (id: string) => {
    setError(''); setSuccess('');
    try {
      await closePeriod(id);
      setSuccess('Period closed successfully');
      loadData();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed');
    }
  };

  const handleReopen = async (id: string) => {
    setError(''); setSuccess('');
    try {
      await reopenPeriod(id);
      setSuccess('Period reopened');
      loadData();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed');
    }
  };

  const filtered = yearFilter ? periods.filter((p: any) => p.fiscal_year_id === yearFilter) : periods;

  if (loading) return <div className="flex justify-center py-12"><RefreshCw className="w-8 h-8 text-primary-400 animate-spin" /></div>;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-kailasa-text">Fiscal Periods</h1>
        <p className="text-kailasa-muted text-sm mt-0.5">Manage accounting periods</p>
      </div>

      {(error || success) && (
        <div className={`card flex items-center gap-2 text-sm ${error ? 'text-red-400 bg-red-900/20 border-red-700/30' : 'text-green-400 bg-green-900/20 border-green-700/30'}`}>
          <AlertCircle size={16} /> <span>{error || success}</span>
          <button onClick={() => { setError(''); setSuccess(''); }} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      <div className="flex gap-3">
        <select className="select w-auto" value={yearFilter} onChange={(e) => setYearFilter(e.target.value)}>
          <option value="">All Fiscal Years</option>
          {years.map((y: any) => <option key={y.id} value={y.id}>{y.name}</option>)}
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
              {isAdmin && <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase w-24">Action</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-kailasa-border/50">
            {filtered.map((p: any) => (
              <tr key={p.id} className="hover:bg-kailasa-surfaceLight">
                <td className="py-2.5 px-3 text-sm font-mono text-primary-300">{p.period_code}</td>
                <td className="py-2.5 px-3 text-sm text-kailasa-text">{p.period_name}</td>
                <td className="py-2.5 px-3 text-sm text-kailasa-muted">{p.start_date}</td>
                <td className="py-2.5 px-3 text-sm text-kailasa-muted">{p.end_date}</td>
                <td className="py-2.5 px-3"><span className={`badge-${p.status}`}>{p.status}</span></td>
                {isAdmin && (
                  <td className="py-2.5 px-3">
                    {p.status === 'open' ? (
                      <button onClick={() => handleClose(p.id)} className="btn-secondary btn-sm flex items-center gap-1 text-xs">
                        <Lock size={12} /> Close
                      </button>
                    ) : p.status === 'closed' ? (
                      <button onClick={() => handleReopen(p.id)} className="btn-secondary btn-sm flex items-center gap-1 text-xs">
                        <Unlock size={12} /> Reopen
                      </button>
                    ) : (
                      <span className="badge-adjusting text-xs">Adjusting</span>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
