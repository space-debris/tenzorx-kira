import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

const MOCK_COHORT_DATA = [
  { cohort: 'Delhi NCR', cases: 42 },
  { cohort: 'North Delhi', cases: 28 },
  { cohort: 'South Delhi', cases: 24 },
  { cohort: 'East Delhi', cases: 21 },
  { cohort: 'West Delhi', cases: 18 },
  { cohort: 'Gurugram', cases: 17 },
  { cohort: 'Noida', cases: 16 },
  { cohort: 'Faridabad', cases: 14 },
  { cohort: 'Ghaziabad', cases: 13 },
  { cohort: 'Greater Noida', cases: 11 },
  { cohort: 'Meerut', cases: 9 },
  { cohort: 'Sonipat', cases: 7 },
];

export default function CohortChart({ cohorts = [] }) {
  // Use real data if available, otherwise use mock data
  const data = cohorts.length > 0 ? cohorts : MOCK_COHORT_DATA;
  
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} barCategoryGap="18%" margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="cohort" tick={{ fontSize: 12, fill: '#64748b', fontWeight: 600 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: '#64748b', fontWeight: 600 }} axisLine={false} tickLine={false} />
        <Tooltip
          cursor={{ fill: 'rgba(30, 41, 59, 0.04)' }}
          contentStyle={{ borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 10px 28px -14px rgba(15,23,42,0.45)' }}
        />
        <Bar dataKey="cases" fill="#2563eb" radius={[10, 10, 4, 4]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
