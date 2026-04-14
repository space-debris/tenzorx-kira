/**
 * KIRA — Kirana Detail Page
 *
 * Full borrower record with profile, assessment history,
 * case/loan history, and risk alerts.
 *
 * Owner: Frontend Lead
 * Phase: 9.4
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { listOrganizationKiranas, listOrganizationCases, getPlatformCase } from '../api/kiraApi';
import CaseTimeline from '../components/CaseTimeline';
import {
  Store, MapPin, Phone, User, ArrowLeft,
  Loader2, AlertTriangle, Briefcase, ChevronRight, Building2
} from 'lucide-react';

const STATUS_COLORS = {
  draft: '#94a3b8', submitted: '#3b82f6', under_review: '#a855f7',
  approved: '#10b981', disbursed: '#06b6d4', monitoring: '#f59e0b',
  restructured: '#ef4444', closed: '#6b7280',
};

const STATUS_LABELS = {
  draft: 'Draft', submitted: 'Submitted', under_review: 'Under Review',
  approved: 'Approved', disbursed: 'Disbursed', monitoring: 'Monitoring',
  restructured: 'Restructured', closed: 'Closed',
};

const RISK_BAND_COLORS = {
  LOW: 'bg-emerald-100 text-emerald-700',
  MEDIUM: 'bg-blue-100 text-blue-700',
  HIGH: 'bg-amber-100 text-amber-700',
  VERY_HIGH: 'bg-red-100 text-red-700',
};

function formatCurrency(num) {
  if (num == null) return '—';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(num);
}

export default function KiranaDetail() {
  const { kiranaId } = useParams();
  const { org } = useAuth();
  const [kirana, setKirana] = useState(null);
  const [cases, setCases] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!org?.id || !kiranaId) return;

    async function load() {
      try {
        setLoading(true);

        // Fetch all kiranas and find this one
        const kiranaRes = await listOrganizationKiranas(org.id);
        const allKiranas = kiranaRes.data || [];
        const matchedKirana = allKiranas.find(k => k.id === kiranaId);

        if (!matchedKirana) {
          setError('Kirana profile not found');
          return;
        }
        setKirana(matchedKirana);

        // Fetch cases for this org and filter by kirana_id
        const casesRes = await listOrganizationCases(org.id);
        const allCases = casesRes.data || [];
        const kiranaCases = allCases.filter(c => c.kirana_id === kiranaId);
        setCases(kiranaCases);

        // Fetch audit events from the first case if available
        if (kiranaCases.length > 0) {
          try {
            const caseDetail = await getPlatformCase(kiranaCases[0].id);
            setAuditEvents(caseDetail.data?.audit_events || []);
          } catch {
            // Audit events are optional
          }
        }
      } catch (err) {
        console.error('Failed to load kirana detail:', err);
        setError('Failed to load kirana details');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [org?.id, kiranaId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  if (error || !kirana) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <p className="text-slate-600 font-medium">{error || 'Kirana not found'}</p>
        <Link to="/app/kiranas" className="text-primary-600 hover:text-primary-700 font-semibold text-sm mt-4 inline-block">← Back to Kirana Directory</Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <Link to="/app/kiranas" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-primary-600 transition mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Kiranas
      </Link>

      {/* Profile Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm mb-6">
        <div className="flex flex-col sm:flex-row items-start gap-5">
          <div className="w-14 h-14 bg-primary-100 rounded-xl flex items-center justify-center text-primary-600 shrink-0">
            <Store className="w-7 h-7" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-extrabold text-slate-900 mb-1">{kirana.store_name}</h1>
            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-500 mt-2">
              <span className="flex items-center gap-1.5"><User className="w-4 h-4" /> {kirana.owner_name}</span>
              <span className="flex items-center gap-1.5"><Phone className="w-4 h-4" /> {kirana.owner_mobile}</span>
            </div>
          </div>
          {kirana.metadata?.shop_size && (
            <span className="px-3 py-1 bg-primary-50 text-primary-700 text-sm font-bold rounded-lg capitalize border border-primary-100">
              {kirana.metadata.shop_size} store
            </span>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column: Location & Details */}
        <div className="lg:col-span-1 space-y-6">
          {/* Location Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-purple-600" /> Location
            </h2>
            <div className="space-y-3 text-sm">
              {kirana.location?.locality && (
                <div>
                  <span className="text-xs font-semibold text-slate-400 uppercase">Locality</span>
                  <p className="font-medium text-slate-800">{kirana.location.locality}</p>
                </div>
              )}
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase">District</span>
                <p className="font-medium text-slate-800">{kirana.location?.district}</p>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase">State</span>
                <p className="font-medium text-slate-800">{kirana.location?.state}</p>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase">PIN Code</span>
                <p className="font-bold text-slate-800 font-mono">{kirana.location?.pin_code}</p>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
            <Link 
              to={cases.length > 0 ? `/app/tools/assessment?caseId=${cases[0].id}` : '/app/tools/assessment'} 
              className="flex items-center justify-between w-full px-4 py-3 bg-primary-50 hover:bg-primary-100 text-primary-700 rounded-lg font-semibold text-sm transition"
            >
              Run New Assessment <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Right Column: Cases + Timeline */}
        <div className="lg:col-span-2 space-y-6">
          {/* Cases */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-primary-600" /> Cases ({cases.length})
            </h2>
            {cases.length > 0 ? (
              <div className="space-y-3">
                {cases.map((c) => (
                  <Link
                    key={c.id}
                    to={`/app/cases/${c.id}`}
                    className="flex items-center justify-between p-4 bg-slate-50 hover:bg-primary-50 rounded-lg border border-slate-100 hover:border-primary-200 transition group"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold capitalize" style={{ backgroundColor: `${STATUS_COLORS[c.status]}15`, color: STATUS_COLORS[c.status] }}>
                          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: STATUS_COLORS[c.status] }} />
                          {STATUS_LABELS[c.status] || c.status}
                        </span>
                        {c.latest_risk_band && (
                          <span className={`px-2 py-0.5 rounded text-xs font-bold ${RISK_BAND_COLORS[c.latest_risk_band] || ''}`}>
                            {c.latest_risk_band}
                          </span>
                        )}
                      </div>
                      {c.latest_loan_range && (
                        <p className="text-sm text-slate-600 font-medium">
                          Loan: {formatCurrency(c.latest_loan_range.low)} – {formatCurrency(c.latest_loan_range.high)}
                        </p>
                      )}
                      {c.notes && <p className="text-xs text-slate-400 mt-1 truncate max-w-sm">{c.notes}</p>}
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-primary-500 transition" />
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-10 text-slate-400">
                <Briefcase className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p className="text-sm">No cases for this kirana yet</p>
              </div>
            )}
          </div>

          {/* Activity Timeline */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-indigo-600" /> Activity Timeline
            </h2>
            <CaseTimeline events={auditEvents} />
          </div>
        </div>
      </div>
    </div>
  );
}
