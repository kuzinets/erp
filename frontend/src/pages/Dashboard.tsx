import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getDashboard } from '../services/api';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  FileText,
  Building2,
  Layers,
  BookOpen,
  Plug,
  ArrowRight,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboard()
      .then((res) => setData(res.data))
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load dashboard'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card flex items-center gap-3 text-red-400">
        <AlertCircle size={20} />
        <span>{error}</span>
      </div>
    );
  }

  const kpis = data?.kpis || {};
  const systems = data?.connected_systems || [];
  const recentJEs = data?.recent_journal_entries || [];

  const kpiCards = [
    {
      label: 'Total Revenue',
      value: kpis.total_revenue || 0,
      icon: <TrendingUp size={22} />,
      color: 'text-green-400',
      bg: 'bg-green-900/30',
    },
    {
      label: 'Total Expenses',
      value: kpis.total_expenses || 0,
      icon: <TrendingDown size={22} />,
      color: 'text-red-400',
      bg: 'bg-red-900/30',
    },
    {
      label: 'Net Income',
      value: kpis.net_income || 0,
      icon: <DollarSign size={22} />,
      color: kpis.net_income >= 0 ? 'text-primary-400' : 'text-red-400',
      bg: 'bg-primary-600/20',
    },
    {
      label: 'Journal Entries',
      value: kpis.journal_entries || 0,
      icon: <FileText size={22} />,
      color: 'text-blue-400',
      bg: 'bg-blue-900/30',
      isCurrency: false,
    },
    {
      label: 'Subsidiaries',
      value: kpis.subsidiaries || 0,
      icon: <Building2 size={22} />,
      color: 'text-purple-400',
      bg: 'bg-purple-900/30',
      isCurrency: false,
    },
    {
      label: 'Active Funds',
      value: kpis.funds || 0,
      icon: <Layers size={22} />,
      color: 'text-yellow-400',
      bg: 'bg-yellow-900/30',
      isCurrency: false,
    },
  ];

  const formatCurrency = (v: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-kailasa-text">Dashboard</h1>
        <p className="text-kailasa-muted text-sm mt-1">KAILASA Financial Overview</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {kpiCards.map((kpi) => (
          <div key={kpi.label} className="card flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl ${kpi.bg} flex items-center justify-center ${kpi.color}`}>
              {kpi.icon}
            </div>
            <div>
              <p className="text-sm text-kailasa-muted">{kpi.label}</p>
              <p className={`text-xl font-bold ${kpi.color}`}>
                {kpi.isCurrency === false ? kpi.value : formatCurrency(kpi.value)}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Journal Entries */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-kailasa-text flex items-center gap-2">
              <BookOpen size={18} className="text-primary-400" />
              Recent Journal Entries
            </h2>
            <Link
              to="/gl/journal-entries"
              className="text-primary-400 text-sm hover:text-primary-300 flex items-center gap-1"
            >
              View all <ArrowRight size={14} />
            </Link>
          </div>

          {recentJEs.length === 0 ? (
            <p className="text-kailasa-muted text-sm py-8 text-center">No journal entries yet</p>
          ) : (
            <div className="space-y-2">
              {recentJEs.map((je: any) => (
                <div
                  key={je.id}
                  className="flex items-center justify-between py-2 px-3 rounded-lg bg-kailasa-bgLight hover:bg-kailasa-surfaceLight transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono text-primary-300">JE-{je.entry_number}</span>
                      <span className={`badge-${je.status}`}>{je.status}</span>
                    </div>
                    <p className="text-xs text-kailasa-muted truncate mt-0.5">{je.memo || 'No memo'}</p>
                  </div>
                  <span className="text-xs text-kailasa-muted ml-2 whitespace-nowrap">{je.entry_date}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Connected Systems */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-kailasa-text flex items-center gap-2">
              <Plug size={18} className="text-primary-400" />
              Connected Systems
            </h2>
            <Link
              to="/subsystems"
              className="text-primary-400 text-sm hover:text-primary-300 flex items-center gap-1"
            >
              Manage <ArrowRight size={14} />
            </Link>
          </div>

          {systems.length === 0 ? (
            <p className="text-kailasa-muted text-sm py-8 text-center">No connected systems</p>
          ) : (
            <div className="space-y-3">
              {systems.map((sys: any) => (
                <div
                  key={sys.id || sys.name}
                  className="flex items-center justify-between py-3 px-3 rounded-lg bg-kailasa-bgLight"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-green-900/30">
                      <CheckCircle2 size={16} className="text-green-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-kailasa-text">{sys.name}</p>
                      <p className="text-xs text-kailasa-muted">
                        {sys.last_sync_at
                          ? `Last sync: ${new Date(sys.last_sync_at).toLocaleDateString()}`
                          : 'Never synced'}
                      </p>
                    </div>
                  </div>
                  <span className="badge-active">Active</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
