import { TrendingDown, TrendingUp } from 'lucide-react';

export default function ForecastPanel({ forecast = null }) {
  if (!forecast) {
    return <div className="text-sm text-slate-400">Forecast data unavailable.</div>;
  }

  const isPositive = forecast.daily_net_velocity >= 0;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Liquidity Forecast</h2>
        <div className={`flex items-center gap-1 text-sm font-semibold ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
          {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          {isPositive ? '+' : ''}₹{forecast.daily_net_velocity.toFixed(0)} / day
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="text-xs font-semibold text-slate-500 mb-1">30-Day Outlook</div>
          <div className="text-lg font-black text-slate-800">
            ₹{forecast.forecast_30_days.toFixed(0)}
          </div>
          {forecast.liquidity_gap_30_days > 0 && (
            <div className="text-xs text-red-500 mt-1 font-medium">Gap: ₹{forecast.liquidity_gap_30_days.toFixed(0)}</div>
          )}
        </div>
        <div className="rounded-lg bg-slate-50 p-3">
          <div className="text-xs font-semibold text-slate-500 mb-1">90-Day Outlook</div>
          <div className="text-lg font-black text-slate-800">
            ₹{forecast.forecast_90_days.toFixed(0)}
          </div>
          {forecast.liquidity_gap_90_days > 0 && (
            <div className="text-xs text-red-500 mt-1 font-medium">Gap: ₹{forecast.liquidity_gap_90_days.toFixed(0)}</div>
          )}
        </div>
      </div>
    </div>
  );
}
