export default function RiskHeatmap({ data = {} }) {
  const entries = Object.entries(data);
  if (!entries.length) {
    return <div className="text-sm text-slate-400">No geography data available.</div>;
  }

  const max = Math.max(...entries.map(([, value]) => value), 1);

  return (
    <div className="grid sm:grid-cols-2 gap-3">
      {entries.map(([label, value]) => (
        <div key={label} className="rounded-xl border border-slate-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold text-slate-800">{label}</div>
            <div className="text-sm font-black text-primary-700">{value}</div>
          </div>
          <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
            <div className="h-full rounded-full bg-gradient-to-r from-primary-400 to-primary-700" style={{ width: `${(value / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
