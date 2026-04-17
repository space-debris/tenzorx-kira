/**
 * KIRA — Lender Dashboard Page
 *
 * Main landing page for authenticated lenders.
 * Shows KPIs, cases by status chart, recent cases, and open alerts.
 * All data fetched from GET /platform/orgs/{org_id}/dashboard.
 *
 * Owner: Frontend Lead
 * Phase: 9.2
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { getOrganizationDashboard } from '../api/kiraApi';
import {
  Users, Briefcase, AlertTriangle, ShieldAlert,
  Link2, ArrowRight, Loader2, TrendingUp, ChevronRight
} from 'lucide-react';
import { PieChart, Pie, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const STATUS_COLORS = {
  draft: '#94a3b8',
  submitted: '#3b82f6',
  under_review: '#a855f7',
  approved: '#10b981',
  disbursed: '#06b6d4',
  monitoring: '#f59e0b',
  restructured: '#ef4444',
  closed: '#6b7280',
};

const STATUS_LABELS = {
  draft: 'Draft',
  submitted: 'Submitted',
  under_review: 'Under Review',
  approved: 'Approved',
  disbursed: 'Disbursed',
  monitoring: 'Monitoring',
  restructured: 'Restructured',
  closed: 'Closed',
};

const RISK_BAND_COLORS = {
  LOW: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  MEDIUM: 'bg-blue-100 text-blue-700 border-blue-200',
  HIGH: 'bg-amber-100 text-amber-700 border-amber-200',
  VERY_HIGH: 'bg-red-100 text-red-700 border-red-200',
};

function formatCurrency(num) {
  if (num == null) return '—';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(num);
}

export default function Dashboard() {
  const { org, user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!org?.id) return;

    async function load() {
      try {
        setLoading(true);
        const res = await getOrganizationDashboard(org.id);
        setData(res.data);
      } catch (err) {
        console.error('Dashboard load error:', err);
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [org?.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <p className="text-slate-600 font-medium">{error}</p>
      </div>
    );
  }

  const summary = data?.summary || {};
  const recentCases = data?.recent_cases || [];
  const openAlerts = data?.open_alerts || [];

  // Build chart data from cases_by_status
  const chartData = Object.entries(summary.cases_by_status || {})
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({
      name: STATUS_LABELS[status] || status,
      value: count,
      fill: STATUS_COLORS[status] || '#94a3b8',
    }));

  const totalCasesForChart = chartData.reduce((acc, item) => acc + item.value, 0);
  const statusBreakdown = chartData
    .map((item) => ({
      ...item,
      percent: totalCasesForChart > 0 ? Math.round((item.value / totalCasesForChart) * 100) : 0,
    }))
    .sort((a, b) => b.value - a.value);

  const kpiCards = [
    { label: 'Total Kiranas', value: summary.total_kiranas ?? 0, icon: Users, color: 'text-primary-600', bg: 'bg-primary-50' },
    { label: 'Total Cases', value: summary.total_cases ?? 0, icon: Briefcase, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Linked Assessments', value: summary.linked_assessments ?? 0, icon: Link2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Open Alerts', value: summary.open_alerts ?? 0, icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50' },
    { label: 'Flagged', value: summary.flagged_assessments ?? 0, icon: ShieldAlert, color: 'text-red-600', bg: 'bg-red-50' },
  ];

  return (
    <div className="animate-fade-in p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800">Dashboard</h1>
        <p className="text-slate-500 mt-1">Welcome back, {user?.full_name?.split(' ')[0]}. Here's your portfolio overview.</p>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5 mb-8">
        {kpiCards.map((kpi, i) => (
          <div key={i} className="bg-white border border-slate-200/60 rounded-2xl p-5 shadow-sm hover:shadow-lg transition-shadow duration-300">
            <div className="flex items-center justify-between">
              <div className="text-2xl font-bold text-slate-800">{kpi.value}</div>
              <div className={`w-11 h-11 rounded-full ${kpi.bg} ${kpi.color} flex items-center justify-center`}>
                <kpi.icon className="w-5 h-5" />
              </div>
            </div>
            <div className="text-sm font-semibold text-slate-500 mt-2">{kpi.label}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-8">
        {/* Cases by Status Chart */}
        <div className="lg:col-span-2 bg-white border border-slate-200/60 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-semibold text-slate-800 flex items-center">
              <TrendingUp className="w-5 h-5 text-primary-500 mr-2" /> Cases by Status
            </h2>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-primary-50 text-primary-700 border border-primary-100">
              {totalCasesForChart} total
            </span>
          </div>

          {chartData.length > 0 ? (
            <div className="grid md:grid-cols-2 gap-6 items-center">
              <div className="relative h-70">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusBreakdown}
                      cx="50%"
                      cy="50%"
                      innerRadius={72}
                      outerRadius={108}
                      paddingAngle={2}
                      stroke="#ffffff"
                      strokeWidth={3}
                      dataKey="value"
                      nameKey="name"
                    >
                      {statusBreakdown.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value, name, ctx) => [`${value} (${ctx?.payload?.percent ?? 0}%)`, name]}
                      contentStyle={{
                        borderRadius: '12px',
                        border: '1px solid #e2e8f0',
                        boxShadow: '0 8px 24px -10px rgb(15 23 42 / 0.35)',
                        fontSize: '13px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>

                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <div className="text-3xl font-black text-slate-900 leading-none">{totalCasesForChart}</div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mt-1">Cases</div>
                </div>
              </div>

              <div className="space-y-3">
                {statusBreakdown.map((item) => (
                  <div key={item.name} className="p-3 rounded-xl border border-slate-200 bg-slate-50/50">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <div className="flex items-center gap-2 font-semibold text-slate-700">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.fill }} />
                        {item.name}
                      </div>
                      <div className="text-slate-500 font-semibold">{item.value} ({item.percent}%)</div>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${item.percent}%`, backgroundColor: item.fill }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="min-h-70 flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-300 rounded-xl bg-slate-50/50">
              <TrendingUp className="w-8 h-8 mb-2 text-slate-300" />
              <p className="text-sm font-medium">No case data available yet</p>
            </div>
          )}
        </div>

        {/* Open Alerts */}
        <div className="bg-white border border-slate-200/60 rounded-2xl p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-800 mb-4 flex items-center">
            <AlertTriangle className="w-5 h-5 text-amber-500 mr-2" /> Open Alerts
          </h2>
          {openAlerts.length > 0 ? (
            <div className="alerts-scroll space-y-4 max-h-85 overflow-y-auto pr-1">
              {openAlerts.map((alert) => (
                <div key={alert.id} className={`p-4 rounded-xl border ${
                  alert.severity === 'critical' ? 'bg-red-50 border-red-200' :
                  alert.severity === 'warning' ? 'bg-amber-50 border-amber-200' :
                  'bg-blue-50 border-blue-200'
                }`}>
                  <p className={`font-bold text-sm ${
                    alert.severity === 'critical' ? 'text-red-800' :
                    alert.severity === 'warning' ? 'text-amber-800' :
                    'text-blue-800'
                  }`}>{alert.title}</p>
                  <p className={`text-xs mt-1 ${
                    alert.severity === 'critical' ? 'text-red-700' :
                    alert.severity === 'warning' ? 'text-amber-700' :
                    'text-blue-700'
                  }`}>{alert.description}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-500">
              <AlertTriangle className="w-10 h-10 mb-2 opacity-50" />
              <span>No open alerts</span>
            </div>
          )}
        </div>
      </div>

      {/* Recent Cases Table */}
      <div className="bg-white border border-slate-200/60 rounded-2xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200/80 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800 flex items-center">
            <Briefcase className="w-5 h-5 text-primary-500 mr-2" /> Recent Cases
          </h2>
          <Link to="/app/cases" className="text-sm font-semibold text-primary-600 hover:text-primary-700 flex items-center gap-1 transition-colors">
            View All <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
        {recentCases.length > 0 ? (
          <div className="alerts-scroll overflow-auto pr-1" style={{ maxHeight: '360px' }}>
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Case ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Risk</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Loan Range</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Notes</th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/80">
                {recentCases.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-slate-700">
                      {c.id?.substring(0, 8)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold" style={{ backgroundColor: `${STATUS_COLORS[c.status]}20`, color: STATUS_COLORS[c.status] }}>
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: STATUS_COLORS[c.status] }} />
                        {STATUS_LABELS[c.status] || c.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {c.latest_risk_band ? (
                        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${RISK_BAND_COLORS[c.latest_risk_band] || 'bg-slate-100 text-slate-600'}`}>
                          {c.latest_risk_band}
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-slate-800">
                      {c.latest_loan_range
                        ? `${formatCurrency(c.latest_loan_range.low)} – ${formatCurrency(c.latest_loan_range.high)}`
                        : '—'}
                    </td>
                    <td className="px-6 py-4 max-w-xs truncate text-slate-500">{c.notes || '—'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <Link to={`/app/cases/${c.id}`} className="text-primary-600 hover:text-primary-700 font-semibold flex items-center gap-1 justify-end">
                        View <ArrowRight className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-20 text-slate-500">No cases yet. Create one to get started.</div>
        )}
      </div>
    </div>
  );
}
