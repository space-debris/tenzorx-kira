import { Activity, TrendingDown, TrendingUp } from 'lucide-react';

function formatPercent(value) {
  return `${value >= 0 ? '+' : ''}${Math.round(value * 100)}%`;
}

export default function RiskTimeline({ runs = [] }) {
  if (!runs.length) {
    return <p className="text-sm text-slate-400">No monitoring runs yet.</p>;
  }

  return (
    <div className="space-y-3">
      {runs.map((run) => (
        <div key={run.id} className="rounded-xl border border-slate-200 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <Activity className="w-4 h-4 text-primary-600" />
                {run.current_risk_band}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                {new Date(run.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
              </div>
            </div>
            <div className={`inline-flex items-center gap-1 text-xs font-bold ${run.inflow_change_ratio < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
              {run.inflow_change_ratio < 0 ? <TrendingDown className="w-3.5 h-3.5" /> : <TrendingUp className="w-3.5 h-3.5" />}
              {formatPercent(run.inflow_change_ratio)}
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-3 mt-4 text-sm">
            <div>
              <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Stress Score</div>
              <div className="font-semibold text-slate-800 mt-1">{Math.round(run.stress_score * 100)}/100</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Restructuring View</div>
              <div className="font-medium text-slate-700 mt-1">{run.restructuring_recommendation || 'No restructure suggested.'}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
