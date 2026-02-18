import { useState, useEffect } from 'react';
import { getContacts, createContact, updateContact, getSubsidiaries } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { Plus, X, Search, RefreshCw, AlertCircle, Users, ChevronLeft, ChevronRight } from 'lucide-react';

const CONTACT_TYPES = ['donor', 'vendor', 'volunteer', 'member', 'other'];

export default function Contacts() {
  const { can } = useAuth();
  const canEdit = can('contacts.create');
  const [contacts, setContacts] = useState<any[]>([]);
  const [subsidiaries, setSubsidiaries] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const pageSize = 20;

  const [form, setForm] = useState({
    name: '', email: '', phone: '', contact_type: 'donor',
    address_line_1: '', city: '', state: '', country: '', zip_code: '',
    subsidiary_id: '', notes: '',
  });

  const loadData = () => {
    setLoading(true);
    const params: any = { page, page_size: pageSize };
    if (search) params.search = search;
    if (typeFilter) params.contact_type = typeFilter;
    getContacts(params)
      .then((res) => { setContacts(res.data.items || []); setTotal(res.data.total || 0); })
      .catch((e) => setError(e.response?.data?.detail || 'Failed'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, [page, typeFilter]);
  useEffect(() => { getSubsidiaries().then((r) => setSubsidiaries(r.data.items || [])).catch(() => {}); }, []);

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setPage(1); loadData(); };

  const handleCreate = () => {
    setEditItem(null);
    setForm({ name: '', email: '', phone: '', contact_type: 'donor', address_line_1: '', city: '', state: '', country: '', zip_code: '', subsidiary_id: '', notes: '' });
    setShowModal(true);
  };

  const handleEdit = (c: any) => {
    setEditItem(c);
    setForm({
      name: c.name || '', email: c.email || '', phone: c.phone || '',
      contact_type: c.contact_type || 'donor',
      address_line_1: c.address_line_1 || '', city: c.city || '',
      state: c.state || '', country: c.country || '', zip_code: c.zip_code || '',
      subsidiary_id: c.subsidiary_id || '', notes: c.notes || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = { ...form };
      if (!payload.subsidiary_id) delete payload.subsidiary_id;
      Object.keys(payload).forEach((k) => { if (payload[k] === '') delete payload[k]; });
      payload.name = form.name;
      payload.contact_type = form.contact_type;
      if (editItem) await updateContact(editItem.id, payload);
      else await createContact(payload);
      setShowModal(false);
      loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Save failed');
    }
  };

  const totalPages = Math.ceil(total / pageSize);
  const badgeClass = (type: string) => `badge-${type === 'donor' ? 'donor' : type === 'vendor' ? 'vendor' : type === 'volunteer' ? 'volunteer' : type === 'member' ? 'member' : 'inactive'}`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-kailasa-text">Contacts</h1>
          <p className="text-kailasa-muted text-sm mt-0.5">{total} contacts</p>
        </div>
        {canEdit && (
          <button onClick={handleCreate} className="btn-primary flex items-center gap-2">
            <Plus size={16} /> New Contact
          </button>
        )}
      </div>

      {error && (
        <div className="card flex items-center gap-2 text-red-400 bg-red-900/20 border-red-700/30">
          <AlertCircle size={16} /> <span className="text-sm">{error}</span>
          <button onClick={() => setError('')} className="ml-auto"><X size={14} /></button>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <form onSubmit={handleSearch} className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-kailasa-muted" />
          <input className="input pl-9" placeholder="Search contacts..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </form>
        <select className="select w-auto" value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}>
          <option value="">All Types</option>
          {CONTACT_TYPES.map((t) => <option key={t} value={t} className="capitalize">{t}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><RefreshCw className="w-6 h-6 text-primary-400 animate-spin" /></div>
      ) : (
        <div className="card !p-0 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-kailasa-border text-left">
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Name</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Type</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Email</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">Phone</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase">City</th>
                <th className="py-3 px-3 text-xs font-semibold text-kailasa-muted uppercase w-16"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-kailasa-border/50">
              {contacts.map((c) => (
                <tr key={c.id} className="hover:bg-kailasa-surfaceLight transition-colors">
                  <td className="py-2.5 px-3 text-sm text-kailasa-text font-medium">{c.name}</td>
                  <td className="py-2.5 px-3"><span className={badgeClass(c.contact_type)}>{c.contact_type}</span></td>
                  <td className="py-2.5 px-3 text-sm text-kailasa-muted">{c.email || '—'}</td>
                  <td className="py-2.5 px-3 text-sm text-kailasa-muted">{c.phone || '—'}</td>
                  <td className="py-2.5 px-3 text-sm text-kailasa-muted">{c.city || '—'}</td>
                  <td className="py-2.5 px-3">
                    {canEdit && (
                      <button onClick={() => handleEdit(c)} className="text-xs text-kailasa-muted hover:text-primary-400">Edit</button>
                    )}
                  </td>
                </tr>
              ))}
              {contacts.length === 0 && (
                <tr><td colSpan={6} className="py-12 text-center text-kailasa-muted">No contacts found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-kailasa-muted">Page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="btn-secondary btn-sm"><ChevronLeft size={14} /></button>
            <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="btn-secondary btn-sm"><ChevronRight size={14} /></button>
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-kailasa-text">{editItem ? 'Edit Contact' : 'New Contact'}</h2>
              <button onClick={() => setShowModal(false)} className="text-kailasa-muted hover:text-kailasa-text"><X size={20} /></button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="label">Name</label>
                  <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div>
                  <label className="label">Type</label>
                  <select className="select" value={form.contact_type} onChange={(e) => setForm({ ...form, contact_type: e.target.value })}>
                    {CONTACT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Subsidiary</label>
                  <select className="select" value={form.subsidiary_id} onChange={(e) => setForm({ ...form, subsidiary_id: e.target.value })}>
                    <option value="">— None —</option>
                    {subsidiaries.map((s: any) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Email</label>
                  <input type="email" className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div>
                  <label className="label">Phone</label>
                  <input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="label">Address</label>
                <input className="input" value={form.address_line_1} onChange={(e) => setForm({ ...form, address_line_1: e.target.value })} placeholder="Street address" />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div><label className="label">City</label><input className="input" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
                <div><label className="label">State</label><input className="input" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} /></div>
                <div><label className="label">Country</label><input className="input" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} /></div>
              </div>
              <div>
                <label className="label">Notes</label>
                <textarea className="input" rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
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
