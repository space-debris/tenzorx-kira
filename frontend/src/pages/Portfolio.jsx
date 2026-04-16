import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { getOrganizationPortfolio } from '../api/kiraApi';
import { useAuth } from '../context/useAuth';
import PortfolioKpiStrip from '../components/PortfolioKpiStrip';
import LoanTable from '../components/LoanTable';
import RiskHeatmap from '../components/RiskHeatmap';
import CohortChart from '../components/CohortChart';
import { INDIA_STATES_DISTRICTS } from '../utils/indiaGeo';

export default function Portfolio() {
  const { org } = useAuth();
  const [data, setData] = useState(null);
  const [loadLimit, setLoadLimit] = useState(10);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    state: '',
    district: '',
    status: '',
    risk: '',
    search: '',
  });

  useEffect(() => {
    if (!org?.id) return;

    async function load() {
      try {
        setLoading(true);
        const res = await getOrganizationPortfolio(org.id);
        setData(res.data);
        setError(null);
      } catch (err) {
        console.error('Failed to load portfolio', err);
        setError('Failed to load portfolio metrics.');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [org?.id]);

  const loans = useMemo(() => {
    const allLoans = data?.loans || [];
    const query = filters.search.toLowerCase();
    return allLoans.filter((loan) => {
      const matchesSearch = !query
        || loan.store_name?.toLowerCase().includes(query)
        || loan.borrower_name?.toLowerCase().includes(query)
        || loan.pin_code?.includes(query);
      const matchesState = !filters.state || loan.state === filters.state;
      const matchesDistrict = !filters.district || loan.district === filters.district;
      const matchesStatus = !filters.status || loan.status === filters.status;
      const matchesRisk = !filters.risk || loan.risk_band === filters.risk;
      return matchesSearch && matchesState && matchesDistrict && matchesStatus && matchesRisk;
    });
  }, [data?.loans, filters]);

  const states = Object.keys(INDIA_STATES_DISTRICTS);
  const districts = filters.state ? INDIA_STATES_DISTRICTS[filters.state] : [];

  if (loading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-primary-500 animate-spin" /></div>;
  }

  if (error) {
    return <div className="text-center py-20"><AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" /><p className="text-slate-600 font-medium">{error}</p></div>;
  }

  return (
    <div className="animate-fade-in max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900">Portfolio</h1>
        <p className="text-slate-500 font-medium mt-1">Risk concentration, drilldowns, and cohort performance from one command center.</p>
      </div>

      <PortfolioKpiStrip metrics={data?.metrics || []} />

      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="grid lg:grid-cols-5 gap-3">
          <input
            value={filters.search}
            onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            placeholder="Search borrower or store"
            className="border border-slate-300 rounded-lg px-3 py-2.5 text-sm outline-none focus:border-primary-500"
          />
          <select value={filters.state} onChange={(event) => setFilters((current) => ({ ...current, state: event.target.value, district: '' }))} className="border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white outline-none focus:border-indigo-500">
            <option value="">All states</option>
            {states.map((state) => <option key={state} value={state}>{state}</option>)}
          </select>
          <select value={filters.district} onChange={(event) => setFilters((current) => ({ ...current, district: event.target.value }))} className="border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white outline-none focus:border-indigo-500" disabled={!filters.state}>
            <option value="">All districts</option>
            {districts.map((district) => <option key={district} value={district}>{district}</option>)}
          </select>
          <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))} className="border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white">
            <option value="">All statuses</option>
            <option value="approved">Approved</option>
            <option value="disbursed">Disbursed</option>
            <option value="monitoring">Monitoring</option>
            <option value="restructured">Restructured</option>
            <option value="closed">Closed</option>
          </select>
          <select value={filters.risk} onChange={(event) => setFilters((current) => ({ ...current, risk: event.target.value }))} className="border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-white">
            <option value="">All risk tiers</option>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="VERY_HIGH">Very High</option>
          </select>
        </div>
      </div>

      <div className="grid xl:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4">Risk By Geography</h2>
          <RiskHeatmap data={data?.geography_distribution || {}} />
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4">Cohort Trend</h2>
          <CohortChart cohorts={data?.cohorts || []} />
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4">Loan Drilldown</h2>
        <LoanTable loans={loans.slice(0, loadLimit)} />
        {loadLimit < loans.length && (
          <div className="mt-6 text-center">
            <button 
              onClick={() => setLoadLimit(prev => prev + 10)}
              className="px-6 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-sm transition"
            >
              Load More ({loans.length - loadLimit} remaining)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
