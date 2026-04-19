import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Activity, AlertTriangle, ArrowLeft, Loader2, TrendingDown, TrendingUp, Wallet } from 'lucide-react';
import { getLoanAccount, uploadStatement } from '../api/kiraApi';
import { useAuth } from '../context/useAuth';
import { formatCurrency } from '../utils/caseUtils';
import StatementUploadCard from '../components/StatementUploadCard';
import RiskTimeline from '../components/RiskTimeline';

function formatChangeRatio(value) {
  if (value == null || Number.isNaN(Number(value))) return '0%';
  const pct = Math.round(Number(value) * 100);
  return `${pct > 0 ? '+' : ''}${pct}%`;
}

function softenAlertDescription(description = '') {
  const raw = String(description || '').trim();
  if (!raw) return 'Fresh monitoring data needs review.';

  if (/100%\s+lower/i.test(raw) || /prior baseline/i.test(raw)) {
    return 'Fresh statements are materially below the recent baseline and should be reviewed.';
  }

  return raw.replace(/prior baseline/gi, 'recent baseline');
}

export default function LoanAccount() {
  const { caseId } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getLoanAccount(caseId);
      setData(res.data);
      setError(null);
    } catch (err) {
      console.error('Failed to load loan account', err);
      setError('Failed to load loan account.');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    if (caseId) load();
  }, [caseId, load]);

  const handleUpload = async (payload) => {
    if (!user?.id) return;
    try {
      setSubmitting(true);
      await uploadStatement(caseId, { ...payload, actor_user_id: user.id });
      await load();
    } catch (err) {
      console.error('Statement upload failed', err);
      setError(err?.response?.data?.detail || 'Failed to upload statement.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-primary-500 animate-spin" /></div>;
  }

  if (error || !data) {
    return <div className="text-center py-20"><AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" /><p className="text-slate-600 font-medium">{error || 'Loan account not found'}</p></div>;
  }

  const { loan_account: account, loan_decision: decision, kirana, statement_uploads: uploads = [], monitoring_runs: runs = [], alerts = [] } = data;
  const latestRun = runs[0];

  return (
    <div className="animate-fade-in max-w-6xl mx-auto space-y-6">
      <Link to="/app/active-loans" className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-primary-600 transition">
        <ArrowLeft className="w-4 h-4" /> Back to Active Loans
      </Link>

      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 flex items-center gap-2">
              <Wallet className="w-6 h-6 text-primary-600" /> {kirana.store_name}
            </h1>
            <p className="text-slate-500 mt-1">{kirana.owner_name} • {kirana.location?.district}, {kirana.location?.state}</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="bg-slate-50 rounded-xl px-4 py-3">
              <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Outstanding</div>
              <div className="text-xl font-black text-slate-900 mt-1">{formatCurrency(account.outstanding_principal)}</div>
            </div>
            <div className="bg-slate-50 rounded-xl px-4 py-3">
              <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Cadence</div>
              <div className="text-xl font-black text-slate-900 mt-1 capitalize">{account.repayment_cadence}</div>
            </div>
          </div>
        </div>
        {decision && (
          <div className="grid sm:grid-cols-4 gap-4 mt-6">
            <div>
              <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Approved Amount</div>
              <div className="text-sm font-semibold text-slate-700 mt-1">{formatCurrency(decision.approved_amount)}</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Tenure</div>
              <div className="text-sm font-semibold text-slate-700 mt-1">{decision.approved_tenure_months} months</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Rate</div>
              <div className="text-sm font-semibold text-slate-700 mt-1">{decision.pricing_rate_annual}% p.a.</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Override Reason</div>
              <div className="text-sm font-semibold text-slate-700 mt-1">{decision.override_reason || 'No override'}</div>
            </div>
          </div>
        )}
      </div>

      {latestRun && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-primary-600" />
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Latest Monitoring Insight</h2>
              </div>
              <p className="text-sm text-slate-600 max-w-2xl">
                {latestRun.restructuring_recommendation || 'Upload a fresh statement to generate the next restructuring recommendation.'}
              </p>
            </div>
            <div className="grid sm:grid-cols-3 gap-3 min-w-full lg:min-w-[420px]">
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Risk Band</div>
                <div className="text-sm font-semibold text-slate-800 mt-1">{latestRun.current_risk_band || 'Pending'}</div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Cashflow Trend</div>
                <div className={`text-sm font-semibold mt-1 flex items-center gap-1.5 ${latestRun.inflow_change_ratio < 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
                  {latestRun.inflow_change_ratio < 0 ? <TrendingDown className="w-4 h-4" /> : <TrendingUp className="w-4 h-4" />}
                  {formatChangeRatio(latestRun.inflow_change_ratio)}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Stress Score</div>
                <div className="text-sm font-semibold text-slate-800 mt-1">{Math.round((latestRun.stress_score || 0) * 100)}/100</div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid xl:grid-cols-2 gap-6">
        <StatementUploadCard
          onSubmit={handleUpload}
          isSubmitting={submitting}
          title="Monitoring statement upload"
          description="Upload the latest bank, Paytm, PhonePe, or UPI statement to refresh risk and generate a restructuring recommendation."
          submitLabel="Upload and refresh monitoring"
        />

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4">Recent Uploads</h2>
          {uploads.length ? (
            <div className="space-y-3">
              {uploads.map((upload) => (
                <div key={upload.id} className="rounded-lg border border-slate-100 p-4">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-semibold text-slate-800">{upload.label}</div>
                    <div className="text-xs uppercase tracking-wide font-bold text-primary-600">{upload.status}</div>
                  </div>
                  <div className="text-xs text-slate-400 mt-2">{upload.note}</div>
                  <div className="text-sm text-slate-600 mt-2">
                    Inflows {formatCurrency(upload.inflow_total)} • Outflows {formatCurrency(upload.outflow_total)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-slate-400">No statements uploaded yet.</div>
          )}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4">Risk Timeline</h2>
        <RiskTimeline runs={runs} />
      </div>

      {alerts.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Monitoring Flags</h2>
          </div>
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div key={alert.id} className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                <div className="text-sm font-semibold text-amber-900">{alert.title}</div>
                <div className="text-xs text-amber-700 mt-1">{softenAlertDescription(alert.description)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
