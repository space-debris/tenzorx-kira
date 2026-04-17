import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Loader2, Search, SlidersHorizontal } from 'lucide-react';
import { getOrganizationPortfolio } from '../api/kiraApi';
import { useAuth } from '../context/useAuth';
import PortfolioKpiStrip from '../components/PortfolioKpiStrip';
import LoanTable from '../components/LoanTable';
import RiskHeatmap from '../components/RiskHeatmap';
import CohortChart from '../components/CohortChart';

const normalizeText = (value) => String(value ?? '').trim().toLowerCase();
const toSentenceCase = (value) => {
  const normalized = String(value ?? '')
    .replace(/[_-]+/g, ' ')
    .trim()
    .toLowerCase();
  if (!normalized) return '';
  return `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)}`;
};

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

  const allLoans = data?.loans || [];

  const states = useMemo(
    () => [...new Set(allLoans.map((loan) => loan.state).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
    [allLoans],
  );

  const districts = useMemo(() => {
    const selectedState = normalizeText(filters.state);
    return [...new Set(
      allLoans
        .filter((loan) => !selectedState || normalizeText(loan.state) === selectedState)
        .map((loan) => loan.district)
        .filter(Boolean),
    )].sort((a, b) => a.localeCompare(b));
  }, [allLoans, filters.state]);

  const statusOptions = useMemo(
    () => [...new Set(allLoans.map((loan) => loan.status).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
    [allLoans],
  );

  const riskOptions = useMemo(
    () => [...new Set(allLoans.map((loan) => loan.risk_band).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
    [allLoans],
  );

  const loans = useMemo(() => {
    const query = normalizeText(filters.search);
    const selectedState = normalizeText(filters.state);
    const selectedDistrict = normalizeText(filters.district);
    const selectedStatus = normalizeText(filters.status);
    const selectedRisk = normalizeText(filters.risk);

    return allLoans.filter((loan) => {
      const searchable = [
        loan.store_name,
        loan.borrower_name,
        loan.pin_code,
        loan.case_id,
      ]
        .map((value) => normalizeText(value))
        .join(' ');

      const matchesSearch = !query || searchable.includes(query);
      const matchesState = !selectedState || normalizeText(loan.state) === selectedState;
      const matchesDistrict = !selectedDistrict || normalizeText(loan.district) === selectedDistrict;
      const matchesStatus = !selectedStatus || normalizeText(loan.status) === selectedStatus;
      const matchesRisk = !selectedRisk || normalizeText(loan.risk_band) === selectedRisk;
      return matchesSearch && matchesState && matchesDistrict && matchesStatus && matchesRisk;
    });
  }, [allLoans, filters]);

  if (loading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-primary-500 animate-spin" /></div>;
  }

  if (error) {
    return <div className="text-center py-20"><AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" /><p className="text-slate-600 font-medium">{error}</p></div>;
  }

  return (
    <div className="animate-fade-in max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-black tracking-tight text-slate-900">Portfolio</h1>
        <p className="text-slate-600 font-medium mt-2">Risk concentration, drilldowns, and cohort performance from one command center.</p>
      </div>

      <PortfolioKpiStrip metrics={data?.metrics || []} />

      <div className="rounded-2xl border border-slate-200 bg-white/95 p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-500">
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Portfolio Filters
        </div>
        <div className="grid lg:grid-cols-5 gap-3">
          <div className="relative lg:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={filters.search}
              onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
              placeholder="Search borrower, store, pin, case ID"
              className="w-full rounded-xl border border-slate-300 bg-white pl-9 pr-3 py-2.5 text-sm outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-100"
            />
          </div>
          <select value={filters.state} onChange={(event) => setFilters((current) => ({ ...current, state: event.target.value, district: '' }))} className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm bg-white outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
            <option value="">All states</option>
            {states.map((state) => <option key={state} value={state}>{state}</option>)}
          </select>
          <select value={filters.district} onChange={(event) => setFilters((current) => ({ ...current, district: event.target.value }))} className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm bg-white outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
            <option value="">All districts</option>
            {districts.map((district) => <option key={district} value={district}>{district}</option>)}
          </select>
          <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))} className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm bg-white outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
            <option value="">All Status</option>
            {statusOptions.map((status) => (
              <option key={status} value={status}>{toSentenceCase(status)}</option>
            ))}
          </select>
          <select value={filters.risk} onChange={(event) => setFilters((current) => ({ ...current, risk: event.target.value }))} className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm bg-white outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100">
            <option value="">All risk tiers</option>
            {riskOptions.map((risk) => (
              <option key={risk} value={risk}>{risk.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid xl:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 mb-4">Risk by geography</h2>
          <RiskHeatmap data={data?.geography_distribution || {}} />
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 mb-4">Cohort trend</h2>
          <CohortChart cohorts={data?.cohorts || []} />
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 mb-4">Loan drilldown</h2>
        <LoanTable loans={loans.slice(0, loadLimit)} />
        {loadLimit < loans.length && (
          <div className="mt-6 text-center">
            <button 
              onClick={() => setLoadLimit(prev => prev + 10)}
              className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-6 py-2.5 text-sm font-semibold text-slate-700 transition hover:-translate-y-0.5 hover:border-slate-400 hover:shadow-md"
            >
              Load More ({loans.length - loadLimit} remaining)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
