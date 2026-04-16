import { Store, CheckCircle, TrendingUp, AlertTriangle, Activity, Settings2 } from 'lucide-react';

const ICON_MAP = {
  "Total kiranas onboarded": Store,
  "Total approved and disbursed": CheckCircle,
  "Active exposure": TrendingUp,
  "High-risk count": AlertTriangle,
  "Stress-alert count": Activity,
  "Restructured count": Settings2,
};

export default function PortfolioKpiStrip({ metrics = [] }) {
  return (
    <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {metrics.map((metric) => {
        const IconComponent = ICON_MAP[metric.label] || Store;
        return (
          <div key={metric.label} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex items-start gap-4 hover:border-indigo-200 transition-colors">
            <div className={`p-3 rounded-xl ${IconsColors[metric.label] || 'bg-slate-50 text-slate-500'}`}>
              <IconComponent className="w-6 h-6" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide font-bold text-slate-400">{metric.label}</div>
              <div className="text-2xl font-black text-slate-900 mt-1">{metric.value}</div>
              {metric.trend_label && <div className="text-xs font-semibold text-slate-500 mt-1">{metric.trend_label}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const IconsColors = {
  "Total kiranas onboarded": "bg-blue-50 text-blue-600",
  "Total approved and disbursed": "bg-emerald-50 text-emerald-600",
  "Active exposure": "bg-indigo-50 text-indigo-600",
  "High-risk count": "bg-red-50 text-red-600",
  "Stress-alert count": "bg-amber-50 text-amber-600",
  "Restructured count": "bg-purple-50 text-purple-600",
};
