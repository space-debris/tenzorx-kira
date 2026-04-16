import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

export default function CohortChart({ cohorts = [] }) {
  if (!cohorts.length) {
    return <div className="text-sm text-slate-400">No cohort trends available yet.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={cohorts}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="cohort" tick={{ fontSize: 12, fill: '#64748b' }} />
        <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
        <Tooltip />
        <Bar dataKey="cases" fill="#2563eb" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
