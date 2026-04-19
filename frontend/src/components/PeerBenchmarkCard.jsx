/**
 * KIRA — Peer Benchmark Card
 *
 * Displays how the assessed store compares to peers in the same area type.
 * Shows overall percentile, per-signal breakdown, and strengths/weaknesses.
 *
 * Owner: Frontend Lead
 * Phase: Optional Extension
 *
 * Props:
 *   peerBenchmark (object) — peer benchmark result from backend
 */

import { Users, TrendingUp, TrendingDown, Award, BarChart3 } from 'lucide-react';

function PercentileBar({ label, percentile }) {
  const pct = Math.max(0, Math.min(100, percentile || 0));
  let color = 'bg-emerald-500';
  let textColor = 'text-emerald-700';
  let bgColor = 'bg-emerald-50';
  if (pct < 25) {
    color = 'bg-red-500';
    textColor = 'text-red-700';
    bgColor = 'bg-red-50';
  } else if (pct < 50) {
    color = 'bg-amber-500';
    textColor = 'text-amber-700';
    bgColor = 'bg-amber-50';
  } else if (pct < 75) {
    color = 'bg-sky-500';
    textColor = 'text-sky-700';
    bgColor = 'bg-sky-50';
  }

  return (
    <div className="mb-4 last:mb-0">
      <div className="flex justify-between items-end mb-1.5">
        <span className="text-sm font-semibold text-slate-700">{label}</span>
        <span className={`text-sm font-black ${textColor} ${bgColor} px-2 py-0.5 rounded-full`}>
          P{pct}
        </span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden relative">
        {/* Quartile markers */}
        <div className="absolute left-1/4 top-0 w-px h-full bg-slate-300 z-10" />
        <div className="absolute left-1/2 top-0 w-px h-full bg-slate-300 z-10" />
        <div className="absolute left-3/4 top-0 w-px h-full bg-slate-300 z-10" />
        <div
          className={`h-full rounded-full ${color} transition-all duration-1000`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

const SIGNAL_LABELS = {
  shelf_density: 'Shelf Density',
  sku_diversity_score: 'SKU Diversity',
  footfall_score: 'Footfall Potential',
  competition_score: 'Competitive Position',
  demand_index: 'Demand Index',
};

export default function PeerBenchmarkCard({ peerBenchmark }) {
  if (!peerBenchmark) return null;

  const {
    area_type,
    overall_percentile,
    signal_percentiles,
    revenue_percentile,
    peer_summary,
    strengths_vs_peers,
    weaknesses_vs_peers,
  } = peerBenchmark;

  const overallColor =
    overall_percentile >= 75 ? 'from-emerald-500 to-emerald-600' :
    overall_percentile >= 50 ? 'from-sky-500 to-sky-600' :
    overall_percentile >= 25 ? 'from-amber-500 to-amber-600' :
    'from-red-500 to-red-600';

  const overallLabel =
    overall_percentile >= 75 ? 'Top Quartile' :
    overall_percentile >= 50 ? 'Above Average' :
    overall_percentile >= 25 ? 'Below Average' :
    'Bottom Quartile';

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className={`bg-gradient-to-r ${overallColor} px-6 py-4`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-white/20 p-2 rounded-xl">
              <Users className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-white font-bold text-lg">Peer Benchmark</h3>
              <p className="text-white/80 text-sm capitalize">
                vs {area_type?.replace(/_/g, ' ')} kirana stores
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-4xl font-black text-white">P{overall_percentile}</div>
            <div className="text-white/80 text-sm font-medium">{overallLabel}</div>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Summary */}
        <p className="text-sm text-slate-600 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100">
          {peer_summary}
        </p>

        {/* Revenue Percentile */}
        <div className="flex items-center gap-4 p-4 bg-indigo-50 rounded-xl border border-indigo-100">
          <Award className="w-8 h-8 text-indigo-600 shrink-0" />
          <div>
            <div className="text-sm font-bold text-indigo-900">Revenue Rank: P{revenue_percentile}</div>
            <div className="text-xs text-indigo-700">
              Estimated revenue places this store at the {revenue_percentile >= 50 ? 'upper' : 'lower'} half of {area_type?.replace(/_/g, ' ')} peers
            </div>
          </div>
        </div>

        {/* Signal Breakdown */}
        <div>
          <h4 className="text-xs font-bold uppercase text-slate-500 tracking-wider mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4" /> Signal-Level Comparison
          </h4>
          {signal_percentiles && Object.entries(signal_percentiles).map(([key, pct]) => (
            <PercentileBar
              key={key}
              label={SIGNAL_LABELS[key] || key.replace(/_/g, ' ')}
              percentile={pct}
            />
          ))}
        </div>

        {/* Strengths & Weaknesses */}
        {((strengths_vs_peers?.length > 0) || (weaknesses_vs_peers?.length > 0)) && (
          <div className="grid md:grid-cols-2 gap-4">
            {strengths_vs_peers?.length > 0 && (
              <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-100">
                <h4 className="text-xs font-bold uppercase text-emerald-700 mb-3 flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5" /> Strengths vs Peers
                </h4>
                <ul className="space-y-2">
                  {strengths_vs_peers.map((s, i) => (
                    <li key={i} className="text-xs text-emerald-800 font-medium border-l-2 border-emerald-300 pl-2">{s}</li>
                  ))}
                </ul>
              </div>
            )}
            {weaknesses_vs_peers?.length > 0 && (
              <div className="bg-amber-50 p-4 rounded-xl border border-amber-100">
                <h4 className="text-xs font-bold uppercase text-amber-700 mb-3 flex items-center gap-1.5">
                  <TrendingDown className="w-3.5 h-3.5" /> Weakness vs Peers
                </h4>
                <ul className="space-y-2">
                  {weaknesses_vs_peers.map((w, i) => (
                    <li key={i} className="text-xs text-amber-800 font-medium border-l-2 border-amber-300 pl-2">{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
