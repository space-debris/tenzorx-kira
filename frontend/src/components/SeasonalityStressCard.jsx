/**
 * KIRA — Seasonality & Stress Card
 *
 * 12-month forecast chart + stress scenario table.
 */

import { CloudRain, TrendingUp, TrendingDown, AlertTriangle, Zap, Sun } from 'lucide-react';

const SEVERITY_STYLES = {
  high: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-100 text-red-800' },
  medium: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800' },
  positive: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', badge: 'bg-emerald-100 text-emerald-800' },
  unknown: { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-700', badge: 'bg-slate-100 text-slate-800' },
};

const CATEGORY_ICONS = {
  weather: CloudRain,
  demand: TrendingDown,
  supply: AlertTriangle,
  competition: Zap,
  seasonal: Sun,
  growth: TrendingUp,
  macro: AlertTriangle,
};

function formatCurrency(n) {
  if (n == null) return '₹0';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
}

function MiniBar({ value, max, color = 'bg-indigo-500' }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
      <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function SeasonalityStressCard({ seasonalityForecast, stressScenarios }) {
  if (!seasonalityForecast && (!stressScenarios || stressScenarios.length === 0)) return null;

  const forecast = seasonalityForecast?.monthly_forecast || [];
  const peak = seasonalityForecast?.peak_month;
  const trough = seasonalityForecast?.trough_month;
  const peakRev = seasonalityForecast?.peak_revenue || 0;
  const troughRev = seasonalityForecast?.trough_revenue || 0;
  const maxRev = Math.max(...forecast.map(m => m.forecast_revenue || 0), 1);
  const volatility = seasonalityForecast?.volatility_index || 0;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      <div className="bg-gradient-to-r from-violet-600 to-purple-600 px-6 py-4">
        <h3 className="text-white font-bold text-lg flex items-center gap-2">
          <Sun className="w-5 h-5" /> Seasonality & Stress Analysis
        </h3>
        <p className="text-white/70 text-sm">12-month forecast with scenario simulation</p>
      </div>

      <div className="p-6 space-y-6">
        {/* 12-Month Forecast */}
        {forecast.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase text-slate-500 tracking-wider mb-4">Monthly Revenue Forecast</h4>
            <div className="grid grid-cols-12 gap-1 items-end h-32 mb-2">
              {forecast.map((m) => {
                const pct = maxRev > 0 ? (m.forecast_revenue / maxRev) * 100 : 0;
                const isPeak = m.month === peak;
                const isTrough = m.month === trough;
                const barColor = isPeak ? 'bg-emerald-500' : isTrough ? 'bg-red-400' : 'bg-indigo-400';
                return (
                  <div key={m.month} className="flex flex-col items-center h-full justify-end group relative">
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-[10px] px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                      {formatCurrency(m.forecast_revenue)}
                    </div>
                    <div
                      className={`w-full rounded-t ${barColor} transition-all duration-500 min-h-[4px]`}
                      style={{ height: `${Math.max(4, pct)}%` }}
                    />
                  </div>
                );
              })}
            </div>
            <div className="grid grid-cols-12 gap-1">
              {forecast.map((m) => (
                <div key={m.month} className="text-[9px] text-slate-400 text-center font-medium">
                  {m.month.slice(0, 3)}
                </div>
              ))}
            </div>

            {/* Summary */}
            <div className="grid grid-cols-3 gap-3 mt-4">
              <div className="bg-emerald-50 p-3 rounded-xl border border-emerald-100 text-center">
                <div className="text-[10px] font-bold uppercase text-emerald-600">Peak</div>
                <div className="text-sm font-black text-emerald-800">{peak?.slice(0, 3)}</div>
                <div className="text-xs text-emerald-700">{formatCurrency(peakRev)}</div>
              </div>
              <div className="bg-red-50 p-3 rounded-xl border border-red-100 text-center">
                <div className="text-[10px] font-bold uppercase text-red-600">Trough</div>
                <div className="text-sm font-black text-red-800">{trough?.slice(0, 3)}</div>
                <div className="text-xs text-red-700">{formatCurrency(troughRev)}</div>
              </div>
              <div className="bg-violet-50 p-3 rounded-xl border border-violet-100 text-center">
                <div className="text-[10px] font-bold uppercase text-violet-600">Volatility</div>
                <div className="text-sm font-black text-violet-800">{(volatility * 100).toFixed(1)}%</div>
                <div className="text-xs text-violet-700">CoV index</div>
              </div>
            </div>
          </div>
        )}

        {/* Stress Scenarios */}
        {stressScenarios && stressScenarios.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase text-slate-500 tracking-wider mb-3">Stress Scenarios</h4>
            <div className="space-y-2">
              {stressScenarios.map((s, i) => {
                const style = SEVERITY_STYLES[s.severity] || SEVERITY_STYLES.unknown;
                const Icon = CATEGORY_ICONS[s.category] || AlertTriangle;
                const isNeg = s.impact_percentage > 0;
                return (
                  <div key={i} className={`${style.bg} ${style.border} border rounded-xl p-3 flex items-center gap-3`}>
                    <Icon className={`w-5 h-5 ${style.text} shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-slate-800">{s.label}</span>
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${style.badge}`}>
                          {isNeg ? `−${s.impact_percentage}%` : `+${Math.abs(s.impact_percentage)}%`}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 truncate">{s.description}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-xs font-bold text-slate-700">{formatCurrency(s.stressed_revenue)}</div>
                      <div className="text-[10px] text-slate-400">{s.duration_months}mo</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
