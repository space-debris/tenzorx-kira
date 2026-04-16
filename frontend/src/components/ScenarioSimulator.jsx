import { useState } from 'react';
import { Activity } from 'lucide-react';

export default function ScenarioSimulator({ currentRevenue, onSimulate }) {
  const [scenario, setScenario] = useState('monsoon_shock');
  const [result, setResult] = useState(null);

  const handleSimulate = async () => {
    if (onSimulate) {
      const simResult = await onSimulate(scenario);
      setResult(simResult);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Activity className="w-5 h-5 text-primary-600" />
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Stress Testing Simulator</h2>
      </div>
      <p className="text-sm text-slate-500">Test how the borrower might perform under different macroeconomic shocks.</p>
      
      <div className="flex flex-col gap-3">
        <select 
          className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white"
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
        >
          <option value="monsoon_shock">Monsoon Shock (30% drop)</option>
          <option value="locality_demand_shock">Locality Demand Shock (15% drop)</option>
          <option value="supply_chain_disruption">Supply Chain Disruption (10% drop)</option>
        </select>
        <button 
          onClick={handleSimulate}
          className="bg-primary-600 hover:bg-primary-700 text-white font-semibold py-2 px-4 rounded-lg text-sm transition"
        >
          Simulate
        </button>
      </div>

      {result && (
        <div className="mt-4 p-4 rounded-lg border border-amber-200 bg-amber-50">
          <div className="text-sm font-semibold text-amber-800 mb-1">Scenario Result</div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-amber-700">Projected Revenue:</span>
            <span className="font-bold text-amber-900">₹{result.stressed_revenue.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
          </div>
          <div className="w-full bg-amber-200 rounded-full h-1.5 mt-2">
            <div className="bg-amber-600 h-1.5 rounded-full" style={{ width: `${100 - result.impact_percentage}%` }}></div>
          </div>
          <div className="text-xs text-right text-amber-700 mt-1">-{result.impact_percentage.toFixed(0)}% Impact</div>
        </div>
      )}
    </div>
  );
}
