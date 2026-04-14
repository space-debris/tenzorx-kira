import {
  AlertTriangle,
  BadgeIndianRupee,
  CalendarClock,
  CheckCircle2,
  Clock3,
  ReceiptText,
  ShieldAlert,
} from 'lucide-react';

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

function titleize(value) {
  if (!value) return '—';
  return String(value)
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function MetricCard({
  icon,
  label,
  value,
  tone = 'slate',
  className = '',
  valueClassName = '',
}) {
  const toneStyles = {
    slate: 'bg-slate-50 border-slate-200 text-slate-700',
    indigo: 'bg-indigo-50 border-indigo-200 text-indigo-700',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
  };
  const Glyph = icon;

  return (
    <div className={`rounded-xl border p-4 ${toneStyles[tone] || toneStyles.slate} ${className}`}>
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider opacity-80 mb-2">
        <Glyph className="w-4 h-4" />
        <span>{label}</span>
      </div>
      <div className={`text-lg font-black tracking-tight leading-tight break-words ${valueClassName}`}>
        {value}
      </div>
    </div>
  );
}

export default function UnderwritingDecisionPanel({ assessment, decision }) {
  if (!assessment || !decision) return null;

  const eligible = Boolean(decision.eligible);
  const recommendedTerms = decision.recommended_terms;
  const finalTerms = decision.final_terms || recommendedTerms;
  const hasOverride = Boolean(decision.has_override);
  const decisionPack = assessment.decision_pack;
  const summary = assessment.explanation_summary;
  const pricing = decision.pricing_recommendation || assessment.pricing_recommendation;

  if (!eligible || !recommendedTerms || !finalTerms) {
    return (
      <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <ShieldAlert className="w-5 h-5 text-amber-500" />
          <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
            Underwriting Decision
          </h2>
        </div>
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          This assessment does not currently support a lendable underwriting recommendation.
          Review the fraud flags, risk posture, and supporting evidence before manual action.
        </div>
      </section>
    );
  }

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-5">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Underwriting Decision
            </h2>
          </div>
          <p className="text-sm text-slate-500">
            Officer-ready recommendation generated from the latest assessment snapshot.
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Policy Guardrail
          </div>
          <div className="text-sm font-bold text-slate-700">
            {formatCurrency(decision.loan_range_guardrail?.low)} - {formatCurrency(decision.loan_range_guardrail?.high)}
          </div>
        </div>
      </div>

      {hasOverride && (
        <div className="mb-5 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
          <div className="flex items-center gap-2 text-indigo-800 font-bold text-sm mb-1">
            <AlertTriangle className="w-4 h-4" />
            Officer Override Captured
          </div>
          <p className="text-sm text-indigo-700 mb-2">{decision.override_reason}</p>
          {decision.policy_exception_flags?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {decision.policy_exception_flags.map((flag) => (
                <span
                  key={flag}
                  className="px-2 py-1 rounded-full bg-white border border-indigo-200 text-[11px] font-bold text-indigo-700"
                >
                  {titleize(flag)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 xl:grid-cols-3 gap-4 mb-6">
        <MetricCard
          icon={BadgeIndianRupee}
          label={hasOverride ? 'Final Amount' : 'Recommended Amount'}
          value={formatCurrency(finalTerms.amount)}
          tone="indigo"
          className="col-span-2 xl:col-span-2 min-h-[116px] flex flex-col justify-between"
          valueClassName="text-3xl"
        />
        <MetricCard
          icon={CalendarClock}
          label="Tenure"
          value={`${finalTerms.tenure_months} Months`}
          tone="slate"
          className="min-h-[116px] flex flex-col justify-between"
          valueClassName="text-2xl"
        />
        <MetricCard
          icon={Clock3}
          label="Repayment"
          value={titleize(finalTerms.repayment_cadence)}
          tone="emerald"
          className="min-h-[116px] flex flex-col justify-between"
          valueClassName="text-2xl"
        />
        <MetricCard
          icon={ReceiptText}
          label="Installment"
          value={formatCurrency(finalTerms.estimated_installment)}
          tone="amber"
          className="min-h-[116px] flex flex-col justify-between"
          valueClassName="text-2xl"
        />
        <MetricCard
          icon={ShieldAlert}
          label="Annual Rate"
          value={formatPercent(finalTerms.annual_interest_rate_pct)}
          tone="slate"
          className="min-h-[116px] flex flex-col justify-between"
          valueClassName="text-2xl"
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Decision Logic
          </div>
          <div className="space-y-3 text-sm text-slate-700">
            <p>{decisionPack?.amount_rationale || 'Concrete loan sizing uses the approved range and conservative revenue view.'}</p>
            <p>{decisionPack?.tenure_rationale || 'Tenure is selected to keep repayment affordable against observed cash generation.'}</p>
            <p>{decisionPack?.repayment_rationale || 'Repayment cadence is matched to the inferred cash rotation pattern.'}</p>
            <p>{decisionPack?.pricing_rationale || pricing?.rationale || 'Pricing falls back to standard policy guidance.'}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 p-4">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
              Pricing Guidance
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-slate-400 mb-1">Rate</div>
                <div className="font-bold text-slate-800">{formatPercent(finalTerms.annual_interest_rate_pct)}</div>
                <div className="text-xs text-slate-500">
                  Band: {formatPercent(pricing?.annual_interest_rate_band?.low)} - {formatPercent(pricing?.annual_interest_rate_band?.high)}
                </div>
              </div>
              <div>
                <div className="text-slate-400 mb-1">Processing Fee</div>
                <div className="font-bold text-slate-800">{formatPercent(finalTerms.processing_fee_pct)}</div>
                <div className="text-xs text-slate-500">
                  Band: {formatPercent(pricing?.processing_fee_band?.low)} - {formatPercent(pricing?.processing_fee_band?.high)}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 p-4">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
              Key Signals
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <div className="text-xs font-semibold uppercase text-emerald-600 mb-2">Strengths</div>
                <div className="space-y-2">
                  {(summary?.strengths || []).slice(0, 3).map((item) => (
                    <div key={item} className="rounded-lg bg-emerald-50 border border-emerald-100 px-3 py-2 text-sm text-emerald-900">
                      {item}
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-amber-600 mb-2">Concerns</div>
                <div className="space-y-2">
                  {(summary?.concerns || []).slice(0, 3).map((item) => (
                    <div key={item} className="rounded-lg bg-amber-50 border border-amber-100 px-3 py-2 text-sm text-amber-900">
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
