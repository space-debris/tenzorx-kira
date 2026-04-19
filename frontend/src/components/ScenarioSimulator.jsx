import { useState } from 'react';
import { Activity, ShieldAlert, ArrowRight, TrendingDown, Loader2 } from 'lucide-react';

export default function ScenarioSimulator({ currentRevenue, onSimulate }) {
  const [scenario, setScenario] = useState('monsoon_shock');
  const [result, setResult] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const handleSimulate = async () => {
    if (onSimulate) {
      setIsSimulating(true);
      try {
        const simResult = await onSimulate(scenario);
        setResult(simResult);
      } finally {
        setIsSimulating(false);
      }
    }
  };

  const formatCurrency = (val) => {
    if (val == null) return 'N/A';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">

      {/* Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary-600 flex-shrink-0" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 leading-none">
            Stress Testing Simulator
          </h2>
        </div>
        <p className="text-xs text-slate-700 font-medium leading-tight">
          Simulate macroeconomic shocks on borrower revenue.
        </p>
      </div>

      {/* Controls - STACKED */}
      <div className="space-y-2">

        {/* Full-width Dropdown */}
        <div className="relative">
          <select
            className="w-full h-[44px] appearance-none border border-slate-300 rounded-lg pl-3 pr-10 text-sm bg-slate-50 text-slate-700 
            focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 
            transition-colors cursor-pointer"
            value={scenario}
            onChange={(e) => {
              setScenario(e.target.value);
              setResult(null);
            }}
          >
            <option value="monsoon_shock">Monsoon Shock (-30%)</option>
            <option value="locality_demand_shock">Locality Demand Shock (-15%)</option>
            <option value="supply_chain_disruption">Supply Chain Disruption (-10%)</option>
          </select>

          {/* Arrow */}
          <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-500">
            <svg className="fill-current h-4 w-4" viewBox="0 0 20 20">
              <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z" />
            </svg>
          </div>
        </div>

        {/* Full-width Button (Next Line) */}
        <button
          onClick={handleSimulate}
          disabled={isSimulating}
          className="w-full h-[44px] flex items-center justify-center bg-slate-900 hover:bg-slate-800 
          disabled:bg-slate-400 text-white font-medium rounded-lg text-sm transition-all active:scale-[0.98]"
        >
          {isSimulating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            'Run Simulation'
          )}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="mt-1 overflow-hidden rounded-xl border border-slate-200 bg-slate-50 animate-in fade-in slide-in-from-bottom-2 duration-300">

          {/* Result Header */}
          <div className="border-b border-slate-200 bg-slate-100/50 px-3 py-2">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-700 leading-none">
              <ShieldAlert className="h-4 w-4 text-rose-500" />
              Scenario Impact Analysis
            </div>
          </div>

          <div className="p-3 space-y-3">

            {/* Before / After */}
            <div className="grid grid-cols-3 items-center gap-2">
              <div>
                <p className="text-xs text-slate-500">Base Revenue</p>
                <p className="text-sm font-semibold text-slate-700">
                  {formatCurrency(currentRevenue)}
                </p>
              </div>

              <div className="flex justify-center">
                <ArrowRight className="h-4 w-4 text-slate-300" />
              </div>

              <div className="text-right">
                <p className="text-xs text-slate-500">Stressed Revenue</p>
                <p className="text-lg font-bold text-slate-900">
                  {formatCurrency(result.stressed_revenue)}
                </p>
              </div>
            </div>

            {/* Impact Bar */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-xs font-semibold">
                <span className="text-slate-600">Revenue Retained</span>
                <span className="text-rose-600 flex items-center gap-1">
                  <TrendingDown className="h-3 w-3" />
                  {result.impact_percentage.toFixed(1)}% Drop
                </span>
              </div>

              <div className="h-2 w-full overflow-hidden rounded-full bg-rose-100">
                <div
                  className="h-full rounded-full bg-slate-900 transition-all duration-700 ease-out"
                  style={{ width: `${100 - result.impact_percentage}%` }}
                />
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}