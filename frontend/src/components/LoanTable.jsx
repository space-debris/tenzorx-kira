import { Link } from 'react-router-dom';
import { formatCurrency } from '../utils/caseUtils';

const RISK_STYLES = {
  LOW: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  MEDIUM: 'bg-blue-50 text-blue-700 border-blue-200',
  HIGH: 'bg-amber-50 text-amber-700 border-amber-200',
  VERY_HIGH: 'bg-rose-50 text-rose-700 border-rose-200',
};

function getStressStyle(score = 0) {
  if (score >= 0.7) return 'text-rose-700 bg-rose-50 border-rose-200';
  if (score >= 0.4) return 'text-amber-700 bg-amber-50 border-amber-200';
  return 'text-emerald-700 bg-emerald-50 border-emerald-200';
}

export default function LoanTable({ loans = [] }) {
  if (!loans.length) {
    return <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm text-slate-500 text-center">No loans available for current filters.</div>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200">
      <table className="w-full">
        <thead>
          <tr className="bg-slate-50/80 text-left">
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Borrower</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Location</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Status</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Risk</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Exposure</th>
            <th className="px-4 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Stress</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {loans.map((loan) => (
            <tr key={loan.case_id} className="hover:bg-slate-50/70 transition-colors">
              <td className="px-4 py-3">
                <div className="font-semibold text-slate-900 text-sm">{loan.store_name}</div>
                <div className="text-xs text-slate-400">{loan.borrower_name}</div>
              </td>
              <td className="px-4 py-3 text-sm text-slate-600">
                {[loan.district, loan.state, loan.pin_code].filter(Boolean).join(' • ')}
              </td>
              <td className="px-4 py-3 text-sm">
                <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-semibold text-slate-700 capitalize">
                  {loan.status.replace('_', ' ')}
                </span>
              </td>
              <td className="px-4 py-3 text-sm font-semibold text-slate-700">
                <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${RISK_STYLES[loan.risk_band] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                  {loan.risk_band || '-'}
                </span>
              </td>
              <td className="px-4 py-3 text-sm font-bold text-slate-800">{formatCurrency(loan.exposure)}</td>
              <td className="px-4 py-3 text-sm">
                <span className={`inline-flex rounded-full border px-2.5 py-1 font-semibold ${getStressStyle(loan.stress_score || 0)}`}>
                  {Math.round((loan.stress_score || 0) * 100)}%
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <Link to={loan.loan_account_id ? `/app/loan-accounts/${loan.case_id}` : `/app/cases/${loan.case_id}`} className="text-primary-600 hover:text-primary-700 text-sm font-bold">
                  Open
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
