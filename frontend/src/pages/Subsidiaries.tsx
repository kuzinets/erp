import { useState, useEffect } from 'react';
import { getSubsidiaries, createSubsidiary, updateSubsidiary } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { Plus, X, RefreshCw, AlertCircle, Building2, Globe, MapPin } from 'lucide-react';

export default function Subsidiaries() {
  const { can } = useAuth();
  const [subs, setSubs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);

  const [form, setForm] = useState({
    code: '',
    name: '',
    parent_id: '',
    currency: 'USD',
    timezone: 'America/New_York',
    address: '',
    library_entity_code: '',
  });

  const loadData = () => {
    setLoading(true);
    getSubsidiaries()
      .then((res) => setSubs(res.data.items || []))
      .catch((e) => setError(e.response?.data?.detail || 'Failed'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const handleEdit = (item: any) => {
    setEditItem(item);
    setForm({
      code: item.code,
      name: item.name,
      parent_id: item.parent_id || '',
      currency: item.currency || 'USD',
      timezone: item.timezone || 'America/New_York',
      address: item.address || '',
      library_entity_code: item.library_entity_code || '',
    });
    setShowModal(true);
  };

  const handleCreate = () => {
    setEditItem(null);
    setForm({ code: '', name: '', parent_id: '', currency: 'USD', timezone: 'America/New_York', address: '', library_entity_code: '' });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = { ...form };
      if (!payload.parent_id) delete payload.parent_id;
      if (!payload.library_entity_code) delete payload.library_entity_code;
      if (editItem) {
        await updateSubsidiary(editItem.id, payload);
      } else {
        await createSubsidiary(payload);
      }
      setShowModal(false);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Save failed');
    }
  };

  if (loading) {
    return <div className="flex justify-center py-12"><RefreshCw className="w-8 h-8 text-primary-400 animate-spin" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-kailasa-text">Subsidiaries</h1>
          <p className="text-kailasa-muted text-sm mt-0.5">{subs.length} entities</p>
        </div>
        {can('org.subsidiaries.create') && (
          <button onClick={handleCreate} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> New Subsidiary
          </button>
        )}
      </div>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} /> <span className="text-sm">{error}</span>
          <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {subs.map((sub) => (
          <div
            key={sub.id}
            className="card hover:shadow-warm-lg transition-shadow cursor-pointer"
            onClick={() => can('org.subsidiaries.create') && handleEdit(sub)}
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary-600/20 flex items-center justify-center">
                <Building2 size={20} className="text-primary-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono text-primary-300">{sub.code}</span>
                  <span className={sub.is_active ? 'badge-active' : 'badge-inactive'}>
                    {sub.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <h3 className="text-kailasa-text font-semibold mt-0.5">{sub.name}</h3>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-kailasa-muted">
              <span className="flex items-center gap-1"><Globe size={12} /> {sub.currency || 'USD'}</span>
              <span className="flex items-center gap-1"><MapPin size={12} /> {sub.timezone || '—'}</span>
              {sub.library_entity_code && (
                <span className="badge-synced">Library: {sub.library_entity_code}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-kailasa-text">
                {editItem ? 'Edit Subsidiary' : 'New Subsidiary'}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-kailasa-muted hover:text-kailasa-text"><X size={20} /></button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Code</label>
                  <input className="input" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="e.g. HQ" required />
                </div>
                <div>
                  <label className="label">Name</label>
                  <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Full name" required />
                </div>
              </div>
              <div>
                <label className="label">Parent Subsidiary</label>
                <select className="select" value={form.parent_id} onChange={(e) => setForm({ ...form, parent_id: e.target.value })}>
                  <option value="">None (top-level)</option>
                  {subs.filter((s) => s.id !== editItem?.id).map((s) => (
                    <option key={s.id} value={s.id}>{s.code} — {s.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Currency</label>
                  <input className="input" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
                </div>
                <div>
                  <label className="label">Timezone</label>
                  <input className="input" value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="label">Library Entity Code (for sync)</label>
                <input className="input" value={form.library_entity_code} onChange={(e) => setForm({ ...form, library_entity_code: e.target.value })} placeholder="Optional" />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">{editItem ? 'Update' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
