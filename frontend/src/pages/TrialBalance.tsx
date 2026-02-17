import { useState, useEffect } from 'react';
import { getTrialBalance, getFiscalPeriods, getSubsidiaries } from '../services/api';
import { RefreshCw, AlertCircle, Download } from 'lucide-react';

export default function TrialBalance() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [periods, setPeriods] = useState<any[]>([]);
  const [subsidiaries, setSubsidiaries] = useState<any[]>([]);
  const [periodCode, setPeriodCode] = useState('');
  const [subsidiaryId, setSubsidiaryId] = useState('');

  useEffect(() => {
    Promise.all([getFiscalPeriods(), getSubsidiaries()])
      .then(([pRes, sRes]) => {
        const p = pRes.data.items || [];
        const s = sRes.data.items || [];
        setPeriods(p);
        setSubsidiaries(s);
        // Default to first open period
        const openPeriod = p.find((pp: any) => pp.status === 'open');
        if (openPeriod) setPeriodCode(openPeriod.period_code);
      })
      .catch(() => {});
  }, []);

  const loadTB = () => {
    if (!periodCode) return;
    setLoading(true);
    setError('');
    const params: any = { fiscal_period: periodCode };
    if (subsidiaryId) params.subsidiary_id = subsidiaryId;
    getTrialBalance(params)
      .then((res) => setData(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (periodCode) loadTB();
  }, [periodCode, subsidiaryId]);

  const rows = data?.items || [];
  const totalDebit = rows.reduce((s: number, r: any) => s + (parseFloat(r.debit_balance) || 0), 0);
  const totalCredit = rows.reduce((s: number, r: any) => s + (parseFloat(r.credit_balance) || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;

  const fmt = (v: number) => v === 0 ? '—' : `$${v.toFixed(2)}`;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-kailasa-text">Trial Balance</h1>
        <p className="text-kailasa-muted text-sm mt-0.5">Verify debits equal credits</p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="label">Fiscal Period</label>
            <select className="select" value={periodCode} onChange={(e) => setPeriodCode(e.target.value)}>
              <option value="">Select period...</option>
              {periods.map((p: any) => (
                <option key={p.id} value={p.period_code}>
                  {p.period_code} — {p.period_name} ({p.status})
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="label">Subsidiary</label>
            <select className="select" value={subsidiaryId} onChange={(e) => setSubsidiaryId(e.target.value)}>
              <option value="">All Subsidiaries</option>
              {subsidiaries.map((s: any) => (
                <option key={s.id} value={s.id}>{s.code} — {s.name}</option>
              ))}
            </select>
          </div>
          <button onClick={loadTB} disabled={!periodCode || loading} className="btn-primary flex items-center gap-2">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} /> <span className="text-sm">{error}</span>
        </div>
      )}

      {/* TB Table */}
      {loading ? (
        <div className="flex justify-center py-12"><RefreshCw className="w-6 h-6 text-primary-400 animate-spin" /></div>
      ) : data ? (
        <div className="card !p-0 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-kailasa-border text-left">
                <th className="py-3 px-4 text-xs font-semibold text-kailasa-muted uppercase">Account #</th>
                <th className="py-3 px-4 text-xs font-semibold text-kailasa-muted uppercase">Account Name</th>
                <th className="py-3 px-4 text-xs font-semibold text-kailasa-muted uppercase">Type</th>
                <th className="py-3 px-4 text-xs font-semibold text-kailasa-muted uppercase text-right">Debit</th>
                <th className="py-3 px-4 text-xs font-semibold text-kailasa-muted uppercase text-right">Credit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-kailasa-border/50">
              {rows.map((row: any) => (
                <tr key={row.account_id || row.account_number} className="hover:bg-kailasa-surfaceLight">
                  <td className="py-2.5 px-4 text-sm font-mono text-primary-300">{row.account_number}</td>
                  <td className="py-2.5 px-4 text-sm text-kailasa-text">{row.account_name}</td>
                  <td className="py-2.5 px-4 text-sm text-kailasa-muted capitalize">{row.account_type}</td>
                  <td className="py-2.5 px-4 text-sm text-right text-kailasa-text">{fmt(parseFloat(row.debit_balance) || 0)}</td>
                  <td className="py-2.5 px-4 text-sm text-right text-kailasa-text">{fmt(parseFloat(row.credit_balance) || 0)}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-kailasa-muted">
                    No activity for this period
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-kailasa-border bg-kailasa-bgLight">
                <td colSpan={3} className="py-3 px-4 text-sm font-bold text-kailasa-text text-right">Totals</td>
                <td className="py-3 px-4 text-sm font-bold text-right text-kailasa-text">${totalDebit.toFixed(2)}</td>
                <td className="py-3 px-4 text-sm font-bold text-right text-kailasa-text">${totalCredit.toFixed(2)}</td>
              </tr>
              <tr className="bg-kailasa-bgLight">
                <td colSpan={3} className="py-2 px-4 text-sm font-bold text-kailasa-text text-right">Difference</td>
                <td colSpan={2} className={`py-2 px-4 text-sm font-bold text-center ${isBalanced ? 'text-green-400' : 'text-red-400'}`}>
                  {isBalanced ? 'BALANCED' : `Out of balance by $${Math.abs(totalDebit - totalCredit).toFixed(2)}`}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      ) : (
        <div className="card text-center text-kailasa-muted py-12">
          Select a fiscal period to view the trial balance
        </div>
      )}
    </div>
  );
}
