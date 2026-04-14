/**
 * KIRA — Case Detail Page
 *
 * Full case detail view with kirana profile, assessment summary,
 * status actions, and audit timeline.
 * Fetches from GET /platform/cases/{case_id}.
 *
 * Owner: Frontend Lead
 * Phase: 9.4
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { getPlatformCase, overrideUnderwritingDecision, updateCaseStatus } from '../api/kiraApi';
import CaseTimeline from '../components/CaseTimeline';
import OverrideDecisionForm from '../components/OverrideDecisionForm';
import UnderwritingDecisionPanel from '../components/UnderwritingDecisionPanel';
import {
  ArrowLeft, Loader2, AlertTriangle, Store, MapPin,
  Phone, User, Briefcase, ShieldCheck, ShieldAlert,
  Activity, AlertOctagon, ChevronRight, CheckCircle2,
  ArrowRightLeft, FileText, Rocket
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

// Allowed status transitions
const STATUS_TRANSITIONS = {
  draft: ['submitted'],
  submitted: ['under_review'],
  under_review: ['approved', 'closed'],
  approved: ['disbursed', 'closed'],
  disbursed: ['monitoring', 'closed'],
  monitoring: ['restructured', 'closed'],
  restructured: ['monitoring', 'closed'],
  closed: [],
};

const RISK_CONFIG = {
  LOW: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', icon: ShieldCheck, label: 'Low Risk' },
  MEDIUM: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', icon: Activity, label: 'Medium Risk' },
  HIGH: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', icon: ShieldAlert, label: 'High Risk' },
  VERY_HIGH: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: AlertOctagon, label: 'Very High Risk' },
};

function formatCurrency(num) {
  if (num == null) return '—';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(num);
}

function parseUTCDate(iso) {
  if (!iso) return null;
  let str = iso;
  if (str.includes('T') && !str.endsWith('Z') && !str.match(/[+-]\d{2}:\d{2}$/)) {
    str += 'Z';
  }
  return new Date(str);
}

function formatDate(iso) {
  if (!iso) return 'N/A';
  return parseUTCDate(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function CaseDetail() {
  const { caseId } = useParams();
  const { user } = useAuth();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [transitionLoading, setTransitionLoading] = useState(null);
  const [transitionNote, setTransitionNote] = useState('');
  const [overrideLoading, setOverrideLoading] = useState(false);

  const loadCase = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getPlatformCase(caseId);
      setCaseData(res.data);
    } catch (err) {
      console.error('Failed to load case:', err);
      setError('Failed to load case details');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    if (caseId) loadCase();
    
    // Reload when tab gains focus (e.g. returning from assessment tool)
    const handleFocus = () => { if (caseId) loadCase(); };
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [caseId, loadCase]);

  const handleStatusTransition = async (newStatus) => {
    if (!user?.id) return;
    try {
      setTransitionLoading(newStatus);
      const payload = {
        actor_user_id: user.id,
        new_status: newStatus,
        note: transitionNote || undefined,
      };
      const res = await updateCaseStatus(caseId, payload);
      setCaseData(res.data);
      setTransitionNote('');
    } catch (err) {
      console.error('Status transition failed:', err);
      alert('Failed to update case status. Please try again.');
    } finally {
      setTransitionLoading(null);
    }
  };

  const handleOverrideSubmit = async (payload) => {
    if (!user?.id) return;
    try {
      setOverrideLoading(true);
      const res = await overrideUnderwritingDecision(caseId, {
        actor_user_id: user.id,
        ...payload,
      });
      setCaseData(res.data);
    } catch (err) {
      console.error('Underwriting override failed:', err);
      alert(err?.response?.data?.detail || 'Failed to save override. Please review the values and try again.');
    } finally {
      setOverrideLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <p className="text-slate-600 font-medium">{error || 'Case not found'}</p>
        <Link to="/app/cases" className="text-primary-600 hover:text-primary-700 font-semibold text-sm mt-4 inline-block">← Back to Cases</Link>
      </div>
    );
  }

  const c = caseData.case || {};
  const kirana = caseData.kirana || {};
  const assessment = caseData.latest_assessment;
  const underwritingDecision = caseData.underwriting_decision;
  const alerts = caseData.alerts || [];
  const auditEvents = caseData.audit_events || [];
  const allowedTransitions = STATUS_TRANSITIONS[c.status] || [];

  const riskConfig = RISK_CONFIG[c.latest_risk_band] || RISK_CONFIG.MEDIUM;
  const RiskIcon = riskConfig.icon;

  return (
    <div className="animate-fade-in max-w-5xl mx-auto">
      {/* Breadcrumb */}
      <Link to="/app/cases" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-primary-600 transition mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Cases
      </Link>

      {/* Case Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm mb-6">
        <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-extrabold text-slate-900">{kirana.store_name || 'Case'}</h1>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold capitalize" style={{ backgroundColor: `${STATUS_COLORS[c.status]}15`, color: STATUS_COLORS[c.status] }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: STATUS_COLORS[c.status] }} />
                {STATUS_LABELS[c.status] || c.status}
              </span>
            </div>
            <p className="text-sm text-slate-500 font-mono">Case ID: {c.id?.substring(0, 8).toUpperCase()}</p>
          </div>

          {c.latest_risk_band && (
            <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border ${riskConfig.bg} ${riskConfig.border}`}>
              <RiskIcon className={`w-5 h-5 ${riskConfig.color}`} />
              <span className={`font-bold text-sm ${riskConfig.color}`}>{riskConfig.label}</span>
            </div>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-1 space-y-6">
          {/* Kirana Profile */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Store className="w-4 h-4 text-primary-600" /> Borrower
            </h2>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 text-slate-700">
                <User className="w-4 h-4 text-slate-400" />
                <span className="font-medium">{kirana.owner_name}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <Phone className="w-4 h-4 text-slate-400" />
                <span className="font-medium">{kirana.owner_mobile}</span>
              </div>
              <div className="flex items-start gap-2 text-slate-700">
                <MapPin className="w-4 h-4 text-slate-400 mt-0.5" />
                <span className="font-medium">
                  {[kirana.location?.locality, kirana.location?.district, kirana.location?.state].filter(Boolean).join(', ')}
                  {kirana.location?.pin_code && ` — ${kirana.location.pin_code}`}
                </span>
              </div>
            </div>
          </div>

          {/* Loan Summary */}
          {c.latest_loan_range && (
            <div className="bg-primary-900 text-white rounded-xl p-5 shadow-lg relative overflow-hidden">
              <div className="absolute top-0 right-0 -mt-6 -mr-6 w-24 h-24 bg-primary-600 opacity-20 rounded-full blur-xl"></div>
              <h2 className="text-primary-200 text-xs font-bold uppercase tracking-wider mb-3">Loan Range</h2>
              <div className="text-2xl font-black">
                {formatCurrency(c.latest_loan_range.low)} – {formatCurrency(c.latest_loan_range.high)}
              </div>
            </div>
          )}

          {/* Status Actions */}
          {allowedTransitions.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-indigo-600" /> Actions
              </h2>
              <input
                type="text"
                value={transitionNote}
                onChange={(e) => setTransitionNote(e.target.value)}
                placeholder="Optional note for this action…"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm mb-3 outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-200"
              />
              <div className="space-y-2">
                {allowedTransitions.map((status) => (
                  <button
                    key={status}
                    onClick={() => handleStatusTransition(status)}
                    disabled={transitionLoading === status}
                    className="w-full flex items-center justify-between px-4 py-2.5 rounded-lg border border-slate-200 hover:border-primary-300 hover:bg-primary-50 text-sm font-semibold text-slate-700 hover:text-primary-700 transition-all disabled:opacity-50"
                  >
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: STATUS_COLORS[status] }} />
                      Move to {STATUS_LABELS[status]}
                    </span>
                    {transitionLoading === status ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Assessment Summary */}
          {!assessment ? (
            <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-sm text-center">
              <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <Rocket className="w-8 h-8" />
              </div>
              <h2 className="text-lg font-bold text-slate-800 mb-2">Ready for Underwriting?</h2>
              <p className="text-sm text-slate-600 mb-6 max-w-sm mx-auto">
                Run our visual and spatial analysis to generate a risk score and loan recommendation.
              </p>
              <Link
                to={`/app/tools/assessment?caseId=${c.id}`}
                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg font-bold text-sm transition shadow-sm"
              >
                <Rocket className="w-4 h-4" /> Run AI Assessment
              </Link>
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-600" /> Latest Assessment
                </h2>
                <Link
                  to={`/app/tools/assessment?caseId=${c.id}`}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 px-3 py-1 rounded-full transition"
                >
                  Run New Assessment
                </Link>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {assessment.risk_band && (
                  <div>
                    <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Risk Band</div>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${RISK_CONFIG[assessment.risk_band]?.bg || ''} ${RISK_CONFIG[assessment.risk_band]?.color || ''}`}>
                      {assessment.risk_band}
                    </span>
                  </div>
                )}
                {assessment.risk_score != null && (
                  <div>
                    <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Risk Score</div>
                    <div className="text-lg font-black text-slate-800">{Math.round(assessment.risk_score * 100)}</div>
                  </div>
                )}
                {assessment.revenue_range && (
                  <div>
                    <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Revenue</div>
                    <div className="text-sm font-bold text-slate-700">
                      {formatCurrency(assessment.revenue_range.low)} – {formatCurrency(assessment.revenue_range.high)}
                    </div>
                  </div>
                )}
                {assessment.recommended_amount != null && (
                  <div>
                    <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Recommended</div>
                    <div className="text-sm font-bold text-slate-700">{formatCurrency(assessment.recommended_amount)}</div>
                  </div>
                )}
                <div>
                  <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Completed</div>
                  <div className="text-sm font-medium text-slate-700">{formatDate(assessment.completed_at)}</div>
                </div>
              </div>
              {(assessment.repayment_cadence || assessment.pricing_recommendation) && (
                <div className="grid sm:grid-cols-3 gap-3 mt-4">
                  <div className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">Cadence</div>
                    <div className="text-sm font-semibold text-slate-700 capitalize">
                      {String(assessment.repayment_cadence || 'weekly').replace('_', ' ')}
                    </div>
                  </div>
                  <div className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">Installment</div>
                    <div className="text-sm font-semibold text-slate-700">
                      {formatCurrency(assessment.estimated_installment ?? assessment.estimated_emi)}
                    </div>
                  </div>
                  <div className="rounded-lg bg-slate-50 border border-slate-200 px-3 py-2">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">Annual Rate</div>
                    <div className="text-sm font-semibold text-slate-700">
                      {assessment.pricing_recommendation?.annual_interest_rate_pct != null
                        ? `${Number(assessment.pricing_recommendation.annual_interest_rate_pct).toFixed(2)}%`
                        : '—'}
                    </div>
                  </div>
                </div>
              )}
              {assessment.fraud_flagged && (
                <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2 text-sm font-medium text-amber-800">
                  <AlertTriangle className="w-4 h-4" /> Fraud flags detected on this assessment
                </div>
              )}
            </div>
          )}

          {assessment && underwritingDecision && (
            <>
              <UnderwritingDecisionPanel
                assessment={assessment}
                decision={underwritingDecision}
              />
              <OverrideDecisionForm
                decision={underwritingDecision}
                isSubmitting={overrideLoading}
                onSubmit={handleOverrideSubmit}
              />
            </>
          )}

          {/* Alerts */}
          {alerts.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" /> Alerts ({alerts.length})
              </h2>
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <div key={alert.id} className={`p-3 rounded-lg border ${
                    alert.severity === 'critical' ? 'bg-red-50 border-red-200' :
                    alert.severity === 'warning' ? 'bg-amber-50 border-amber-200' : 'bg-blue-50 border-blue-200'
                  }`}>
                    <p className={`text-sm font-semibold ${
                      alert.severity === 'critical' ? 'text-red-800' :
                      alert.severity === 'warning' ? 'text-amber-800' : 'text-blue-800'
                    }`}>{alert.title}</p>
                    <p className={`text-xs mt-1 ${
                      alert.severity === 'critical' ? 'text-red-600' :
                      alert.severity === 'warning' ? 'text-amber-600' : 'text-blue-600'
                    }`}>{alert.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notes */}
          {c.notes && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-3">Notes</h2>
              <p className="text-sm text-slate-600 leading-relaxed">{c.notes}</p>
            </div>
          )}

          {/* Activity Timeline */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-indigo-600" /> Activity History
            </h2>
            <CaseTimeline events={auditEvents} />
          </div>
        </div>
      </div>
    </div>
  );
}
