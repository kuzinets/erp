import { useState, useEffect } from 'react';
import { getDepartments, createDepartment, getSubsidiaries } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { Plus, X, RefreshCw, AlertCircle, Building } from 'lucide-react';

export default function Departments() {
  const { isAdmin } = useAuth();
  const [departments, setDepartments] = useState<any[]>([]);
  const [subsidiaries, setSubsidiaries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ code: '', name: '', subsidiary_id: '' });

  const loadData = async () => {
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

  useEffect(() => { loadData(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createDepartment({
        code: form.code,
        name: form.name,
        subsidiary_id: form.subsidiary_id || undefined,
      });
      setShowModal(false);
      setForm({ code: '', name: '', subsidiary_id: '' });
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed');
    }
  };

  if (loading) return <div className="flex justify-center py-12"><RefreshCw className="w-8 h-8 text-primary-400 animate-spin" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-kailasa-text">Departments</h1>
          <p className="text-kailasa-muted text-sm mt-0.5">{departments.length} departments</p>
        </div>
        {isAdmin && (
          <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> New Department
          </button>
        )}
      </div>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} /> <span className="text-sm">{error}</span>
          <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

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

      {showModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-kailasa-text">New Department</h2>
              <button onClick={() => setShowModal(false)} className="text-kailasa-muted hover:text-kailasa-text"><X size={20} /></button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div><label className="label">Code</label><input className="input" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required /></div>
              <div><label className="label">Name</label><input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
              <div>
                <label className="label">Subsidiary</label>
                <select className="select" value={form.subsidiary_id} onChange={(e) => setForm({ ...form, subsidiary_id: e.target.value })}>
                  <option value="">— Select —</option>
                  {subsidiaries.map((s: any) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
                </select>
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
