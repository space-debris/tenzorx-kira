import {
  AlertTriangle,
  BadgeIndianRupee,
  Building2,
  CreditCard,
  ShieldAlert,
  TrendingUp,
  Users,
} from 'lucide-react';

function formatCurrency(value) {
  if (value == null) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function KpiCard({ icon, label, value, tone = 'slate', sub }) {
  const toneStyles = {
    slate: 'bg-slate-50 border-slate-200 text-slate-700',
    indigo: 'bg-indigo-50 border-indigo-200 text-indigo-700',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
    red: 'bg-red-50 border-red-200 text-red-700',
  };
  const Glyph = icon;
  return (
    <div className={`rounded-xl border p-4 ${toneStyles[tone] || toneStyles.slate}`}>
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider opacity-70 mb-1.5">
        <Glyph className="w-3.5 h-3.5" />
        <span>{label}</span>
      </div>
      <div className="text-xl font-black tracking-tight leading-tight">{value}</div>
      {sub && <div className="text-[11px] mt-1 opacity-60">{sub}</div>}
    </div>
  );
}

export default function PortfolioKpiStrip({ kpis }) {
  if (!kpis) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
      <KpiCard
        icon={Building2}
        label="Kiranas"
        value={kpis.total_kiranas}
        tone="slate"
        sub={`${kpis.total_cases} cases`}
      />
      <KpiCard
        icon={CreditCard}
        label="Active Loans"
        value={kpis.active_loans}
        tone="indigo"
        sub={`${kpis.total_loans} total`}
      />
      <KpiCard
        icon={BadgeIndianRupee}
        label="Disbursed"
        value={formatCurrency(kpis.total_disbursed)}
        tone="emerald"
      />
      <KpiCard
        icon={TrendingUp}
        label="Outstanding"
        value={formatCurrency(kpis.total_outstanding)}
        tone="indigo"
        sub={`Collected: ${formatCurrency(kpis.total_collected)}`}
      />
      <KpiCard
        icon={AlertTriangle}
        label="Overdue / NPA"
        value={`${kpis.overdue_count} / ${kpis.npa_count}`}
        tone={kpis.npa_count > 0 ? 'red' : kpis.overdue_count > 0 ? 'amber' : 'emerald'}
        sub={`${kpis.restructured_count} restructured`}
      />
      <KpiCard
        icon={ShieldAlert}
        label="High Risk"
        value={kpis.high_risk_count}
        tone={kpis.high_risk_count > 0 ? 'amber' : 'emerald'}
        sub={`${kpis.open_alerts} open alerts`}
      />
    </div>
  );
}
