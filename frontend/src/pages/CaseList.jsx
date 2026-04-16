/**
 * KIRA - Case List Page
 *
 * Table of all assessment cases with status/risk filters.
 * Fetches from GET /platform/orgs/{org_id}/cases.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Briefcase, Search, ArrowRight, Loader2, AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import { listOrganizationCases, listOrganizationKiranas } from '../api/kiraApi';
import { formatCurrency, getCaseNextAction } from '../utils/caseUtils';

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

export default function CaseList() {
  const { org } = useAuth();
  const [cases, setCases] = useState([]);
  const [kiranaMap, setKiranaMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterRisk, setFilterRisk] = useState('');

  useEffect(() => {
    if (!org?.id) return;

    async function load() {
      try {
        setLoading(true);
        const [casesRes, kiranasRes] = await Promise.all([
          listOrganizationCases(org.id),
          listOrganizationKiranas(org.id),
        ]);

        setCases(casesRes.data || []);

        const nextMap = {};
        (kiranasRes.data || []).forEach((kirana) => {
          nextMap[kirana.id] = kirana;
        });
        setKiranaMap(nextMap);
      } catch (err) {
        console.error('Failed to load cases:', err);
        setError('Failed to load cases');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [org?.id]);

  const filtered = cases.filter((caseItem) => {
    const kirana = kiranaMap[caseItem.kirana_id];
    const q = searchQuery.toLowerCase();
    const matchesSearch = !q
      || kirana?.store_name?.toLowerCase().includes(q)
      || kirana?.owner_name?.toLowerCase().includes(q)
      || kirana?.location?.district?.toLowerCase().includes(q)
      || kirana?.location?.pin_code?.includes(q)
      || caseItem.id?.toLowerCase().includes(q)
      || caseItem.notes?.toLowerCase().includes(q);
    const matchesStatus = !filterStatus || caseItem.status === filterStatus;
    const matchesRisk = !filterRisk || caseItem.latest_risk_band === filterRisk;
    return matchesSearch && matchesStatus && matchesRisk;
  });

  if (loading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-primary-500 animate-spin" /></div>;
  }

  if (error) {
    return <div className="text-center py-20"><AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" /><p className="text-slate-600 font-medium">{error}</p></div>;
  }

  return (
    <div className="animate-fade-in max-w-7xl mx-auto">
      <div className="mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-primary-600" /> Cases
          </h1>
          <p className="text-slate-500 font-medium mt-1">{cases.length} total case{cases.length !== 1 ? 's' : ''}</p>
        </div>
        <Link to="/app/new-case" className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-semibold text-sm transition-all shadow-sm flex items-center gap-1.5">
          + New Case
        </Link>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search by store name, owner, district, pin code, or case ID..."
            className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-xl outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-100 transition-all text-sm"
          />
        </div>
        <select
          value={filterStatus}
          onChange={(event) => setFilterStatus(event.target.value)}
          className="appearance-none px-4 py-2.5 border border-slate-300 bg-white rounded-xl outline-none focus:border-primary-500 text-sm font-medium text-slate-700 min-w-[150px]"
        >
          <option value="">All Statuses</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <select
          value={filterRisk}
          onChange={(event) => setFilterRisk(event.target.value)}
          className="appearance-none px-4 py-2.5 border border-slate-300 bg-white rounded-xl outline-none focus:border-primary-500 text-sm font-medium text-slate-700 min-w-[130px]"
        >
          <option value="">All Risk</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="VERY_HIGH">Very High</option>
        </select>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {filtered.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-left">
                  <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Store</th>
                  <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Risk</th>
                  <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Loan Range</th>
                  <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Next Action</th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((caseItem) => {
                  const kirana = kiranaMap[caseItem.kirana_id];
                  return (
                    <tr key={caseItem.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-900 text-sm">{kirana?.store_name || 'Unknown'}</div>
                        <div className="text-xs text-slate-400">{kirana?.owner_name}</div>
                        <div className="text-xs text-slate-400 mt-1">
                          {[kirana?.location?.district, kirana?.location?.pin_code].filter(Boolean).join(' • ')}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold capitalize" style={{ backgroundColor: `${STATUS_COLORS[caseItem.status]}15`, color: STATUS_COLORS[caseItem.status] }}>
                          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: STATUS_COLORS[caseItem.status] }} />
                          {STATUS_LABELS[caseItem.status] || caseItem.status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {caseItem.latest_risk_band ? (
                          <span className={`px-2 py-0.5 rounded text-xs font-bold border ${RISK_BAND_COLORS[caseItem.latest_risk_band] || 'bg-slate-100 text-slate-600'}`}>
                            {caseItem.latest_risk_band}
                          </span>
                        ) : <span className="text-xs text-slate-400">-</span>}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-slate-700">
                        {caseItem.latest_loan_range ? (
                          (caseItem.latest_loan_range.low === 0 && caseItem.latest_loan_range.high === 0) ? (
                            <span className="text-red-700 font-bold bg-red-50 px-2 py-1 rounded text-xs border border-red-200">Not Recommended</span>
                          ) : (
                            `${formatCurrency(caseItem.latest_loan_range.low)} - ${formatCurrency(caseItem.latest_loan_range.high)}`
                          )
                        ) : '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600 max-w-xs">
                        <div className="font-medium">{getCaseNextAction(caseItem)}</div>
                        {caseItem.notes && <div className="text-xs text-slate-400 truncate mt-1">{caseItem.notes}</div>}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link to={`/app/cases/${caseItem.id}`} className="text-primary-600 hover:text-primary-700 text-sm font-semibold flex items-center gap-1 justify-end">
                          View <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-16 text-slate-400 text-sm">
            <Briefcase className="w-10 h-10 mx-auto mb-3 opacity-30" />
            {cases.length === 0 ? 'No cases yet. Create your first case.' : 'No cases match your current filters.'}
          </div>
        )}
      </div>
    </div>
  );
}
