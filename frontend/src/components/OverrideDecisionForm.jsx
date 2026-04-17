import { useEffect, useMemo, useState } from 'react';
import { Loader2, RotateCcw, ShieldCheck } from 'lucide-react';

const TENURE_OPTIONS = [12, 18, 24, 36];

function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${Number(value).toFixed(2)}%`;
}

function buildFormState(decision) {
  const source = decision?.final_terms || decision?.recommended_terms;
  return {
    amount: source?.amount ?? '',
    tenure_months: source?.tenure_months ?? 18,
    repayment_cadence: source?.repayment_cadence ?? 'weekly',
    annual_interest_rate_pct: source?.annual_interest_rate_pct ?? '',
    processing_fee_pct: source?.processing_fee_pct ?? '',
    reason: decision?.override_reason ?? '',
  };
}

export default function OverrideDecisionForm({ decision, isSubmitting, onSubmit, onCancel, mode = 'override' }) {
  const [form, setForm] = useState(buildFormState(decision));

  useEffect(() => {
    setForm(buildFormState(decision));
  }, [decision]);

  const recommended = decision?.recommended_terms;
  const pricing = decision?.pricing_recommendation;
  const canOverride = Boolean(decision?.eligible && recommended);

  const hasChanges = useMemo(() => {
    if (!recommended) return false;
    return (
      Number(form.amount) !== Number(recommended.amount) ||
      Number(form.tenure_months) !== Number(recommended.tenure_months) ||
      String(form.repayment_cadence) !== String(recommended.repayment_cadence) ||
      Number(form.annual_interest_rate_pct) !== Number(recommended.annual_interest_rate_pct) ||
      Number(form.processing_fee_pct) !== Number(recommended.processing_fee_pct)
    );
  }, [form, recommended]);

  if (!canOverride) {
    return (
      <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider mb-2">
          {mode === 'restructure' ? 'Restructure Loan' : 'Officer Override'}
        </h2>
        <p className="text-sm text-slate-500">
          An override form becomes available once the case has an eligible underwriting recommendation.
        </p>
      </section>
    );
  }

  const handleChange = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleReset = () => {
    setForm({
      amount: recommended.amount,
      tenure_months: recommended.tenure_months,
      repayment_cadence: recommended.repayment_cadence,
      annual_interest_rate_pct: recommended.annual_interest_rate_pct,
      processing_fee_pct: recommended.processing_fee_pct,
      reason: '',
    });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!hasChanges || !form.reason.trim()) return;

    onSubmit({
      override_amount: Number(form.amount),
      override_tenure_months: Number(form.tenure_months),
      override_repayment_cadence: form.repayment_cadence,
      override_annual_interest_rate_pct: Number(form.annual_interest_rate_pct),
      override_processing_fee_pct: Number(form.processing_fee_pct),
      reason: form.reason.trim(),
    });
  };

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-5">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <ShieldCheck className="w-5 h-5 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              {mode === 'restructure' ? 'Restructure Loan' : 'Officer Override'}
            </h2>
          </div>
          <p className="text-sm text-slate-500">
            {mode === 'restructure' 
              ? 'Update the amount, cadence, tenure, or pricing for the restructured loan.' 
              : 'Override amount, cadence, tenure, or pricing. Every change is recorded against the case audit trail.'}
          </p>
        </div>
        <button
          type="button"
          onClick={handleReset}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 text-sm font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-50 transition"
        >
          <RotateCcw className="w-4 h-4" />
          {mode === 'restructure' ? 'Reset Form' : 'Reset to Recommendation'}
        </button>
      </div>

      <div className="grid lg:grid-cols-3 gap-4 mb-5">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
            Amount Guardrail
          </div>
          <div className="font-black text-slate-800">
            {formatCurrency(decision.loan_range_guardrail?.low)} - {formatCurrency(decision.loan_range_guardrail?.high)}
          </div>
        </div>
        {pricing?.annual_interest_rate_band?.low != null && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              Rate Band
            </div>
            <div className="font-black text-slate-800">
              {formatPercent(pricing.annual_interest_rate_band.low)} - {formatPercent(pricing.annual_interest_rate_band.high)}
            </div>
          </div>
        )}
        {pricing?.processing_fee_band?.low != null && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              Fee Band
            </div>
            <div className="font-black text-slate-800">
              {formatPercent(pricing.processing_fee_band.low)} - {formatPercent(pricing.processing_fee_band.high)}
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid md:grid-cols-2 xl:grid-cols-5 gap-4">
          <label className="block">
            <span className="text-sm font-semibold text-slate-700 mb-1 block">Amount</span>
            <input
              type="number"
              min="0"
              value={form.amount}
              onChange={(e) => handleChange('amount', e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-200"
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700 mb-1 block">Tenure</span>
            <select
              value={form.tenure_months}
              onChange={(e) => handleChange('tenure_months', e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-200 bg-white"
            >
              {TENURE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option} months
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700 mb-1 block">Cadence</span>
            <select
              value={form.repayment_cadence}
              onChange={(e) => handleChange('repayment_cadence', e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-200 bg-white"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700 mb-1 block">Annual Rate</span>
            <input
              type="number"
              step="0.01"
              min="0"
              max="60"
              value={form.annual_interest_rate_pct}
              onChange={(e) => handleChange('annual_interest_rate_pct', e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-200"
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-700 mb-1 block">Processing Fee</span>
            <input
              type="number"
              step="0.01"
              min="0"
              max="10"
              value={form.processing_fee_pct}
              onChange={(e) => handleChange('processing_fee_pct', e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-200"
            />
          </label>
        </div>

        <label className="block">
          <span className="text-sm font-semibold text-slate-700 mb-1 block">
            {mode === 'restructure' ? 'Restructure Reason' : 'Override Reason'}
          </span>
          <textarea
            rows="3"
            value={form.reason}
            onChange={(e) => handleChange('reason', e.target.value)}
            placeholder="Explain why the officer is deviating from the system recommendation."
            className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-200 resize-y"
          />
        </label>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
          <p className="text-xs text-slate-500">
            Recommended baseline: {formatCurrency(recommended.amount)}, {recommended.tenure_months} months, {recommended.repayment_cadence}, {formatPercent(recommended.annual_interest_rate_pct)} rate.
          </p>
          <div className="flex items-center gap-2">
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="inline-flex items-center justify-center px-4 py-2.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-bold transition"
              >
                Cancel
              </button>
            )}
            <button
              type="submit"
              disabled={isSubmitting || !hasChanges || !form.reason.trim()}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                mode === 'restructure' ? 'Restructure Loan' : 'Save Override'
              )}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
