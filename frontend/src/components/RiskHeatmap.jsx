import { MapPin } from 'lucide-react';

const RISK_COLORS = {
  LOW: { bg: 'bg-emerald-500', text: 'text-emerald-800', light: 'bg-emerald-50' },
  MEDIUM: { bg: 'bg-amber-500', text: 'text-amber-800', light: 'bg-amber-50' },
  HIGH: { bg: 'bg-orange-500', text: 'text-orange-800', light: 'bg-orange-50' },
  VERY_HIGH: { bg: 'bg-red-500', text: 'text-red-800', light: 'bg-red-50' },
};

function formatCurrency(value) {
  if (value == null) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

export default function RiskHeatmap({ riskDistribution, exposureByRisk, geographicConcentration }) {
  return (
    <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-5">
        <MapPin className="w-5 h-5 text-indigo-600" />
        <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
          Risk Concentration
        </h2>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Risk Distribution */}
        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Risk Tier Distribution
          </div>

          {riskDistribution && (
            <div className="space-y-3">
              {[
                { band: 'LOW', count: riskDistribution.low },
                { band: 'MEDIUM', count: riskDistribution.medium },
                { band: 'HIGH', count: riskDistribution.high },
                { band: 'VERY_HIGH', count: riskDistribution.very_high },
              ].map(({ band, count }) => {
                const total =
                  (riskDistribution.low || 0) +
                  (riskDistribution.medium || 0) +
                  (riskDistribution.high || 0) +
                  (riskDistribution.very_high || 0);
                const pct = total > 0 ? (count / total) * 100 : 0;
                const colors = RISK_COLORS[band] || RISK_COLORS.MEDIUM;
                const exposure = exposureByRisk?.[band] || 0;

                return (
                  <div key={band}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${colors.bg}`} />
                        <span className="text-sm font-semibold text-slate-700">
                          {band.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span>{count} loans</span>
                        <span className="font-bold">{pct.toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="flex h-2.5 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className={`${colors.bg} rounded-full transition-all duration-500`}
                        style={{ width: `${Math.max(pct, 2)}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      Exposure: {formatCurrency(exposure)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Geographic Concentration */}
        <div>
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Geographic Spread
          </div>

          {geographicConcentration?.by_state &&
          Object.keys(geographicConcentration.by_state).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(geographicConcentration.by_state)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 8)
                .map(([state, count]) => {
                  const maxCount = Math.max(
                    ...Object.values(geographicConcentration.by_state)
                  );
                  const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;

                  return (
                    <div key={state} className="flex items-center gap-3">
                      <span className="text-sm text-slate-700 font-medium w-28 truncate">
                        {state}
                      </span>
                      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className="h-full bg-indigo-400 rounded-full transition-all duration-500"
                          style={{ width: `${Math.max(pct, 4)}%` }}
                        />
                      </div>
                      <span className="text-xs font-bold text-slate-600 w-8 text-right">
                        {count}
                      </span>
                    </div>
                  );
                })}
            </div>
          ) : (
            <p className="text-sm text-slate-400">No geographic data available.</p>
          )}

          {geographicConcentration?.by_district &&
            Object.keys(geographicConcentration.by_district).length > 0 && (
              <div className="mt-4">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Top Districts
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(geographicConcentration.by_district)
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 8)
                    .map(([district, count]) => (
                      <span
                        key={district}
                        className="px-2 py-1 rounded-full bg-slate-100 border border-slate-200 text-[10px] font-semibold text-slate-600"
                      >
                        {district} ({count})
                      </span>
                    ))}
                </div>
              </div>
            )}
        </div>
      </div>
    </section>
  );
}
