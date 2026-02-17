import { useState, useEffect } from 'react';
import {
  getStatementOfActivities,
  getStatementOfFinancialPosition,
  getFundBalances,
  getFiscalPeriods,
  getSubsidiaries,
} from '../services/api';
import { RefreshCw, AlertCircle, BarChart3, PieChart } from 'lucide-react';

type ReportType = 'activities' | 'position' | 'funds';

export default function FinancialStatements() {
  const [reportType, setReportType] = useState<ReportType>('activities');
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
        setPeriods(p);
        setSubsidiaries(sRes.data.items || []);
        const openPeriod = p.find((pp: any) => pp.status === 'open');
        if (openPeriod) setPeriodCode(openPeriod.period_code);
      })
      .catch(() => {});
  }, []);

  const loadReport = () => {
    if (!periodCode) return;
    setLoading(true);
    setError('');

    let fetcher;
    if (reportType === 'activities') {
      const params: any = { fiscal_period: periodCode };
      if (subsidiaryId) params.subsidiary_id = subsidiaryId;
      fetcher = getStatementOfActivities(params);
    } else if (reportType === 'position') {
      const params: any = { as_of_period: periodCode };
      if (subsidiaryId) params.subsidiary_id = subsidiaryId;
      fetcher = getStatementOfFinancialPosition(params);
    } else {
      const params: any = { fiscal_period: periodCode };
      fetcher = getFundBalances(params);
    }

    fetcher
      .then((res) => setData(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'Failed'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (periodCode) loadReport();
  }, [periodCode, subsidiaryId, reportType]);

  const fmt = (v: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v || 0);

  const renderActivities = () => {
    if (!data) return null;
    const revenue = data.revenue?.items || data.revenue || [];
    const expenses = data.expenses?.items || data.expenses || [];
    const totalRevenue = data.revenue?.total ?? revenue.reduce((s: number, r: any) => s + (parseFloat(r.amount) || 0), 0);
    const totalExpenses = data.expenses?.total ?? expenses.reduce((s: number, r: any) => s + (parseFloat(r.amount) || 0), 0);

    return (
      <div className="space-y-6">
        {/* Revenue */}
        <div>
          <h3 className="text-sm font-bold text-green-400 uppercase tracking-wider mb-3">Revenue</h3>
          <div className="space-y-1">
            {revenue.map((r: any) => (
              <div key={r.account_number} className="flex justify-between py-1.5 px-3 hover:bg-kailasa-surfaceLight rounded">
                <span className="text-sm text-kailasa-text">
                  <span className="font-mono text-primary-300 mr-2">{r.account_number}</span>
                  {r.account_name}
                </span>
                <span className="text-sm text-green-400 font-medium">{fmt(parseFloat(r.amount))}</span>
              </div>
            ))}
            <div className="flex justify-between py-2 px-3 border-t border-kailasa-border mt-2 font-bold">
              <span className="text-sm text-kailasa-text">Total Revenue</span>
              <span className="text-sm text-green-400">{fmt(totalRevenue)}</span>
            </div>
          </div>
        </div>

        {/* Expenses */}
        <div>
          <h3 className="text-sm font-bold text-red-400 uppercase tracking-wider mb-3">Expenses</h3>
          <div className="space-y-1">
            {expenses.map((r: any) => (
              <div key={r.account_number} className="flex justify-between py-1.5 px-3 hover:bg-kailasa-surfaceLight rounded">
                <span className="text-sm text-kailasa-text">
                  <span className="font-mono text-primary-300 mr-2">{r.account_number}</span>
                  {r.account_name}
                </span>
                <span className="text-sm text-red-400 font-medium">{fmt(parseFloat(r.amount))}</span>
              </div>
            ))}
            <div className="flex justify-between py-2 px-3 border-t border-kailasa-border mt-2 font-bold">
              <span className="text-sm text-kailasa-text">Total Expenses</span>
              <span className="text-sm text-red-400">{fmt(totalExpenses)}</span>
            </div>
          </div>
        </div>

        {/* Net */}
        <div className="flex justify-between py-3 px-4 bg-kailasa-bgLight rounded-lg border-2 border-kailasa-border font-bold">
          <span className="text-kailasa-text">Change in Net Assets</span>
          <span className={totalRevenue - totalExpenses >= 0 ? 'text-green-400' : 'text-red-400'}>
            {fmt(totalRevenue - totalExpenses)}
          </span>
        </div>
      </div>
    );
  };

  const renderPosition = () => {
    if (!data) return null;
    const assets = data.assets?.items || data.assets || [];
    const liabilities = data.liabilities?.items || data.liabilities || [];
    const equity = data.net_assets?.items || data.equity || [];
    const totalAssets = data.assets?.total ?? assets.reduce((s: number, r: any) => s + (parseFloat(r.amount) || 0), 0);
    const totalLiabilities = data.liabilities?.total ?? liabilities.reduce((s: number, r: any) => s + (parseFloat(r.amount) || 0), 0);
    const totalEquity = data.net_assets?.total ?? equity.reduce((s: number, r: any) => s + (parseFloat(r.amount) || 0), 0);

    const renderSection = (title: string, items: any[], color: string, total: number) => (
      <div>
        <h3 className={`text-sm font-bold ${color} uppercase tracking-wider mb-3`}>{title}</h3>
        <div className="space-y-1">
          {items.map((r: any) => (
            <div key={r.account_number} className="flex justify-between py-1.5 px-3 hover:bg-kailasa-surfaceLight rounded">
              <span className="text-sm text-kailasa-text">
                <span className="font-mono text-primary-300 mr-2">{r.account_number}</span>
                {r.account_name}
              </span>
              <span className="text-sm text-kailasa-text">{fmt(parseFloat(r.amount))}</span>
            </div>
          ))}
          <div className="flex justify-between py-2 px-3 border-t border-kailasa-border mt-2 font-bold">
            <span className="text-sm text-kailasa-text">Total {title}</span>
            <span className={`text-sm ${color}`}>{fmt(total)}</span>
          </div>
        </div>
      </div>
    );

    return (
      <div className="space-y-6">
        {renderSection('Assets', assets, 'text-blue-400', totalAssets)}
        {renderSection('Liabilities', liabilities, 'text-red-400', totalLiabilities)}
        {renderSection('Net Assets', equity, 'text-purple-400', totalEquity)}
        <div className="flex justify-between py-3 px-4 bg-kailasa-bgLight rounded-lg border-2 border-kailasa-border font-bold">
          <span className="text-kailasa-text">Liabilities + Net Assets</span>
          <span className="text-kailasa-text">{fmt(totalLiabilities + totalEquity)}</span>
        </div>
      </div>
    );
  };

  const renderFunds = () => {
    if (!data) return null;
    const funds = data.funds || data.items || [];
    return (
      <div className="space-y-2">
        {funds.map((f: any) => (
          <div key={f.fund_code || f.id} className="flex justify-between items-center py-3 px-4 bg-kailasa-bgLight rounded-lg">
            <div>
              <p className="text-sm font-medium text-kailasa-text">{f.fund_name || f.name}</p>
              <p className="text-xs text-kailasa-muted capitalize">{(f.fund_type || '').replace('_', ' ')}</p>
            </div>
            <span className={`text-sm font-bold ${(parseFloat(f.balance) || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {fmt(parseFloat(f.balance) || 0)}
            </span>
          </div>
        ))}
        {funds.length === 0 && <p className="text-center text-kailasa-muted py-8">No fund data available</p>}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-kailasa-text">Financial Reports</h1>
        <p className="text-kailasa-muted text-sm mt-0.5">Non-profit financial statements</p>
      </div>

      {/* Report Type Tabs */}
      <div className="flex gap-2">
        {[
          { key: 'activities' as const, label: 'Statement of Activities', icon: <BarChart3 size={16} /> },
          { key: 'position' as const, label: 'Statement of Financial Position', icon: <PieChart size={16} /> },
          { key: 'funds' as const, label: 'Fund Balances', icon: <PieChart size={16} /> },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setReportType(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              reportType === tab.key
                ? 'bg-primary-600/20 text-primary-400 border border-primary-600/30'
                : 'bg-kailasa-surface text-kailasa-muted hover:text-kailasa-text border border-kailasa-border'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="label">Fiscal Period</label>
            <select className="select" value={periodCode} onChange={(e) => setPeriodCode(e.target.value)}>
              <option value="">Select period...</option>
              {periods.map((p: any) => (
                <option key={p.id} value={p.period_code}>{p.period_code} — {p.period_name}</option>
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
        </div>
      </div>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} /> <span className="text-sm">{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><RefreshCw className="w-6 h-6 text-primary-400 animate-spin" /></div>
      ) : (
        <div className="card">
          {reportType === 'activities' && renderActivities()}
          {reportType === 'position' && renderPosition()}
          {reportType === 'funds' && renderFunds()}
        </div>
      )}
    </div>
  );
}
