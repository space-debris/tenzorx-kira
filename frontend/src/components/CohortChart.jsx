import { BarChart3 } from 'lucide-react';

const COHORT_COLORS = [
  'bg-indigo-500',
  'bg-emerald-500',
  'bg-amber-500',
  'bg-rose-500',
  'bg-violet-500',
  'bg-sky-500',
  'bg-orange-500',
  'bg-teal-500',
];

function formatCurrency(value) {
  if (value == null) return '₹0';
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
  return `₹${(value / 1000).toFixed(0)}K`;
}

export default function CohortChart({ cohortData, benchmarks }) {
  if (!cohortData) return null;

  const series = [
    { key: 'by_vintage', title: 'By Vintage' },
    { key: 'by_risk_tier', title: 'By Risk Tier' },
    { key: 'by_state', title: 'By State' },
    { key: 'by_cadence', title: 'By Cadence' },
  ];

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-5">
        <BarChart3 className="w-5 h-5 text-indigo-600" />
        <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
          Cohort Analysis
        </h2>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {series.map(({ key, title }) => {
          const dimension = cohortData[key];
          if (!dimension || !dimension.buckets || dimension.buckets.length === 0) return null;

          const maxOutstanding = Math.max(
            ...dimension.buckets.map((b) => b.total_outstanding || 0),
            1,
          );

          return (
            <div key={key}>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                {title}
              </div>
              <div className="space-y-2.5">
                {dimension.buckets.map((bucket, i) => {
                  const pct = (bucket.total_outstanding / maxOutstanding) * 100;
                  const barColor = COHORT_COLORS[i % COHORT_COLORS.length];

                  return (
                    <div key={bucket.label}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-semibold text-slate-700">
                          {bucket.label}
                        </span>
                        <div className="flex items-center gap-3 text-[11px] text-slate-500">
                          <span>{bucket.loan_count} loans</span>
                          <span className="font-bold">
                            {formatCurrency(bucket.total_outstanding)}
                          </span>
                        </div>
                      </div>
                      <div className="flex h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className={`${barColor} rounded-full transition-all duration-500`}
                          style={{ width: `${Math.max(pct, 3)}%` }}
                        />
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-[10px] text-slate-400">
                        <span>DPD: {bucket.avg_dpd?.toFixed(0)}d</span>
                        <span>Overdue: {bucket.overdue_pct?.toFixed(0)}%</span>
                        <span>NPA: {bucket.npa_pct?.toFixed(0)}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Benchmarks */}
      {benchmarks && Object.keys(benchmarks).length > 0 && (
        <div className="mt-6 pt-5 border-t border-slate-100">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Portfolio Benchmarks
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: 'Avg DPD', value: `${benchmarks.portfolio_avg_dpd?.toFixed(0)}d` },
              { label: 'Overdue Rate', value: `${benchmarks.portfolio_overdue_rate?.toFixed(1)}%` },
              { label: 'NPA Rate', value: `${benchmarks.portfolio_npa_rate?.toFixed(1)}%` },
              { label: 'Avg Tenure', value: `${benchmarks.portfolio_avg_tenure?.toFixed(0)}m` },
              { label: 'Avg Rate', value: `${benchmarks.portfolio_avg_rate?.toFixed(1)}%` },
            ].map(({ label, value }) => (
              <div
                key={label}
                className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-center"
              >
                <div className="text-[10px] font-bold uppercase text-slate-400">{label}</div>
                <div className="text-sm font-black text-slate-800 mt-0.5">{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
