import { Store, CheckCircle, TrendingUp, AlertTriangle, Activity, Settings2 } from 'lucide-react';

const INR_NUMBER_FORMATTER = new Intl.NumberFormat('en-IN', {
  maximumFractionDigits: 0,
});

const CURRENCY_LABEL_HINTS = ['exposure', 'amount', 'aum', 'outstanding', 'loan value'];

const DEFAULT_CARD_THEME = {
  card: 'border-slate-200 bg-white shadow-sm hover:border-slate-300 hover:shadow-lg',
  icon: 'bg-slate-100 text-slate-600 ring-slate-200/80',
  accent: 'from-slate-400 via-slate-300 to-slate-200',
  value: 'text-slate-900',
  orb: 'bg-slate-300/20',
};

const CARD_THEMES = {
  'Total kiranas onboarded': {
    card: 'border-sky-200/80 bg-gradient-to-br from-sky-50 to-white shadow-sky-100/70 hover:border-sky-300',
    icon: 'bg-sky-100 text-sky-700 ring-sky-200/90',
    accent: 'from-sky-500 via-cyan-400 to-blue-400',
    value: 'text-sky-950',
    orb: 'bg-sky-400/20',
  },
  'Total approved and disbursed': {
    card: 'border-emerald-200/80 bg-gradient-to-br from-emerald-50 to-white shadow-emerald-100/70 hover:border-emerald-300',
    icon: 'bg-emerald-100 text-emerald-700 ring-emerald-200/90',
    accent: 'from-emerald-500 via-lime-400 to-teal-400',
    value: 'text-emerald-950',
    orb: 'bg-emerald-400/20',
  },
  'Active exposure': {
    card: 'border-indigo-200/80 bg-gradient-to-br from-indigo-50 to-white shadow-indigo-100/70 hover:border-indigo-300',
    icon: 'bg-indigo-100 text-indigo-700 ring-indigo-200/90',
    accent: 'from-indigo-500 via-violet-400 to-blue-400',
    value: 'text-indigo-950',
    orb: 'bg-indigo-400/20',
  },
  'High-risk count': {
    card: 'border-rose-200/80 bg-gradient-to-br from-rose-50 to-white shadow-rose-100/70 hover:border-rose-300',
    icon: 'bg-rose-100 text-rose-700 ring-rose-200/90',
    accent: 'from-rose-500 via-orange-400 to-amber-400',
    value: 'text-rose-950',
    orb: 'bg-rose-400/20',
  },
  'Stress-alert count': {
    card: 'border-amber-200/80 bg-gradient-to-br from-amber-50 to-white shadow-amber-100/70 hover:border-amber-300',
    icon: 'bg-amber-100 text-amber-700 ring-amber-200/90',
    accent: 'from-amber-500 via-orange-400 to-yellow-400',
    value: 'text-amber-950',
    orb: 'bg-amber-400/20',
  },
  'Restructured count': {
    card: 'border-fuchsia-200/80 bg-gradient-to-br from-fuchsia-50 to-white shadow-fuchsia-100/70 hover:border-fuchsia-300',
    icon: 'bg-fuchsia-100 text-fuchsia-700 ring-fuchsia-200/90',
    accent: 'from-fuchsia-500 via-purple-400 to-indigo-400',
    value: 'text-fuchsia-950',
    orb: 'bg-fuchsia-400/20',
  },
};

const TREND_TONE_STYLES = {
  neutral: 'bg-slate-100 text-slate-600',
  positive: 'bg-emerald-100 text-emerald-700',
  negative: 'bg-rose-100 text-rose-700',
};

function isCurrencyMetric(label = '') {
  const normalized = label.toLowerCase();
  return CURRENCY_LABEL_HINTS.some((hint) => normalized.includes(hint));
}

function formatMetricValue(metric) {
  const value = metric?.value;
  if (value == null || value === '') return '-';

  if (typeof value === 'number') {
    const formatted = INR_NUMBER_FORMATTER.format(value);
    return isCurrencyMetric(metric.label) ? `₹${formatted}` : formatted;
  }

  if (typeof value === 'string') {
    const normalized = value.trim();
    const numericCandidate = Number(normalized.replace(/[₹,\s]/g, ''));
    const hasOnlyNumericChars = /^[-+]?([₹\s\d,.]+)$/.test(normalized);

    if (!Number.isNaN(numericCandidate) && hasOnlyNumericChars) {
      const formatted = INR_NUMBER_FORMATTER.format(numericCandidate);
      const currencyLike = normalized.includes('₹') || isCurrencyMetric(metric.label);
      return currencyLike ? `₹${formatted}` : formatted;
    }
  }

  return value;
}

function getTrendTone(label = '') {
  const normalized = label.toLowerCase();
  if (!normalized) return 'neutral';
  if (/(up|increase|improv|growth|higher|surge|\+)/.test(normalized)) return 'positive';
  if (/(down|declin|decrease|drop|risk|overdue|stress|-)/.test(normalized)) return 'negative';
  return 'neutral';
}

const ICON_MAP = {
  'Total kiranas onboarded': Store,
  'Total approved and disbursed': CheckCircle,
  'Active exposure': TrendingUp,
  'High-risk count': AlertTriangle,
  'Stress-alert count': Activity,
  'Restructured count': Settings2,
};

export default function PortfolioKpiStrip({ metrics = [] }) {
  return (
    <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {metrics.map((metric, index) => {
        const IconComponent = ICON_MAP[metric.label] || Store;
        const theme = CARD_THEMES[metric.label] || DEFAULT_CARD_THEME;
        const trendTone = getTrendTone(metric.trend_label || '');

        return (
          <article
            key={metric.label}
            className={`group relative overflow-hidden rounded-2xl border p-5 transition-all duration-300 hover:-translate-y-0.5 ${theme.card}`}
            style={{ animationDelay: `${index * 60}ms` }}
          >
            <div className={`pointer-events-none absolute inset-x-0 top-0 h-1 bg-linear-to-r ${theme.accent}`} />
            <div className={`pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full blur-2xl transition-transform duration-300 group-hover:scale-110 ${theme.orb}`} />

            <div className="relative z-10 flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">
                  {metric.label}
                </p>
                <div className={`mt-2 text-3xl font-black leading-none ${theme.value}`}>
                  {formatMetricValue(metric)}
                </div>
                {metric.trend_label ? (
                  <span className={`mt-3 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${TREND_TONE_STYLES[trendTone]}`}>
                    {metric.trend_label}
                  </span>
                ) : (
                  <span className="mt-3 inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">
                    Stable
                  </span>
                )}
              </div>

              <div className={`relative mt-0.5 rounded-2xl p-3 ring-1 ${theme.icon}`}>
                <IconComponent className="h-6 w-6" />
              </div>
            </div>

            <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-px bg-linear-to-r from-transparent via-white/80 to-transparent" />
          </article>
        );
      })}
    </div>
  );
}
