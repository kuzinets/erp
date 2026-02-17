import { useState, useEffect } from 'react';
import {
  getSubsystems,
  getSubsystem,
  triggerSync,
  getSyncLogs,
  getFiscalPeriods,
  getSubsystemMappings,
} from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import {
  Plug,
  RefreshCw,
  AlertCircle,
  X,
  Play,
  Clock,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  ArrowRight,
} from 'lucide-react';

export default function Subsystems() {
  const { isAdmin } = useAuth();
  const [systems, setSystems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [syncLogs, setSyncLogs] = useState<any[]>([]);
  const [mappings, setMappings] = useState<any[]>([]);
  const [periods, setPeriods] = useState<any[]>([]);
  const [syncPeriod, setSyncPeriod] = useState('');
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<any>(null);

  const loadSystems = () => {
    setLoading(true);
    getSubsystems()
      .then((res) => setSystems(res.data.items || []))
      .catch((e) => setError(e.response?.data?.detail || 'Failed'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadSystems();
    getFiscalPeriods()
      .then((res) => {
        const p = res.data.items || [];
        setPeriods(p);
        const open = p.find((pp: any) => pp.status === 'open');
        if (open) setSyncPeriod(open.period_code);
      })
      .catch(() => {});
  }, []);

  const loadDetail = async (id: string) => {
    setSelectedId(id);
    try {
      const [detailRes, logsRes, mappingsRes] = await Promise.all([
        getSubsystem(id),
        getSyncLogs(id),
        getSubsystemMappings(id),
      ]);
      setDetail(detailRes.data);
      setSyncLogs(logsRes.data.items || []);
      setMappings(mappingsRes.data.items || []);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load details');
    }
  };

  const handleSync = async () => {
    if (!selectedId || !syncPeriod) return;
    setSyncing(true);
    setSyncResult(null);
    setError('');
    try {
      const res = await triggerSync(selectedId, syncPeriod);
      setSyncResult(res.data);
      // Reload logs
      const logsRes = await getSyncLogs(selectedId);
      setSyncLogs(logsRes.data.items || []);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center py-12"><RefreshCw className="w-8 h-8 text-primary-400 animate-spin" /></div>;
  }

  // Detail view
  if (selectedId && detail) {
    return (
      <div className="space-y-4">
        <button onClick={() => { setSelectedId(null); setDetail(null); setSyncResult(null); }} className="text-primary-400 hover:text-primary-300 flex items-center gap-1 text-sm">
          <ChevronLeft size={16} /> Back to systems
        </button>

        {error && (
          <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
            <AlertCircle size={16} /> <span className="text-sm">{error}</span>
            <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
          </div>
        )}

        {/* System Info */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-primary-600/20 flex items-center justify-center">
                <Plug size={24} className="text-primary-400" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-kailasa-text">{detail.name}</h1>
                <p className="text-sm text-kailasa-muted capitalize">{detail.system_type} System</p>
              </div>
            </div>
            <span className={detail.is_active ? 'badge-active' : 'badge-inactive'}>
              {detail.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><p className="text-kailasa-muted">Base URL</p><p className="text-kailasa-text font-mono text-xs break-all">{detail.base_url}</p></div>
            <div><p className="text-kailasa-muted">API Username</p><p className="text-kailasa-text">{detail.api_username || '—'}</p></div>
            <div><p className="text-kailasa-muted">Sync Frequency</p><p className="text-kailasa-text">{detail.sync_frequency_minutes || '—'} min</p></div>
            <div><p className="text-kailasa-muted">Last Sync</p><p className="text-kailasa-text">{detail.last_sync_at ? new Date(detail.last_sync_at).toLocaleString() : 'Never'}</p></div>
          </div>
        </div>

        {/* Trigger Sync */}
        {isAdmin && (
          <div className="card">
            <h3 className="text-sm font-semibold text-kailasa-muted uppercase mb-3">Trigger Sync</h3>
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <label className="label">Fiscal Period</label>
                <select className="select" value={syncPeriod} onChange={(e) => setSyncPeriod(e.target.value)}>
                  {periods.map((p: any) => (
                    <option key={p.id} value={p.period_code}>{p.period_code} — {p.period_name}</option>
                  ))}
                </select>
              </div>
              <button onClick={handleSync} disabled={syncing || !syncPeriod} className="btn-primary flex items-center gap-2">
                {syncing ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
                {syncing ? 'Syncing...' : 'Run Sync'}
              </button>
            </div>
            {syncResult && (
              <div className="mt-3 p-3 rounded-lg bg-green-900/20 border border-green-700/30 text-green-400 text-sm">
                <CheckCircle2 size={16} className="inline mr-2" />
                Sync complete: {syncResult.postings_imported || 0} postings imported, {syncResult.journal_entries_created || 0} JE(s) created
              </div>
            )}
          </div>
        )}

        {/* Account Mappings */}
        <div className="card">
          <h3 className="text-sm font-semibold text-kailasa-muted uppercase mb-3">Account Mappings</h3>
          {mappings.length === 0 ? (
            <p className="text-kailasa-muted text-sm">No mappings configured</p>
          ) : (
            <div className="space-y-2">
              {mappings.map((m: any) => (
                <div key={m.id || m.source_account_code} className="flex items-center gap-3 py-2 px-3 bg-kailasa-bgLight rounded-lg text-sm">
                  <span className="font-mono text-primary-300">{m.source_account_code}</span>
                  <ArrowRight size={14} className="text-kailasa-muted" />
                  <span className="font-mono text-green-400">{m.target_account_number || m.target_account_id}</span>
                  <span className="text-kailasa-muted ml-auto">{m.source_posting_type || ''}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sync Logs */}
        <div className="card">
          <h3 className="text-sm font-semibold text-kailasa-muted uppercase mb-3">Sync History</h3>
          {syncLogs.length === 0 ? (
            <p className="text-kailasa-muted text-sm">No sync history</p>
          ) : (
            <div className="space-y-2">
              {syncLogs.map((log: any) => (
                <div key={log.id} className="flex items-center justify-between py-2 px-3 bg-kailasa-bgLight rounded-lg">
                  <div className="flex items-center gap-3">
                    {log.status === 'success' ? (
                      <CheckCircle2 size={16} className="text-green-400" />
                    ) : log.status === 'running' ? (
                      <RefreshCw size={16} className="text-blue-400 animate-spin" />
                    ) : (
                      <XCircle size={16} className="text-red-400" />
                    )}
                    <div>
                      <p className="text-sm text-kailasa-text">
                        Period: {log.fiscal_period_synced || '—'}
                      </p>
                      <p className="text-xs text-kailasa-muted">
                        {log.postings_imported || 0} postings, {log.journal_entries_created || 0} JEs
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`badge-${log.status}`}>{log.status}</span>
                    <p className="text-xs text-kailasa-muted mt-1">
                      {log.started_at ? new Date(log.started_at).toLocaleString() : ''}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // List view
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-kailasa-text">Connected Systems</h1>
        <p className="text-kailasa-muted text-sm mt-0.5">Manage subsystem integrations</p>
      </div>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} /> <span className="text-sm">{error}</span>
          <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {systems.map((sys) => (
          <div
            key={sys.id}
            className="card hover:shadow-warm-lg transition-shadow cursor-pointer"
            onClick={() => loadDetail(sys.id)}
          >
            <div className="flex items-start gap-3">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${sys.is_active ? 'bg-green-900/30' : 'bg-gray-700/40'}`}>
                <Plug size={24} className={sys.is_active ? 'text-green-400' : 'text-gray-500'} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-kailasa-text font-semibold">{sys.name}</h3>
                  <span className={sys.is_active ? 'badge-active' : 'badge-inactive'}>
                    {sys.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="text-sm text-kailasa-muted capitalize mt-0.5">{sys.system_type} System</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-kailasa-muted">
                  <span className="flex items-center gap-1"><Clock size={12} /> {sys.sync_frequency_minutes || '—'}m interval</span>
                  <span>Last: {sys.last_sync_at ? new Date(sys.last_sync_at).toLocaleDateString() : 'Never'}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
        {systems.length === 0 && (
          <div className="col-span-2 card text-center text-kailasa-muted py-12">
            No connected systems configured
          </div>
        )}
      </div>
    </div>
  );
}
