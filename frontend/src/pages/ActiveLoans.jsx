import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Wallet, Loader2, AlertTriangle, ArrowRight, Clock3 } from 'lucide-react';
import { listOrganizationCases, listOrganizationKiranas } from '../api/kiraApi';
import { useAuth } from '../context/useAuth';
import { ACTIVE_LOAN_STATUSES, formatCurrency, getCaseNextAction } from '../utils/caseUtils';

const STATUS_LABELS = {
  approved: 'Approved',
  disbursed: 'Disbursed',
  monitoring: 'Monitoring',
  restructured: 'Restructured',
};

const STATUS_STYLES = {
  approved: 'bg-emerald-100 text-emerald-700',
  disbursed: 'bg-sky-100 text-sky-700',
  monitoring: 'bg-amber-100 text-amber-700',
  restructured: 'bg-rose-100 text-rose-700',
};

export default function ActiveLoans() {
  const { org } = useAuth();
  const [cases, setCases] = useState([]);
  const [kiranaMap, setKiranaMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
        console.error('Failed to load active loans:', err);
        setError('Failed to load active loans.');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [org?.id]);

  const activeLoans = useMemo(
    () => cases.filter((caseItem) => ACTIVE_LOAN_STATUSES.includes(caseItem.status)),
    [cases],
  );

  const totalExposure = activeLoans.reduce(
    (sum, caseItem) => sum + (caseItem.latest_loan_range?.high || 0),
    0,
  );

  if (loading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-primary-500 animate-spin" /></div>;
  }

  if (error) {
    return <div className="text-center py-20"><AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" /><p className="text-slate-600 font-medium">{error}</p></div>;
  }

  return (
    <div className="animate-fade-in max-w-7xl mx-auto">
      <div className="mb-8 flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 flex items-center gap-2">
            <Wallet className="w-6 h-6 text-primary-600" /> Active Loans
          </h1>
          <p className="text-slate-500 font-medium mt-1">Current exposure across approved, disbursed, and monitored borrower cases.</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl px-5 py-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide font-bold text-slate-400">Total Exposure Ceiling</div>
          <div className="text-2xl font-black text-slate-900 mt-1">{formatCurrency(totalExposure)}</div>
        </div>
      </div>

      {activeLoans.length === 0 ? (
        <div className="text-center py-20 bg-white border border-slate-200 rounded-xl">
          <Wallet className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500 font-medium">No active loans yet</p>
          <p className="text-sm text-slate-400 mt-1">Approved and disbursed cases will appear here automatically.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {activeLoans.map((caseItem) => {
            const kirana = kiranaMap[caseItem.kirana_id];
            return (
              <Link
                key={caseItem.id}
                to={caseItem.status === 'approved' ? `/app/cases/${caseItem.id}` : `/app/loan-accounts/${caseItem.id}`}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:border-primary-200 hover:shadow-md transition-all"
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-3 mb-2">
                      <h2 className="text-lg font-bold text-slate-900">{kirana?.store_name || 'Unknown Store'}</h2>
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${STATUS_STYLES[caseItem.status] || 'bg-slate-100 text-slate-700'}`}>
                        {STATUS_LABELS[caseItem.status] || caseItem.status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500">{kirana?.owner_name || 'Unknown borrower'}</p>
                    <p className="text-sm text-slate-500 mt-1">
                      {[kirana?.location?.district, kirana?.location?.state, kirana?.location?.pin_code].filter(Boolean).join(' • ')}
                    </p>
                  </div>
                  <div className="grid sm:grid-cols-3 gap-4 lg:min-w-[420px]">
                    <div>
                      <div className="text-xs uppercase font-bold tracking-wide text-slate-400">Loan Range</div>
                      <div className="text-sm font-bold text-slate-800 mt-1">
                        {caseItem.latest_loan_range
                          ? `${formatCurrency(caseItem.latest_loan_range.low)} - ${formatCurrency(caseItem.latest_loan_range.high)}`
                          : '-'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs uppercase font-bold tracking-wide text-slate-400">Next Action</div>
                      <div className="text-sm font-semibold text-slate-700 mt-1">{getCaseNextAction(caseItem)}</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase font-bold tracking-wide text-slate-400">Updated</div>
                      <div className="text-sm font-semibold text-slate-700 mt-1 flex items-center gap-1.5">
                        <Clock3 className="w-3.5 h-3.5 text-slate-400" />
                        {new Date(caseItem.updated_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex justify-end mt-4 text-primary-600 text-sm font-semibold items-center gap-1">
                  Open case <ArrowRight className="w-4 h-4" />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
