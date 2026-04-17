export default function RiskHeatmap({ data = {} }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    return <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500 text-center">No geography data available.</div>;
  }

  const max = Math.max(...entries.map(([, value]) => value), 1);

  return (
    <div className="grid sm:grid-cols-2 gap-3">
      {entries.map(([label, value], index) => {
        const ratio = (value / max) * 100;
        const tone = ratio >= 75
          ? 'bg-rose-50 text-rose-700 border-rose-200'
          : ratio >= 45
            ? 'bg-amber-50 text-amber-700 border-amber-200'
            : 'bg-emerald-50 text-emerald-700 border-emerald-200';

        return (
        <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="font-semibold text-slate-800">{label}</div>
              <div className="text-xs text-slate-400 mt-0.5">Rank #{index + 1}</div>
            </div>
            <div className={`rounded-full border px-2.5 py-1 text-xs font-bold ${tone}`}>
              {value}
            </div>
          </div>
          <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
            <div className="h-full rounded-full bg-linear-to-r from-primary-300 via-primary-500 to-primary-700" style={{ width: `${ratio}%` }} />
          </div>
          <div className="mt-2 text-xs font-semibold text-slate-500">{Math.round(ratio)}% of peak concentration</div>
        </div>
      )})}
    </div>
  );
}
