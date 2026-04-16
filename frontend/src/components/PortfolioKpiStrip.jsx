export default function PortfolioKpiStrip({ metrics = [] }) {
  return (
    <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
      {metrics.map((metric) => (
        <div key={metric.label} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="text-xs uppercase tracking-wide font-bold text-slate-400">{metric.label}</div>
          <div className="text-2xl font-black text-slate-900 mt-2">{metric.value}</div>
          {metric.trend_label && <div className="text-xs text-slate-500 mt-2">{metric.trend_label}</div>}
        </div>
      ))}
    </div>
  );
}
