/**
 * KIRA - Kirana Detail Page
 *
 * Full borrower record with profile, assessment history,
 * loan history, statement-upload readiness, and risk alerts.
 */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Store, MapPin, Phone, User, ArrowLeft, Loader2, AlertTriangle,
  Briefcase, ChevronRight, Building2, FileSearch, Wallet, Upload
} from 'lucide-react';
import { useAuth } from '../context/useAuth';
import { getPlatformKiranaDetail } from '../api/kiraApi';
import CaseTimeline from '../components/CaseTimeline';
import { formatCurrency, getCaseNextAction } from '../utils/caseUtils';

const STATUS_COLORS = {
  draft: '#94a3b8',
  submitted: '#3b82f6',
  under_review: '#a855f7',
  approved: '#10b981',
  disbursed: '#06b6d4',
  monitoring: '#f59e0b',
  restructured: '#ef4444',
  closed: '#6b7280',
};

const STATUS_LABELS = {
  draft: 'Draft',
  submitted: 'Submitted',
  under_review: 'Under Review',
  approved: 'Approved',
  disbursed: 'Disbursed',
  monitoring: 'Monitoring',
  restructured: 'Restructured',
  closed: 'Closed',
};

const RISK_BAND_COLORS = {
  LOW: 'bg-emerald-100 text-emerald-700',
  MEDIUM: 'bg-blue-100 text-blue-700',
  HIGH: 'bg-amber-100 text-amber-700',
  VERY_HIGH: 'bg-red-100 text-red-700',
};

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function KiranaDetail() {
  const { kiranaId } = useParams();
  const { org } = useAuth();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!org?.id || !kiranaId) return;

    async function load() {
      try {
        setLoading(true);
        const res = await getPlatformKiranaDetail(org.id, kiranaId);
        setDetail(res.data);
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
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-primary-500 animate-spin" /></div>;
  }

  if (error || !detail?.kirana) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <p className="text-slate-600 font-medium">{error || 'Kirana not found'}</p>
        <Link to="/app/kiranas" className="text-primary-600 hover:text-primary-700 font-semibold text-sm mt-4 inline-block">Back to Kirana Directory</Link>
      </div>
    );
  }

  const { kirana, cases = [], assessment_history: assessmentHistory = [], loan_history: loanHistory = [], statement_uploads: statementUploads = [], alerts = [], audit_events: auditEvents = [] } = detail;

  return (
    <div className="animate-fade-in max-w-6xl mx-auto">
      <Link to="/app/kiranas" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-primary-600 transition mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Kiranas
      </Link>

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
        <div className="lg:col-span-1 space-y-6">
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

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
            <Link
              to={cases.length > 0 ? `/app/tools/assessment?caseId=${cases[0].id}` : '/app/tools/assessment'}
              className="flex items-center justify-between w-full px-4 py-3 bg-primary-50 hover:bg-primary-100 text-primary-700 rounded-lg font-semibold text-sm transition"
            >
              Run New Assessment <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" /> Risk Alerts
            </h2>
            {alerts.length > 0 ? (
              <div className="space-y-3">
                {alerts.map((alertItem) => (
                  <div key={alertItem.id} className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                    <div className="text-sm font-semibold text-amber-900">{alertItem.title}</div>
                    <div className="text-xs text-amber-700 mt-1">{alertItem.description}</div>
                    <div className="text-[11px] uppercase tracking-wide font-bold text-amber-500 mt-2">{alertItem.severity}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">No active alerts for this borrower.</p>
            )}
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-primary-600" /> Cases ({cases.length})
            </h2>
            {cases.length > 0 ? (
              <div className="space-y-3">
                {cases.map((caseItem) => (
                  <Link
                    key={caseItem.id}
                    to={`/app/cases/${caseItem.id}`}
                    className="flex items-center justify-between p-4 bg-slate-50 hover:bg-primary-50 rounded-lg border border-slate-100 hover:border-primary-200 transition group"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold capitalize" style={{ backgroundColor: `${STATUS_COLORS[caseItem.status]}15`, color: STATUS_COLORS[caseItem.status] }}>
                          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: STATUS_COLORS[caseItem.status] }} />
                          {STATUS_LABELS[caseItem.status] || caseItem.status}
                        </span>
                        {caseItem.latest_risk_band && (
                          <span className={`px-2 py-0.5 rounded text-xs font-bold ${RISK_BAND_COLORS[caseItem.latest_risk_band] || ''}`}>
                            {caseItem.latest_risk_band}
                          </span>
                        )}
                      </div>
                      {caseItem.latest_loan_range && (
                        <p className="text-sm text-slate-600 font-medium">
                          Loan: {formatCurrency(caseItem.latest_loan_range.low)} - {formatCurrency(caseItem.latest_loan_range.high)}
                        </p>
                      )}
                      <p className="text-xs text-slate-400 mt-1">{getCaseNextAction(caseItem)}</p>
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

          <div className="grid xl:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
                <FileSearch className="w-4 h-4 text-emerald-600" /> Assessment History
              </h2>
              {assessmentHistory.length > 0 ? (
                <div className="space-y-3">
                  {assessmentHistory.map((assessment) => (
                    <div key={assessment.assessment_id} className="rounded-lg border border-slate-100 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${RISK_BAND_COLORS[assessment.risk_band] || 'bg-slate-100 text-slate-700'}`}>
                          {assessment.risk_band || 'UNRATED'}
                        </span>
                        <span className="text-xs text-slate-400">{formatDate(assessment.completed_at)}</span>
                      </div>
                      <div className="text-sm font-semibold text-slate-800 mt-3">
                        Revenue: {assessment.revenue_range ? `${formatCurrency(assessment.revenue_range.low)} - ${formatCurrency(assessment.revenue_range.high)}` : '-'}
                      </div>
                      <div className="text-sm text-slate-500 mt-1">
                        Loan: {assessment.loan_range ? `${formatCurrency(assessment.loan_range.low)} - ${formatCurrency(assessment.loan_range.high)}` : '-'}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No completed assessments yet.</p>
              )}
            </div>

            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Wallet className="w-4 h-4 text-sky-600" /> Loan History
              </h2>
              {loanHistory.length > 0 ? (
                <div className="space-y-3">
                  {loanHistory.map((loanItem) => (
                    <div key={loanItem.case_id} className="rounded-lg border border-slate-100 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-semibold text-slate-800">{STATUS_LABELS[loanItem.status] || loanItem.status}</span>
                        <span className="text-xs text-slate-400">{formatDate(loanItem.updated_at)}</span>
                      </div>
                      <div className="text-sm text-slate-600 mt-2">
                        {loanItem.loan_range ? `${formatCurrency(loanItem.loan_range.low)} - ${formatCurrency(loanItem.loan_range.high)}` : 'Range not available yet'}
                      </div>
                      {loanItem.notes && <div className="text-xs text-slate-400 mt-1">{loanItem.notes}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No loan progression recorded yet.</p>
              )}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Upload className="w-4 h-4 text-indigo-600" /> Statement Uploads
            </h2>
            {statementUploads.length > 0 ? (
              <div className="space-y-3">
                {statementUploads.map((upload) => (
                  <div key={upload.id} className="rounded-lg border border-slate-100 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-semibold text-slate-800">{upload.label}</span>
                      <span className="text-xs uppercase tracking-wide font-bold text-indigo-500">{upload.status}</span>
                    </div>
                    <div className="text-xs text-slate-400 mt-2">{upload.note}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">No statement uploads recorded yet. The upload pipeline lands in Phase 11.</p>
            )}
          </div>

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
