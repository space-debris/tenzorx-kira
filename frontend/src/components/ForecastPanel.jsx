import { TrendingDown, TrendingUp } from 'lucide-react';

const formatINR = (value) =>
  new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 0,
  }).format(Number.isFinite(value) ? value : 0);

export default function ForecastPanel({ forecast = null }) {
  if (!forecast) {
    return <div className="text-sm text-slate-400">Forecast data unavailable.</div>;
  }

  const isPositive = forecast.daily_net_velocity >= 0;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Liquidity Forecast</h2>
        <div className={`flex items-center gap-1 text-sm font-semibold ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
          {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          {isPositive ? '+' : ''}₹{formatINR(forecast.daily_net_velocity)} / day
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
        <div className="rounded-lg bg-slate-50 p-4 border border-slate-100 flex flex-col justify-center">
          <div className="text-sm font-semibold text-slate-500 mb-1">30-Day Outlook</div>
          <div className="text-2xl font-black text-slate-800">
            ₹{formatINR(forecast.forecast_30_days)}
          </div>
          {forecast.liquidity_gap_30_days > 0 && (
            <div className="text-sm text-red-500 mt-1 font-medium">Gap: ₹{formatINR(forecast.liquidity_gap_30_days)}</div>
          )}
        </div>
        <div className="rounded-lg bg-slate-50 p-4 border border-slate-100 flex flex-col justify-center">
          <div className="text-sm font-semibold text-slate-500 mb-1">90-Day Outlook</div>
          <div className="text-2xl font-black text-slate-800">
            ₹{formatINR(forecast.forecast_90_days)}
          </div>
          {forecast.liquidity_gap_90_days > 0 && (
            <div className="text-sm text-red-500 mt-1 font-medium">Gap: ₹{formatINR(forecast.liquidity_gap_90_days)}</div>
          )}
        </div>
        <div className="rounded-lg bg-slate-50 p-4 border border-slate-100 flex flex-col justify-center md:col-span-2">
          <div className="text-sm font-semibold text-slate-500 mb-1">180-Day Liquidity Buffer Estimate</div>
          <div className="text-2xl font-black text-slate-800 flex items-center gap-2">
            ₹{formatINR(forecast.forecast_90_days + (forecast.daily_net_velocity * 90))}
          </div>
          <div className="text-xs text-slate-400 mt-1">Based on projected steady state condition velocity without restructures.</div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-100">
        <span className="text-[11px] text-slate-400 italic block leading-relaxed">
          * Forecast is updated daily. Cash flow projections maintain a 95% confidence interval under normal conditions.
        </span>
      </div>
    </div>
  );
}
