import { useCallback, useEffect, useState } from 'react';
import {
  ArrowLeft,
  BadgeIndianRupee,
  CalendarClock,
  CheckCircle2,
  Clock3,
  CreditCard,
  Loader2,
  ReceiptText,
  ShieldAlert,
} from 'lucide-react';
import StatementUploadCard from '../components/StatementUploadCard';
import RiskTimeline from '../components/RiskTimeline';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function formatPercent(value) {
  if (value == null) return '—';
  return `${Number(value).toFixed(2)}%`;
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function titleize(value) {
  if (!value) return '—';
  return String(value)
    .split('_')
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(' ');
}

const STATUS_COLORS = {
  active: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  current: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  overdue: 'bg-amber-100 text-amber-800 border-amber-200',
  npa: 'bg-red-100 text-red-800 border-red-200',
  restructured: 'bg-orange-100 text-orange-800 border-orange-200',
  closed: 'bg-slate-100 text-slate-600 border-slate-200',
  written_off: 'bg-red-100 text-red-800 border-red-200',
};

function MetricCard({ icon, label, value, tone = 'slate', className = '' }) {
  const toneStyles = {
    slate: 'bg-slate-50 border-slate-200 text-slate-700',
    indigo: 'bg-indigo-50 border-indigo-200 text-indigo-700',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
    red: 'bg-red-50 border-red-200 text-red-700',
  };
  const Glyph = icon;
  return (
    <div className={`rounded-xl border p-4 ${toneStyles[tone] || toneStyles.slate} ${className}`}>
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider opacity-80 mb-2">
        <Glyph className="w-4 h-4" />
        <span>{label}</span>
      </div>
      <div className="text-lg font-black tracking-tight leading-tight">{value}</div>
    </div>
  );
}

export default function LoanAccount({ loanId, onBack }) {
  const [loan, setLoan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [runningMonitoring, setRunningMonitoring] = useState(false);

  const fetchLoan = useCallback(async () => {
    if (!loanId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/platform/loans/${loanId}`);
      if (!res.ok) throw new Error(`Failed to load loan (${res.status})`);
      const data = await res.json();
      setLoan(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [loanId]);

  useEffect(() => {
    fetchLoan();
  }, [fetchLoan]);

  const handleRunMonitoring = async () => {
    if (!loanId) return;
    setRunningMonitoring(true);
    try {
      const formData = new FormData();
      const res = await fetch(
        `${API_BASE}/api/v1/platform/loans/${loanId}/monitoring/run`,
        { method: 'POST', body: formData }
      );
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || 'Monitoring run failed');
      }
      await fetchLoan();
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningMonitoring(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (error || !loan) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-center">
          <ShieldAlert className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-red-700 font-semibold">{error || 'Loan not found'}</p>
          {onBack && (
            <button
              onClick={onBack}
              className="mt-3 text-sm text-indigo-600 hover:text-indigo-800 underline"
            >
              Go back
            </button>
          )}
        </div>
      </div>
    );
  }

  const loanData = loan.loan;
  const kirana = loan.kirana;
  const hasDPD = loanData.days_past_due > 0;

  return (
    <div className="max-w-5xl mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              onClick={onBack}
              className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 transition"
            >
              <ArrowLeft className="w-4 h-4 text-slate-600" />
            </button>
          )}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <CreditCard className="w-5 h-5 text-indigo-600" />
              <h1 className="text-lg font-black text-slate-900">Loan Account</h1>
            </div>
            <p className="text-sm text-slate-500">
              {kirana?.store_name || 'Unknown Store'} — {kirana?.owner_name || ''}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1.5 rounded-full border text-xs font-bold uppercase ${
              STATUS_COLORS[loanData.status] || STATUS_COLORS.active
            }`}
          >
            {titleize(loanData.status)}
          </span>
          <button
            onClick={handleRunMonitoring}
            disabled={runningMonitoring}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition disabled:opacity-50"
          >
            {runningMonitoring ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Running...
              </>
            ) : (
              'Run Monitoring'
            )}
          </button>
        </div>
      </div>

      {/* Loan Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        <MetricCard
          icon={BadgeIndianRupee}
          label="Principal"
          value={formatCurrency(loanData.principal_amount)}
          tone="indigo"
          className="col-span-2"
        />
        <MetricCard
          icon={BadgeIndianRupee}
          label="Outstanding"
          value={formatCurrency(loanData.outstanding_principal)}
          tone={hasDPD ? 'red' : 'emerald'}
        />
        <MetricCard
          icon={ReceiptText}
          label="Installment"
          value={formatCurrency(loanData.estimated_installment)}
          tone="slate"
        />
        <MetricCard
          icon={CalendarClock}
          label="Tenure"
          value={`${loanData.tenure_months}m`}
          tone="slate"
        />
        <MetricCard
          icon={Clock3}
          label="Cadence"
          value={titleize(loanData.repayment_cadence)}
          tone="emerald"
        />
      </div>

      {/* Additional Details */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Loan Details
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Annual Rate</span>
              <span className="font-semibold text-slate-800">{formatPercent(loanData.annual_interest_rate_pct)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Processing Fee</span>
              <span className="font-semibold text-slate-800">{formatPercent(loanData.processing_fee_pct)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Disbursed</span>
              <span className="font-semibold text-slate-800">{formatDate(loanData.disbursed_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Maturity</span>
              <span className="font-semibold text-slate-800">{formatDate(loanData.maturity_date)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Total Collected</span>
              <span className="font-semibold text-slate-800">{formatCurrency(loanData.total_collected)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Days Past Due</span>
              <span className={`font-semibold ${hasDPD ? 'text-red-600' : 'text-emerald-600'}`}>
                {loanData.days_past_due}
              </span>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Original Assessment Snapshot
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Original Risk Band</span>
              <span className="font-semibold text-slate-800">{loanData.original_risk_band || '—'}</span>
            </div>
            {loanData.original_revenue_range && (
              <>
                <div className="flex justify-between">
                  <span className="text-slate-500">Revenue (Low)</span>
                  <span className="font-semibold text-slate-800">
                    {formatCurrency(loanData.original_revenue_range.low)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Revenue (High)</span>
                  <span className="font-semibold text-slate-800">
                    {formatCurrency(loanData.original_revenue_range.high)}
                  </span>
                </div>
              </>
            )}
            {loanData.utilization && (
              <>
                <div className="flex justify-between">
                  <span className="text-slate-500">Supplier Spend</span>
                  <span className="font-semibold text-slate-800">
                    {loanData.utilization.supplier_inventory_pct?.toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Diversion Risk</span>
                  <span
                    className={`font-semibold ${
                      loanData.utilization.diversion_risk === 'high'
                        ? 'text-red-600'
                        : loanData.utilization.diversion_risk === 'medium'
                        ? 'text-amber-600'
                        : 'text-emerald-600'
                    }`}
                  >
                    {titleize(loanData.utilization.diversion_risk)}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Statement Upload */}
      <StatementUploadCard
        loanId={loanId}
        uploads={loan.statement_uploads || []}
        onUploadComplete={() => fetchLoan()}
      />

      {/* Risk Timeline */}
      <RiskTimeline
        monitoringRuns={loan.monitoring_runs || []}
        alerts={loan.alerts || []}
      />
    </div>
  );
}
