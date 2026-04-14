/**
 * KIRA — New Case / Onboarding Page
 *
 * Guided form to create a new kirana case via POST /platform/cases.
 *
 * Owner: Frontend Lead
 * Phase: 9.3
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { createPlatformCase } from '../api/kiraApi';
import {
  Store, ArrowLeft, PlusCircle, AlertCircle,
  MapPin, User, Phone, FileText, Loader2
} from 'lucide-react';

const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Delhi', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand',
  'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur',
  'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan',
  'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh',
  'Uttarakhand', 'West Bengal',
];

export default function NewCase() {
  const navigate = useNavigate();
  const { user, org } = useAuth();

  const [form, setForm] = useState({
    store_name: '',
    owner_name: '',
    owner_mobile: '',
    state: '',
    district: '',
    pin_code: '',
    locality: '',
    notes: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validate required fields
    if (!form.store_name.trim()) { setError('Store name is required'); return; }
    if (!form.owner_name.trim()) { setError('Owner name is required'); return; }
    if (!form.owner_mobile.trim() || form.owner_mobile.trim().length < 8) { setError('Valid mobile number is required'); return; }
    if (!form.state) { setError('State is required'); return; }
    if (!form.district.trim()) { setError('District is required'); return; }
    if (!form.pin_code.trim() || form.pin_code.trim().length < 3) { setError('Valid PIN code is required'); return; }

    try {
      setIsSubmitting(true);

      const payload = {
        org_id: org.id,
        created_by_user_id: user.id,
        store_name: form.store_name.trim(),
        owner_name: form.owner_name.trim(),
        owner_mobile: form.owner_mobile.trim(),
        state: form.state,
        district: form.district.trim(),
        pin_code: form.pin_code.trim(),
        locality: form.locality.trim() || undefined,
        assigned_to_user_id: user.id, // Fallback to current user
        notes: form.notes.trim() || undefined,
        metadata: {},
      };

      const res = await createPlatformCase(payload);
      const newCaseId = res.data?.case?.id;

      if (newCaseId) {
        navigate(`/app/cases/${newCaseId}`);
      } else {
        navigate('/app/cases');
      }
    } catch (err) {
      console.error('Failed to create case:', err);
      setError(err?.response?.data?.detail || 'Failed to create case. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="animate-fade-in max-w-3xl mx-auto">
      <Link to="/app/cases" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-primary-600 transition mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Cases
      </Link>

      <div className="mb-8">
        <h1 className="text-2xl font-extrabold text-slate-900 flex items-center gap-2">
          <PlusCircle className="w-6 h-6 text-primary-600" /> New Case
        </h1>
        <p className="text-slate-500 font-medium mt-1">Onboard a new kirana borrower and create an assessment case</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 p-4 rounded-xl flex items-start gap-3 mb-6 shadow-sm animate-scale-in">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <span className="font-medium text-sm">{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Store Info */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-5 flex items-center gap-2">
            <Store className="w-4 h-4 text-primary-600" /> Store Details
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Store Name *</label>
              <input type="text" value={form.store_name} onChange={(e) => updateField('store_name', e.target.value)} required placeholder="e.g., Gupta General Store" className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm" />
            </div>
          </div>
        </div>

        {/* Owner Info */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-5 flex items-center gap-2">
            <User className="w-4 h-4 text-purple-600" /> Owner Details
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Owner Name *</label>
              <input type="text" value={form.owner_name} onChange={(e) => updateField('owner_name', e.target.value)} required placeholder="e.g., Sanjay Gupta" className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Mobile Number *</label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input type="tel" value={form.owner_mobile} onChange={(e) => updateField('owner_mobile', e.target.value)} required placeholder="+91-9876543210" className="w-full border border-slate-300 rounded-lg pl-10 pr-4 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm" />
              </div>
            </div>
          </div>
        </div>

        {/* Location */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-5 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-emerald-600" /> Location
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">State *</label>
              <select value={form.state} onChange={(e) => updateField('state', e.target.value)} required className="appearance-none w-full border border-slate-300 bg-white rounded-lg px-4 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm">
                <option value="">Select state</option>
                {INDIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">District *</label>
              <input type="text" value={form.district} onChange={(e) => updateField('district', e.target.value)} required placeholder="e.g., Meerut" className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">PIN Code *</label>
              <input type="text" value={form.pin_code} onChange={(e) => updateField('pin_code', e.target.value)} required placeholder="e.g., 250002" maxLength={6} className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm font-mono" />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Locality</label>
              <input type="text" value={form.locality} onChange={(e) => updateField('locality', e.target.value)} placeholder="e.g., Shastri Nagar (optional)" className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm" />
            </div>
          </div>
        </div>

        {/* Notes */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-5 flex items-center gap-2">
            <FileText className="w-4 h-4 text-amber-600" /> Additional Notes
          </h2>
          <textarea
            value={form.notes}
            onChange={(e) => updateField('notes', e.target.value)}
            placeholder="Any notes for this case (optional)…"
            rows={3}
            className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm resize-none"
          />
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-3 pt-2">
          <Link to="/app/cases" className="px-6 py-3 border border-slate-300 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition">
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-bold text-sm transition-all shadow-lg shadow-primary-600/25"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Creating…
              </>
            ) : (
              <>
                <PlusCircle className="w-4 h-4" /> Create Case
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
