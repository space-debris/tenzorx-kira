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
    <div className="h-full bg-white border border-slate-200 rounded-xl p-3 shadow-sm flex flex-col">
      <div className="flex justify-between items-center mb-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">Liquidity Forecast</h2>
        <div className={`flex items-center gap-1 text-[10px] font-bold ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
          {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {isPositive ? '+' : ''}₹{formatINR(forecast.daily_net_velocity)} / day
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-2 flex-1 items-start">
        <div className="rounded-lg bg-emerald-50 p-2 border border-emerald-100">
          <div className="text-[10px] font-bold text-emerald-700 mb-0.5">30-Day</div>
          <div className="text-sm font-black text-slate-900">₹{formatINR(forecast.forecast_30_days)}</div>
          {forecast.liquidity_gap_30_days > 0 && (
            <div className="text-[10px] text-red-600 mt-0.5 font-bold">Gap: ₹{formatINR(forecast.liquidity_gap_30_days)}</div>
          )}
        </div>
        <div className="rounded-lg bg-blue-50 p-2 border border-blue-100">
          <div className="text-[10px] font-bold text-blue-700 mb-0.5">90-Day</div>
          <div className="text-sm font-black text-slate-900">₹{formatINR(forecast.forecast_90_days)}</div>
          {forecast.liquidity_gap_90_days > 0 && (
            <div className="text-[10px] text-red-600 mt-0.5 font-bold">Gap: ₹{formatINR(forecast.liquidity_gap_90_days)}</div>
          )}
        </div>
        <div className="rounded-lg bg-purple-50 p-2 border border-purple-100">
          <div className="text-[10px] font-bold text-purple-700 mb-0.5">180-Day</div>
          <div className="text-sm font-black text-slate-900">₹{formatINR(forecast.forecast_90_days + (forecast.daily_net_velocity * 90))}</div>
          <div className="text-[9px] text-slate-500">Projected</div>
        </div>
      </div>

      <div className="mt-2 pt-1 border-t border-slate-100">
        <span className="text-[9px] text-slate-400 italic leading-tight block">
          * Updated daily. 95% confidence interval under normal conditions.
        </span>
      </div>
    </div>
  );
}
